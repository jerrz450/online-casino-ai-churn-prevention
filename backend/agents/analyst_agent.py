import asyncio
import json
import logging
from typing import AsyncIterator, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command

from backend.agents.models.analyst_models import AnalystReport, SelfEvaluation
from backend.agents.tools.analyst_tools import (
    get_score_distribution, get_false_positive_rate,
    get_segment_performance, get_intervention_outcomes,
    get_model_metrics,
)
from backend.db.redis_client import get_redis
from backend.db.setup_checkpoints import connect_to_checkpoints
from backend.services.domain.system_tuner import update_threshold, reload_model, trigger_retrain, update_train_config
from backend.services.external.llm_service import get_llm
from backend.prompts.analyst_prompts import ANALYST_SYSTEM, SELF_EVAL_SYSTEM

logger = logging.getLogger(__name__)

_TOOLS = [get_score_distribution, get_false_positive_rate, get_segment_performance, get_intervention_outcomes, get_model_metrics]
_NODES = {"gather_stats", "analyze", "self_evaluate", "await_approval", "apply"}

class AnalystState(TypedDict):

    stats: dict
    report: str
    recommendations: list[dict]
    needs_revision: bool
    critique: str
    revision_count: int
    approved_actions: list[str]
    approved_params: dict
    applied: list[str]


async def _invoke(schema, messages):
    return await get_llm(use_langchain=True).with_structured_output(schema).ainvoke(messages)

async def gather_stats(state: AnalystState) -> dict:

    results = await asyncio.gather(*(asyncio.to_thread(t.func) for t in _TOOLS))
    return {"stats": dict(zip((t.name for t in _TOOLS), results))} 

async def analyze(state: AnalystState) -> dict:

    critique = f"\n\nPrevious critique: {state['critique']}\nRevise accordingly." if state.get("critique") else ""

    report: AnalystReport = await _invoke(
            AnalystReport,
            [
            ("system", ANALYST_SYSTEM),
            ("human", f"Stats:\n{json.dumps(state['stats'], indent=2)}{critique}\n\nProvide analysis and recommendations."),
            ],
        )
    
    return {
        "report": report.summary,
        "recommendations": [r.model_dump() for r in report.recommendations],
        "needs_revision": False,
        "critique": "",
    }

async def self_evaluate(state: AnalystState) -> dict:
    
    evaluation: SelfEvaluation = await _invoke(SelfEvaluation, [
        ("system", SELF_EVAL_SYSTEM),
        ("human", f"Stats:\n{json.dumps(state['stats'], indent=2)}\n\nRecommendations:\n{json.dumps(state['recommendations'], indent=2)}\n\nAre these well-justified? Should any be revised?"),
    ])

    revised = [r.model_dump() for r in evaluation.revised_recommendations] if evaluation.revised_recommendations else state["recommendations"]

    return {
        "needs_revision": evaluation.needs_revision,
        "critique": evaluation.critique,
        "recommendations": revised,
        "revision_count": state.get("revision_count", 0) + 1,
    }

async def await_approval(state: AnalystState) -> dict:

    approved = interrupt({"report": state["report"], "recommendations": state["recommendations"]})

    if isinstance(approved, dict):
        return {
            "approved_actions": approved.get("approved_actions", []),
            "approved_params": approved.get("approved_params", {}),
        }
    
    return {}

async def apply(state: AnalystState) -> dict:

    redis = await get_redis()

    applied = []

    for action in state.get("approved_actions", []):
        params = state.get("approved_params", {}).get(action, {})

        if action == "update_threshold":
            await update_threshold(redis, params["value"])

        elif action == "reload_model":
            await reload_model(redis)

        elif action == "trigger_retrain":
            await trigger_retrain()

        elif action == "update_train_config":
            train_params = {k: v for k, v in params.items() if v is not None and k != "value"}
            await update_train_config(redis, train_params)

        applied.append(action)
        logger.info(f"Applied: {action}")

    return {"applied": applied}


def _route_after_eval(state: AnalystState) -> str:

    if state.get("needs_revision") and state.get("revision_count", 0) < 1:
        return "analyze"
    
    return "await_approval"


def _parse_event(event: dict, thread_id: str) -> dict | None:

    # Parses the raw event from the graph and extracts relevant info to stream to the frontend. This is where you can customize what info to send based on the event type and content.
    # Convert LangGraph’s verbose internal event into a frontend message.

    etype = event["event"]
    name = event.get("name", "")

    if etype == "on_chain_start" and name in _NODES:
        return {"type": "node", "name": name}

    if etype == "on_chat_model_stream":

        chunk = event["data"].get("chunk")

        if chunk and chunk.content:
            return {"type": "token", "content": chunk.content}

    if etype == "on_tool_start":
        return {"type": "tool_start", "name": name}

    if etype == "on_tool_end":
        return {"type": "tool_end", "name": name, "preview": str(event["data"].get("output", ""))[:200]}

    return None

async def _build_graph():

    checkpointer = await connect_to_checkpoints()

    g = StateGraph(AnalystState)

    g.add_node("gather_stats", gather_stats)
    g.add_node("analyze", analyze)
    g.add_node("self_evaluate", self_evaluate)
    g.add_node("await_approval", await_approval)
    g.add_node("apply", apply)
    g.add_edge(START, "gather_stats")
    g.add_edge("gather_stats", "analyze")
    g.add_edge("analyze", "self_evaluate")
    g.add_conditional_edges("self_evaluate", _route_after_eval)
    g.add_edge("await_approval", "apply")
    g.add_edge("apply", END)

    return g.compile(checkpointer=checkpointer)


class AnalystAgent:

    _graph = None

    # Build the graph on demand, then reuse for subsequent analyses to save time. Each analysis run is differentiated by thread_id in the config, which allows for multiple concurrent runs if needed.
    async def _get_graph(self):

        if self._graph is None:
            self._graph = await _build_graph()

        return self._graph

    async def stream_analysis(self, thread_id: str) -> AsyncIterator[str]:

        graph = await self._get_graph()

        config = {"configurable": {"thread_id": thread_id}} # Thread ID allows multiple concurrent runs and keeps their state separate in the checkpointer, while still using the same underlying graph structure and code.

        # Keep track of the anlyst state accross events.
        initial: AnalystState = {
            "stats": {}, "report": "", 
            "recommendations": [],
            "needs_revision": False, 
            "critique": "", "revision_count": 0,
            "approved_actions": [], 
            "approved_params": {}, 
            "applied": [],
        }

        async for event in graph.astream_events(initial, config, version="v2"): # Stream events from the graph as they happen.

            msg = _parse_event(event, thread_id) # Parse relevant info to stream event to the frontend.

            if msg:
                yield f"data: {json.dumps(msg)}\n\n"

        # After the graph finishes, check if there are any interrupts (like approved actions from the frontend) and stream those as well before closing the connection.
        snapshot = await graph.aget_state(config)

        if snapshot.next:

            interrupts = [t.interrupts for t in snapshot.tasks if t.interrupts] # Check for any interrupts from state, that might have been triggered by frontend.

            if interrupts:
                payload = interrupts[0][0].value

                yield f"data: {json.dumps({'type': 'interrupt', 'thread_id': thread_id, **payload})}\n\n" # Stream the interrupt payload to the frontend so it can update the UI or trigger any necessary actions.

    async def stream_apply(self, thread_id: str, approved_actions: list[str], params: dict) -> AsyncIterator[str]:
        
        # Compared to stream_analysis, this method allows the frontend to trigger the "apply" node directly with specific approved actions and parameters, without going through the whole analysis process again.
        graph = await self._get_graph()

        config = {"configurable": {"thread_id": thread_id}}
        resume = {"approved_actions": approved_actions, "approved_params": params} # This payload will be injected into the graph at the "await_approval" node, allowing it to skip directly to "apply" with the given actions and params.

        async for event in graph.astream_events(Command(resume=resume), config, version="v2"): 

            msg = _parse_event(event, thread_id)

            if msg:
                yield f"data: {json.dumps(msg)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"


_agent: AnalystAgent | None = None

def get_analyst_agent() -> AnalystAgent:

    global _agent

    if _agent is None:
        _agent = AnalystAgent()

    return _agent
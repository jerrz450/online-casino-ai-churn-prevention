"""
Monitor Agent - Detects player behavioral anomalies.

Uses hybrid approach:
1. Deterministic rules catch obvious patterns (fast, cheap)
2. LLM analysis for complex/ambiguous cases (only when needed)

LangGraph flow:
  Events → Rule Check → [Anomaly?] → Yes → LLM Analysis
                                   → No → Continue
"""

from typing import TypedDict, List, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from backend.services.external.llm_service import get_llm
from backend.db.setup_checkpoints import connect_to_checkpoints
from backend.db.postgres import get_db
from backend.db.connection import get_engine
from pathlib import Path
from backend.agents.pydantic_models.monitor_models import MonitorDecision
import json

class MonitorState(TypedDict):

    """State object passed between nodes."""

    events: List[dict]  # Bet events with monitor_context
    flagged_players: List[int]  # Player IDs that need intervention
    needs_llm_analysis: bool  # Whether to route to LLM
    analysis_reason: str  # Why this needs deeper analysis

class MonitorAgent:

    """
    Watches player behavior for churn risk signals.

    Deterministic rules handle 90% of cases. LLM only for edge cases.
    """

    def __init__(self):

        self.db = get_db()
        self.checkpointer = None
        self.graph = None

    async def _ensure_initialized(self):

        if self.graph is None:
            self.checkpointer = await connect_to_checkpoints()
            self.graph = self._build_graph()

    def _build_graph(self):

        workflow = StateGraph(MonitorState)

        workflow.add_node("rule_check", self._deterministic_rule_check)
        workflow.add_node("llm_call", self._llm_analysis)

        workflow.set_entry_point("rule_check")

        workflow.add_conditional_edges(
            "rule_check",
            self._should_use_llm,
            {
                "llm": "llm_call",
                "end": END,
            }
        )

        workflow.add_edge("llm_call", END)

        return workflow.compile(checkpointer = self.checkpointer)

    def _deterministic_rule_check(self, state: MonitorState) -> MonitorState:
        
        """
        Apply deterministic rules to detect obvious anomalies.

        Rules:
        - Consecutive losses >= 5 + bet escalation
        - Emotional state = TILTING
        - Bankroll drop > 30% in session
        - Boredom (breaking even for too long)
        """

        events = state["events"]
        flagged = []
        needs_llm = False
        reason = ""

        for event in events:
            ctx = event.get("monitor_context", {})
            player_id = ctx.get("player_id")
            decision = "PASS"

            consecutive_losses = ctx.get("consecutive_losses", 0)
            bet_amount = event.get("bet_amount", 0)
            typical_bet = ctx.get("typical_bet", 0)
            bankroll_change = ctx.get("bankroll_change_percent", 0)

            if ctx.get("emotional_state") == "tilting":
                flagged.append(player_id)
                decision = "FLAG"

            elif consecutive_losses >= 5 and bet_amount > typical_bet * 2:
                flagged.append(player_id)
                decision = "FLAG"

            elif bankroll_change < -30:
                flagged.append(player_id)
                decision = "FLAG"

            elif ctx.get("emotional_state") == "bored":
                flagged.append(player_id)
                decision = "FLAG"

            else:
                if consecutive_losses >= 2 and bet_amount > typical_bet * 1.2:
                    needs_llm = True
                    reason = f"Ambiguous: Player {player_id} early tilt signals"

                if ctx.get("emotional_state") == "winning" and bet_amount > typical_bet * 2.5:
                    needs_llm = True
                    reason = f"Ambiguous: Player {player_id} aggressive betting while winning"

                if -25 < bankroll_change < -15:
                    needs_llm = True
                    reason = f"Ambiguous: Player {player_id} moderate bankroll decline"

            if player_id:
                self.db.create_monitor_event(
                    player_id=player_id,
                    decision=decision,
                    decision_source="rules",
                    player_context=json.dumps(ctx)
                )   

        state["flagged_players"] = list(set(flagged)) 
        state["needs_llm_analysis"] = needs_llm
        state["analysis_reason"] = reason

        return state


    def _should_use_llm(self, state: MonitorState) -> Literal["llm", "end"]:
        
        """
        Conditional edge: decide if LLM analysis needed.

        Returns "llm" to route to LLM, "end" to skip.
        """

        if state.get("needs_llm_analysis", False):
            return "llm"
        
        return "end"


    async def _llm_analysis(self, state: MonitorState) -> MonitorState:

        prompt_path = Path(__file__).parent.parent / "prompts" / "monitor_llm.txt"
        prompt_template = prompt_path.read_text()

        event = state["events"][0] if state["events"] else {}
        ctx = event.get("monitor_context", {})

        prompt = prompt_template.format(
            reason=state["analysis_reason"],
            player_type=ctx.get("player_type", "unknown"),
            consecutive_losses=ctx.get("consecutive_losses", 0),
            bet_amount=event.get("bet_amount", 0),
            typical_bet=ctx.get("typical_bet", 0),
            bankroll_change=ctx.get("bankroll_change_percent", 0)
        )

        try:

            llm = get_llm()
            result = await llm.invoke_structured(prompt, MonitorDecision, max_tokens=10)
            decision: MonitorDecision = result  # type: ignore
            player_id = ctx.get("player_id")

            if decision:
                print(f"LLM: {decision.decision}")

                if decision.decision == "FLAG":
                    if player_id:
                        state["flagged_players"].append(player_id)
            
            self.db.create_monitor_event(
                player_id=player_id,
                decision=decision.decision,
                decision_source="llm",
                player_context=json.dumps(ctx) 
            )   

        except Exception as e:
            print(f"  LLM failed: {e}")

        return state

    async def analyze_events(self, events: List[dict]) -> List[int]:

        await self._ensure_initialized()

        initial_state: MonitorState = {
            "events": events,
            "flagged_players": [],
            "needs_llm_analysis": False,
            "analysis_reason": ""
        }

        config = {"configurable": {"thread_id": "monitor_global"}}
        final_state = await self.graph.ainvoke(initial_state, config=config)

        flagged = final_state["flagged_players"]

        if flagged:
            print(f"[Monitor] Flagged {len(flagged)} players: {flagged}")

        return flagged

if __name__ == "__main__":

    agent = MonitorAgent()
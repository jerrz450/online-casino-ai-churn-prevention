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
from backend.services.llm_service import get_llm
from pathlib import Path
from backend.agents.pydantic_models.monitor_models import MonitorDecision

# State that flows through the graph
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

        return workflow.compile()

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

            # Rule 1: Tilting (clear signal)
            if ctx.get("emotional_state") == "tilting":
                flagged.append(player_id)
                continue  

            # Rule 2: Consecutive losses + bet escalation
            consecutive_losses = ctx.get("consecutive_losses", 0)
            bet_amount = event.get("bet_amount", 0)
            typical_bet = ctx.get("typical_bet", 0)

            if consecutive_losses >= 5 and bet_amount > typical_bet * 2:
                flagged.append(player_id)
                continue  # Clear chasing pattern

            # Rule 3: Bankroll crash (>30% loss)
            bankroll_change = ctx.get("bankroll_change_percent", 0)
            if bankroll_change < -30:

                flagged.append(player_id)
                continue  # Clear danger signal

            # Rule 4: Boredom (breaking even)
            if ctx.get("emotional_state") == "bored":
                flagged.append(player_id)
                continue  # Clear engagement issue

            # Ambiguous case 1: Early tilt signals (2-3 losses + bet increase)
            if consecutive_losses >= 2 and bet_amount > typical_bet * 1.2:

                needs_llm = True
                reason = f"Ambiguous: Player {player_id} early tilt signals (2+ losses, bet up 20%)"

            # Ambiguous case 2: Winning aggressively (could be confidence or overconfidence)
            if ctx.get("emotional_state") == "winning" and bet_amount > typical_bet * 2.5:
                needs_llm = True
                reason = f"Ambiguous: Player {player_id} aggressive betting while winning"

            # Ambiguous case 3: Moderate bankroll decline (15-25%)
            # Not crash yet, but trending negative - worth LLM analysis
            if -25 < bankroll_change < -15:

                needs_llm = True
                reason = f"Ambiguous: Player {player_id} moderate bankroll decline ({bankroll_change:.1f}%)"

        # update state
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

            if decision:
                print(f"  LLM: {decision.decision}")

                if decision.decision == "FLAG":
                    player_id = ctx.get("player_id")
                    
                    if player_id:
                        state["flagged_players"].append(player_id)

        except Exception as e:
            print(f"  LLM failed: {e}")

        return state

    async def analyze_events(self, events: List[dict]) -> List[int]:
        """
        Main entry point: analyze batch of events.

        Args:
            events: List of bet events with monitor_context

        Returns:
            List of player IDs flagged for intervention
        """
        initial_state: MonitorState = {
            "events": events,
            "flagged_players": [],
            "needs_llm_analysis": False,
            "analysis_reason": ""
        }

        final_state = await self.graph.ainvoke(initial_state)

        flagged = final_state["flagged_players"]

        if flagged:
            print(f"[Monitor] Flagged {len(flagged)} players: {flagged}")

        return flagged

if __name__ == "__main__":

    agent = MonitorAgent()
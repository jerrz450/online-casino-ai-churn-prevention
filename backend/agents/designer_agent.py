from typing import Optional, Dict, Any
import asyncio
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import create_agent
from backend.services.external.llm_service import get_llm
from backend.db.setup_checkpoints import connect_to_checkpoints
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

from backend.db.postgres import get_db

class DesignerTools:

    def __init__(self):

        self.db = get_db()

    def get_intervention_success_rate(self, intervention_type: str) -> float:

        return self.db.get_intervention_success_rate(intervention_type)

    def get_player_intervention_history(self, player_id: int, limit: int = 5) -> list:

        return self.db.get_player_intervention_history(player_id, limit)

    def check_cooldown(self, player_id: int, hours: int = 6) -> dict:

        return self.db.check_cooldown(player_id, hours)

    def check_monthly_bonus_limit(self, player_id: int, max_monthly: float = 100.0) -> Dict[str, Any]:

        prefs = self.db.get_player_preferences(player_id)

        if not prefs:
            return {"can_send": True, "used": 0.0, "remaining": max_monthly}

        used = prefs.get("monthly_bonus_total", 0.0) or 0.0
        remaining = max_monthly - used
        can_send = remaining > 0

        return {"can_send": can_send, "used": used, "remaining": remaining}

    def check_exclusion_status(self, player_id: int) -> Dict[str, Any]:

        prefs = self.db.get_player_preferences(player_id)
        
        if not prefs:
            return {"excluded": False, "opted_out": False}

        return {
            "excluded": prefs.get("do_not_disturb", False),
            "opted_out": prefs.get("opted_out_marketing", False)
        }

    def get_player_preferences(self, player_id: int) -> Optional[dict]:

        return self.db.get_player_preferences(player_id)

_designer_tools = None

def get_designer_tools():
    
    global _designer_tools

    if _designer_tools is None:
        _designer_tools = DesignerTools()

    return _designer_tools

@tool
def check_cooldown(player_id: int, hours: int = 6) -> dict:
    """Check if enough time has passed since player's last intervention.

    Use this before designing any intervention to ensure compliance with timing rules.
    Returns dict with 'can_send' (bool), 'reason' (str), and optionally 'hours_since_last' (float).

    Args:
        player_id: The player to check
        hours: Minimum hours required between interventions (default 6)
    """
    return get_designer_tools().check_cooldown(player_id, hours)

@tool
def check_monthly_bonus_limit(player_id: int, max_monthly: float = 100.0) -> Dict[str, Any]:
    """Check if player has reached their monthly bonus limit.

    Use this to ensure we don't exceed budget constraints for this player.
    Returns dict with 'can_send' (bool), 'used' (float), 'remaining' (float).

    Args:
        player_id: The player to check
        max_monthly: Maximum monthly bonus allowed (default 100.0 EUR)
    """
    return get_designer_tools().check_monthly_bonus_limit(player_id, max_monthly)

@tool
def check_exclusion_status(player_id: int) -> Dict[str, Any]:
    """Check if player is excluded or has opted out of marketing communications.

    CRITICAL: Must check this before sending any intervention. Never send to excluded/opted-out players.
    Returns dict with 'excluded' (bool), 'opted_out' (bool).

    Args:
        player_id: The player to check
    """
    return get_designer_tools().check_exclusion_status(player_id)

@tool
def get_player_intervention_history(player_id: int, limit: int = 5) -> list:
    """Get past interventions sent to this player.

    Use this to avoid repeating the same intervention type and understand what worked before.
    Returns list of dicts with intervention_type, amount, outcome, timestamp.

    Args:
        player_id: The player to check
        limit: Number of recent interventions to retrieve (default 5)
    """
    return get_designer_tools().get_player_intervention_history(player_id, limit)

@tool
def get_intervention_success_rate(intervention_type: str) -> float:
    """Get historical success rate for a specific intervention type.

    Use this to choose the most effective intervention type based on past performance.
    Returns float between 0.0 and 1.0 representing retention rate.

    Args:
        intervention_type: Type of intervention (bonus_cash, free_spins, personalized_message, cashback)
    """
    return get_designer_tools().get_intervention_success_rate(intervention_type)

class DesignerAgent:

    def __init__(self):

        self.checkpointer = None
        self.agent = None

    async def _ensure_initialized(self):

        if self.agent is None:
            self.checkpointer = await connect_to_checkpoints()
            self.agent = self._build_agent()

    def _build_agent(self):

        llm: ChatOpenAI = get_llm(use_langchain=True)

        tools = [
                check_cooldown,
                check_monthly_bonus_limit,
                check_exclusion_status,
                get_player_intervention_history,
                get_intervention_success_rate,
            ]

        return create_agent(llm, tools, checkpointer= self.checkpointer)

    async def design_intervention(self, player_context: dict, risk_score: float) -> Optional[dict]:

        await self._ensure_initialized()

        if self.agent is None:
            raise RuntimeError("Agent initialization failed")

        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "prompts" / "designer_agent.txt"
        prompt_template = prompt_path.read_text()

        player_id = player_context.get("player_id")
        player_type = player_context.get("player_type")
        emotional_state = player_context.get("emotional_state")
        current_bankroll = player_context.get("current_bankroll", 0)
        net_profit_loss = player_context.get("net_profit_loss", 0)
        consecutive_losses = player_context.get("consecutive_losses", 0)
        sessions_completed = player_context.get("sessions_completed", 0)

        prompt = prompt_template.format(
                player_id=player_id,
                player_type=player_type,
                risk_score=risk_score,
                emotional_state=emotional_state,
                current_bankroll=current_bankroll,
                net_profit_loss=net_profit_loss,
                consecutive_losses=consecutive_losses,
                sessions_completed=sessions_completed,
            )
        
        from langchain_core.messages import HumanMessage
        from backend.db.setup_checkpoints import get_recent_messages_checkpoint

        thread_id = f"designer_player_{player_id}"
        config = {"configurable": {"thread_id": thread_id}} 

        past_messages = await get_recent_messages_checkpoint(self.checkpointer, thread_id, limit=5)
        print("CHECKPOINT MESSAGES", past_messages)
        
        new_message = HumanMessage(content=prompt)
        all_messages = past_messages + [new_message]
        
        result = await self.agent.ainvoke({"messages": all_messages}, config = config)

        import json
        import re

        last_message = result["messages"][-1].content
        print(f"[Designer] Raw LLM response: {last_message[:200]}...")

        json_match = re.search(r'\{[\s\S]*\}', last_message)
        if json_match:
            try:
                intervention_data = json.loads(json_match.group())
                print(f"[Designer] Parsed intervention: {intervention_data}")
                return intervention_data
            except json.JSONDecodeError as e:
                print(f"[Designer] Failed to parse JSON: {e}")
                print(f"[Designer] Attempted to parse: {json_match.group()}")
                return None

        print(f"[Designer] No JSON found in response")
        return None
     
"""
Serializer to provide context in the dictionary format to the LLM agents
Each agent has it's own function, to convert to certain format and structure.

"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.simulation import SimulatedPlayer

class PlayerContextSerializer:

    """Converts player objects to structured dicts for LLM agents."""

    @staticmethod
    def to_monitor_context(player: 'SimulatedPlayer') -> dict:
        
        """
        Format for Monitor Agent - behavioral signals for anomaly detection.

        Focus: Recent patterns, emotional state, red flags.
        """

        state = player.behavior_state

        return {
            "player_id": player.player_id,
            "player_type": player.player_type.type_name,

            # Current state
            "emotional_state": state.emotional_state.value,
            "consecutive_losses": state.consecutive_losses,
            "consecutive_wins": state.consecutive_wins,

            # Financial state
            "current_bankroll": round(state.current_bankroll, 2),
            "session_start_bankroll": round(state.session_start_bankroll, 2),
            "net_profit_loss": round(state.net_profit_loss, 2),
            "bankroll_change_percent": round(
                ((state.current_bankroll - state.session_start_bankroll) / state.session_start_bankroll * 100)
                if state.session_start_bankroll > 0 else 0,
                2
            ),

            # Session activity
            "bets_this_session": state.bets_this_session,
            "total_wagered": round(state.total_wagered, 2),

            # Risk indicators
            "is_at_risk": state.is_at_risk,
            "is_active": player.is_active,

            # Type profile (for comparison)
            "tilt_threshold": player.player_type.tilt_threshold,
            "typical_bet": player.player_type.typical_bet,
        }


    @staticmethod
    def to_predictor_context(player: 'SimulatedPlayer') -> dict:
        
        """
        Format for Predictor Agent - historical patterns for similarity search.

        Focus: Behavioral summary, session history, churn indicators.
        """

        state = player.behavior_state

        return {
            "player_id": player.player_id,
            "player_type": player.player_type.type_name,

            # Behavioral summary
            "emotional_state": state.emotional_state.value,
            "consecutive_losses": state.consecutive_losses,
            "sessions_completed": state.sessions_completed,
            "sessions_since_big_event": state.sessions_since_last_big_event,

            # Financial patterns
            "net_profit_loss": round(state.net_profit_loss, 2),
            "total_wagered": round(state.total_wagered, 2),
            "current_bankroll": round(state.current_bankroll, 2),

            # Churn indicators
            "base_churn_probability": player.player_type.base_churn_probability,
            "current_risk_score": state.churn_risk_score,

            # Past interventions
            "interventions_received": len(state.interventions_received),
            "last_intervention": state.last_intervention_accepted,
        }


    @staticmethod
    def to_designer_context(player: 'SimulatedPlayer') -> dict:
        
        """
        Format for Designer Agent - player value and preferences.

        Focus: LTV, intervention preferences, budget constraints.
        """

        state = player.behavior_state

        return {
            "player_id": player.player_id,
            "player_type": player.player_type.type_name,

            # Value metrics
            "estimated_ltv": player.player_type.estimated_ltv_eur,
            "total_wagered": round(state.total_wagered, 2),
            "net_profit_loss": round(state.net_profit_loss, 2),

            # Preferences
            "prefers_free_spins": player.player_type.prefers_free_spins,
            "intervention_acceptance_rate": player.player_type.intervention_acceptance_rate,

            # Current state
            "emotional_state": state.emotional_state.value,
            "current_bankroll": round(state.current_bankroll, 2),
            "churn_risk_score": state.churn_risk_score,

            # Past interventions (what worked before)
            "interventions_history": state.interventions_received,
            "interventions_count": len(state.interventions_received),
        }


    @staticmethod
    def to_validator_context(player: 'SimulatedPlayer', intervention: dict) -> dict:
        
        """
        Format for Validator Agent - compliance checks.

        Focus: Limits, regulations, player protection.
        """

        state = player.behavior_state

        return {
            "player_id": player.player_id,
            "player_type": player.player_type.type_name,

            # Proposed intervention
            "intervention_type": intervention.get("type"),
            "intervention_amount": intervention.get("amount"),

            # Compliance data
            "interventions_today": len(state.interventions_received),  # Would be filtered by date in production
            "total_bonus_received": sum(i.get("amount", 0) for i in state.interventions_received),

            # Player state (for responsible gaming checks)
            "emotional_state": state.emotional_state.value,
            "total_wagered": round(state.total_wagered, 2),
            "net_profit_loss": round(state.net_profit_loss, 2),
            "has_churned": state.has_churned,
        }


    @staticmethod
    def to_executor_context(player: 'SimulatedPlayer', intervention: dict) -> dict:
        
        """
        Format for Executor Agent - delivery details.

        Focus: What to deliver, how, and when.
        """

        return {
            "player_id": player.player_id,
            "is_active": player.is_active,

            # Intervention details
            "intervention_type": intervention.get("type"),
            "intervention_amount": intervention.get("amount"),
            "intervention_message": intervention.get("message", ""),

            # Delivery context
            "emotional_state": player.behavior_state.emotional_state.value,
            "current_session_bets": player.behavior_state.bets_this_session,
        }


    @staticmethod
    def to_analyzer_context(player: 'SimulatedPlayer', intervention: dict, before_state: dict) -> dict:
        
        """
        Format for Analyzer Agent - outcome measurement.

        Focus: Before/after metrics, ROI calculation.
        """

        state = player.behavior_state

        return {
            "player_id": player.player_id,
            "player_type": player.player_type.type_name,

            # Intervention details
            "intervention": intervention,

            # Before state
            "before": before_state,

            # After state (24h later)
            "after": {
                "has_churned": state.has_churned,
                "churn_reason": state.churn_reason.value if state.churn_reason else None,
                "sessions_completed": state.sessions_completed,
                "total_wagered": round(state.total_wagered, 2),
                "net_profit_loss": round(state.net_profit_loss, 2),
            },

            # ROI calculation
            "intervention_cost": intervention.get("amount", 0),
            "estimated_ltv": player.player_type.estimated_ltv_eur,
        }


    @staticmethod
    def to_full_context(player: 'SimulatedPlayer') -> dict:

        """Complete player context - for debugging or admin views."""

        state = player.behavior_state

        return {
            "player_id": player.player_id,
            "player_type": player.player_type.type_name,
            "created_at": player.created_at.isoformat() if player.created_at else None,

            # Current state
            "is_active": player.is_active,
            "emotional_state": state.emotional_state.value,
            "current_bankroll": round(state.current_bankroll, 2),
            "net_profit_loss": round(state.net_profit_loss, 2),

            # Streaks
            "consecutive_wins": state.consecutive_wins,
            "consecutive_losses": state.consecutive_losses,

            # Session data
            "bets_this_session": state.bets_this_session,
            "sessions_completed": state.sessions_completed,
            "total_wagered": round(state.total_wagered, 2),

            # Risk
            "is_at_risk": state.is_at_risk,
            "churn_risk_score": state.churn_risk_score,
            "has_churned": state.has_churned,
            "churn_reason": state.churn_reason.value if state.churn_reason else None,

            # Interventions
            "interventions_received": state.interventions_received,

            # Player profile
            "estimated_ltv": player.player_type.estimated_ltv_eur,
            "typical_bet": player.player_type.typical_bet,
        }

from backend.services.domain.knowledge_service import query_similar_players

class PredictorAgent:

    async def calculate_risk(self, player, top_k: int = 10) -> float:

        similar = await query_similar_players(player, top_k=top_k)

        if not similar:
            return 0.0

        churned_count = sum(
            1 for match in similar
            if match.metadata.get("outcome") == "churned"
        )

        risk_score = churned_count / len(similar)

        print(f"[Predictor] Player {player.player_id}: {churned_count}/{len(similar)} similar players churned (risk: {risk_score:.2f})")

        return risk_score

_predictor = None

def get_predictor() -> PredictorAgent:
    
    global _predictor
    
    if _predictor is None:
        _predictor = PredictorAgent()

    return _predictor

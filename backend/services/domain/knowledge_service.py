from typing import Optional, TYPE_CHECKING
from datetime import datetime
from backend.services.external.embedding_service import get_embedding_service
from backend.services.external.pinecone_service import get_pinecone_service
from backend.services.domain.player_context_serializer import PlayerContextSerializer
from config.settings import PINECONE_NAMESPACE

async def store_player_snapshot(
    player, 
    outcome: str = "pending"
) -> str:

    ctx = PlayerContextSerializer.to_predictor_context(player)

    text = f"""
        Player type: {ctx['player_type']}
        Emotional state: {ctx['emotional_state']}
        Consecutive losses: {ctx['consecutive_losses']}
        Sessions completed: {ctx['sessions_completed']}
        Net profit/loss: {ctx['net_profit_loss']}
        Current bankroll: {ctx['current_bankroll']}
        Churn risk score: {ctx['current_risk_score']}
    """

    embedding = await get_embedding_service().generate_embedding(text)

    snapshot_id = f"player_{ctx['player_id']}_{int(datetime.now().timestamp())}"

    metadata = {
        "player_id": ctx['player_id'],
        "player_type": ctx['player_type'],
        "emotional_state": ctx['emotional_state'],
        "consecutive_losses": ctx['consecutive_losses'],
        "net_profit_loss": ctx['net_profit_loss'],
        "outcome": outcome,
        "timestamp": int(datetime.now().timestamp())
    }

    await get_pinecone_service().upsert([(snapshot_id, embedding, metadata)])
    print("Stored to Pinecone successfully!")

    return snapshot_id

async def query_similar_players(player, 
                                top_k: int = 5) -> list:

    ctx = PlayerContextSerializer.to_predictor_context(player)

    text = f"""
        Player type: {ctx['player_type']}
        Emotional state: {ctx['emotional_state']}
        Consecutive losses: {ctx['consecutive_losses']}
        Sessions completed: {ctx['sessions_completed']}
        Net profit/loss: {ctx['net_profit_loss']}
        Current bankroll: {ctx['current_bankroll']}
        Churn risk score: {ctx['current_risk_score']}
        """

    embedding = await get_embedding_service().generate_embedding(text)

    results = await get_pinecone_service().query(embedding, top_k=top_k)

    return results.matches

async def update_outcome(snapshot_id: str, outcome: str, intervention_worked: Optional[bool] = None):

    metadata_updates = {"outcome": outcome}

    if intervention_worked is not None:
        metadata_updates["intervention_worked"] = intervention_worked

    pinecone = get_pinecone_service()

    pinecone.index.update(id=snapshot_id, set_metadata=metadata_updates, namespace=PINECONE_NAMESPACE)
    print(f"Updated snapshot {snapshot_id} to outcome={outcome}")

"""Pydantic models for Predictor agent."""

from pydantic import BaseModel
from typing import List

class PredictorResult(BaseModel):

    player_id: int
    risk_score: float
    similar_count: int
    churned_count: int
    similar_player_ids: List[int]

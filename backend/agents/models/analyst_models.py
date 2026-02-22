from typing import Literal
from pydantic import BaseModel, ConfigDict


class RecommendationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float | None = None          # update_threshold
    max_depth: int | None = None        # update_train_config
    learning_rate: float | None = None  # update_train_config
    subsample: float | None = None      # update_train_config
    colsample_bytree: float | None = None  # update_train_config
    min_child_weight: int | None = None    # update_train_config


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    action: Literal["update_threshold", "trigger_retrain", "reload_model", "update_train_config"]
    rationale: str
    params: RecommendationParams


class AnalystReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    findings: list[str]
    recommendations: list[Recommendation]
    confidence: Literal["high", "medium", "low"]


class SelfEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    needs_revision: bool
    critique: str
    revised_recommendations: list[Recommendation]

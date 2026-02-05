"""Pydantic models for Monitor agent."""

from pydantic import BaseModel
from typing import Literal

class MonitorDecision(BaseModel):
    
    """LLM decision for ambiguous player behavior."""
    decision: Literal["FLAG", "IGNORE"]

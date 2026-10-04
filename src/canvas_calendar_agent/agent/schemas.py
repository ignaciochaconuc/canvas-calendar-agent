"""Schemas estructurados que debe producir el agente."""

from __future__ import annotations
from datetime import time
from typing import Literal
from pydantic import BaseModel, Field

AgentEventType = Literal["exam", "quiz", "assignment", "project", "presentation",
                         "class", "activity", "deadline", "other"]
Importance = Literal["important", "not_important", "uncertain"]


class ExtractedAcademicEvent(BaseModel):
    title: str | None
    event_type: AgentEventType | None
    year: int | None = Field(default=None, ge=1900, le=2200)
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)
    time: time | None
    is_update: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str | None
    importance: Importance = "uncertain"


class CandidateAnalysis(BaseModel):
    events: list[ExtractedAcademicEvent]

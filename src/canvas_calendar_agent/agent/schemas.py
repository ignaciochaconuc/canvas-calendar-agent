"""Schema estructurado que debe producir el agente."""

from __future__ import annotations

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field

AgentEventType = Literal[
    "exam", "quiz", "assignment", "project", "presentation",
    "class", "activity", "deadline", "other",
]


class ExtractedAcademicEvent(BaseModel):
    """Interpretación estructurada de un único EventCandidate."""

    has_event: bool
    title: str | None
    event_type: AgentEventType | None
    date: date | None
    time: time | None
    is_update: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str | None

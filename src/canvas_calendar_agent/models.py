"""Modelos internos comunes para el pipeline académico."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

EventType = Literal[
    "exam", "quiz", "assignment", "project", "presentation",
    "class", "activity", "deadline", "other",
]


@dataclass(slots=True)
class AcademicEvent:
    course_id: int
    course_name: str
    course_code: str | None
    title: str
    event_type: EventType
    start_at: datetime | None
    end_at: datetime | None
    all_day: bool
    description: str | None
    source_type: str
    source_id: str | None
    source_url: str | None
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EventCandidate:
    course_id: int
    course_name: str
    source_type: str
    source_id: str | None
    title: str
    text: str | None
    source_url: str | None
    published_at: datetime | None


@dataclass(slots=True)
class ExtractedDocument:
    filename: str
    mime_type: str
    page_count: int
    text: str
    pages: list[str]

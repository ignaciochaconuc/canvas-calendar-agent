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
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractedDocument:
    filename: str
    mime_type: str
    page_count: int
    text: str
    pages: list[str]


@dataclass(slots=True)
class SpreadsheetRow:
    sheet_name: str
    row_number: int
    values: list[str]


@dataclass(slots=True)
class ExtractedSpreadsheet:
    filename: str
    mime_type: str
    sheet_names: list[str]
    rows: list[SpreadsheetRow]


@dataclass(slots=True)
class EventSource:
    source_type: str
    source_id: str | None
    label: str
    url: str | None = None


@dataclass(slots=True)
class ConsolidatedEvent:
    course_id: int
    course_name: str
    course_code: str | None
    title: str
    event_type: EventType
    start_at: datetime | None
    end_at: datetime | None
    all_day: bool
    description: str | None
    confidence: float
    sources: list[EventSource]
    status: Literal["ok", "pending", "conflict", "approved", "discarded"]
    alternatives: list[datetime | None] = field(default_factory=list)

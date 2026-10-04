"""Consolidación conservadora y determinística de eventos académicos."""

from __future__ import annotations
import re, unicodedata
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo
from .models import AcademicEvent, ConsolidatedEvent, EventCandidate, EventSource
from .agent.schemas import CandidateAnalysis

def normalize_title(title: str) -> str:
    value = "".join(c for c in unicodedata.normalize("NFD", title.lower())
                    if unicodedata.category(c) != "Mn")
    value = re.sub(r"\bi\s*([1-9])\b", r"interrogacion \1", value)
    value = re.sub(r"\binterrogacion\s*(\d+)\b", r"interrogacion \1", value)
    value = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", value)).strip()
    return value

def _compatible_titles(a: str, b: str) -> bool:
    left, right = normalize_title(a), normalize_title(b)
    if left == right: return True
    shorter, longer = sorted((left, right), key=len)
    return len(shorter) >= 8 and longer.startswith(shorter + " ")

def _compatible_types(a: str, b: str) -> bool:
    return a == b or "other" in {a, b} or {a, b} <= {"exam", "quiz"} or {a, b} <= {"assignment", "project", "deadline"}

def _source(event: AcademicEvent) -> EventSource:
    return EventSource(event.source_type, event.source_id, event.source_type, event.source_url)

def consolidate_events(events: Iterable[AcademicEvent]) -> list[ConsolidatedEvent]:
    result: list[ConsolidatedEvent] = []
    for item in events:
        match = next((current for current in result
                      if current.course_id == item.course_id
                      and _compatible_titles(current.title, item.title)
                      and _compatible_types(current.event_type, item.event_type)), None)
        if match is None:
            consolidated=ConsolidatedEvent(item.course_id, item.course_name, item.course_code,
                item.title, item.event_type, item.start_at, item.end_at, item.all_day,
                item.description, item.confidence, [_source(item)],
                "ok" if item.start_at else "pending", [item.start_at])
            consolidated.agent_importance=item.metadata.get("importance")
            result.append(consolidated)
            continue
        match.sources.append(_source(item)); match.confidence = max(match.confidence, item.confidence)
        if item.start_at not in match.alternatives: match.alternatives.append(item.start_at)
        if match.start_at and item.start_at:
            if match.start_at.date() != item.start_at.date() or (
                not match.all_day and not item.all_day and match.start_at.time() != item.start_at.time()):
                match.status = "conflict"
            elif match.all_day and not item.all_day:
                match.start_at, match.all_day = item.start_at, False
        elif match.start_at is None and item.start_at is not None:
            match.start_at = item.start_at; match.status = "ok"
    return sorted(result, key=lambda event: (event.course_name, event.start_at.isoformat() if event.start_at else "9999"))

def edit_event(event: ConsolidatedEvent, *, start_at: datetime | None,
               title: str | None = None, all_day: bool | None = None) -> ConsolidatedEvent:
    return replace(event, title=title or event.title, start_at=start_at,
                   all_day=event.all_day if all_day is None else all_day,
                   status="approved" if start_at else "pending", alternatives=[start_at],
                   manual_approval=bool(start_at))

def discard_event(event: ConsolidatedEvent) -> ConsolidatedEvent:
    return replace(event, status="discarded")

def analysis_to_events(analysis: CandidateAnalysis, candidate: EventCandidate,
                       course: dict) -> list[AcademicEvent]:
    result = []
    for index, item in enumerate(analysis.events):
        complete = item.year is not None and item.month is not None and item.day is not None
        start = None
        if complete:
            clock = item.time
            start = datetime(item.year, item.month, item.day,
                             clock.hour if clock else 0, clock.minute if clock else 0,
                             tzinfo=ZoneInfo("America/Santiago"))
        result.append(AcademicEvent(candidate.course_id, candidate.course_name,
            course.get("course_code"), item.title or candidate.title, item.event_type or "other",
            start, None, complete and item.time is None, item.reasoning_summary,
            candidate.source_type, f"{candidate.source_id}:event:{index}", candidate.source_url,
            item.confidence, {"partial_date": {"year": item.year, "month": item.month, "day": item.day},
                              "importance": item.importance}))
    return result

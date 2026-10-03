"""Conversión determinística de fechas estructuradas de Canvas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .models import AcademicEvent

PROJECT_TIMEZONE = ZoneInfo("America/Santiago")


def parse_canvas_datetime(value: str | None) -> datetime | None:
    """Interpreta ISO 8601 y conserva el instante en la zona del proyecto."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Canvas entregó una fecha sin zona horaria.")
    return parsed.astimezone(PROJECT_TIMEZONE)


def assignment_to_event(
    assignment: dict[str, Any], course: dict[str, Any]
) -> AcademicEvent | None:
    due_at = parse_canvas_datetime(assignment.get("due_at"))
    if due_at is None:
        return None
    return AcademicEvent(
        course_id=int(course["id"]),
        course_name=_course_name(course),
        course_code=course.get("course_code"),
        title=assignment.get("name") or "Tarea sin título",
        event_type="assignment",
        start_at=due_at,
        end_at=None,
        all_day=False,
        description=assignment.get("description"),
        source_type="assignment",
        source_id=_source_id(assignment.get("id")),
        source_url=assignment.get("html_url"),
        confidence=1.0,
        metadata={
            "unlock_at": assignment.get("unlock_at"),
            "lock_at": assignment.get("lock_at"),
            "submission_types": assignment.get("submission_types", []),
        },
    )


def calendar_event_to_event(
    calendar_event: dict[str, Any], course: dict[str, Any]
) -> AcademicEvent | None:
    start_at = parse_canvas_datetime(calendar_event.get("start_at"))
    if start_at is None:
        return None
    return AcademicEvent(
        course_id=int(course["id"]),
        course_name=_course_name(course),
        course_code=course.get("course_code"),
        title=calendar_event.get("title") or "Evento sin título",
        event_type="other",
        start_at=start_at,
        end_at=parse_canvas_datetime(calendar_event.get("end_at")),
        all_day=bool(calendar_event.get("all_day", False)),
        description=calendar_event.get("description"),
        source_type="calendar_event",
        source_id=_source_id(calendar_event.get("id")),
        source_url=calendar_event.get("html_url") or calendar_event.get("url"),
        confidence=1.0,
        metadata={
            "location_name": calendar_event.get("location_name"),
            "location_address": calendar_event.get("location_address"),
            "context_code": calendar_event.get("context_code"),
        },
    )


def extract_structured_events(
    course: dict[str, Any], assignments: Iterable[dict[str, Any]],
    calendar_events: Iterable[dict[str, Any]],
) -> list[AcademicEvent]:
    events = [assignment_to_event(item, course) for item in assignments]
    events.extend(calendar_event_to_event(item, course) for item in calendar_events)
    return deduplicate_events(event for event in events if event is not None)


def deduplicate_events(events: Iterable[AcademicEvent]) -> list[AcademicEvent]:
    """Elimina duplicados del mismo tipo e ID de origen, conservando el primero."""
    result: list[AcademicEvent] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        if event.source_id is None:
            result.append(event)
            continue
        key = (event.source_type, event.source_id)
        if key not in seen:
            seen.add(key)
            result.append(event)
    return result


def _course_name(course: dict[str, Any]) -> str:
    return course.get("name") or course.get("course_code") or "Curso sin nombre"


def _source_id(value: Any) -> str | None:
    return None if value is None else str(value)

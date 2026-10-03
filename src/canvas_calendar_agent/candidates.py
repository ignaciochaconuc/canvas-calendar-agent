"""Creación de contenido pendiente para un futuro agente de interpretación."""

from __future__ import annotations

from typing import Any, Iterable

from .extractors import parse_canvas_datetime
from .models import EventCandidate


def build_event_candidates(
    course: dict[str, Any], *, assignments: Iterable[dict[str, Any]] = (),
    announcements: Iterable[dict[str, Any]] = (), pages: Iterable[dict[str, Any]] = (),
    course_details: dict[str, Any] | None = None,
) -> list[EventCandidate]:
    candidates: list[EventCandidate] = []
    for item in assignments:
        if not item.get("due_at"):
            candidates.append(_candidate(course, "assignment", item.get("id"),
                item.get("name") or "Tarea sin título", item.get("description"),
                item.get("html_url"), item.get("created_at")))
    for item in announcements:
        candidates.append(_candidate(course, "announcement", item.get("id"),
            item.get("title") or "Anuncio sin título", item.get("message"),
            item.get("html_url"), item.get("posted_at")))
    for item in pages:
        if item.get("body"):
            candidates.append(_candidate(course, "page", item.get("page_id"),
                item.get("title") or "Página sin título", item.get("body"),
                item.get("html_url"), item.get("published_at") or item.get("created_at")))
    details = course_details or {}
    if details.get("syllabus_body"):
        candidates.append(_candidate(course, "syllabus", course.get("id"),
            f"Programa: {_course_name(course)}", details["syllabus_body"],
            details.get("html_url"), details.get("created_at")))
    return candidates


def _candidate(course: dict[str, Any], source_type: str, source_id: Any,
               title: str, text: str | None, source_url: str | None,
               published_at: str | None) -> EventCandidate:
    return EventCandidate(
        course_id=int(course["id"]), course_name=_course_name(course),
        source_type=source_type,
        source_id=None if source_id is None else str(source_id), title=title,
        text=text, source_url=source_url,
        published_at=parse_canvas_datetime(published_at),
    )


def _course_name(course: dict[str, Any]) -> str:
    return course.get("name") or course.get("course_code") or "Curso sin nombre"

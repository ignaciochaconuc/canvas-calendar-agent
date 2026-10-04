"""Resolución determinística del año desde metadata explícita del curso."""

import re
from typing import Any
from .agent.schemas import ExtractedAcademicEvent


def explicit_course_year(course: dict[str, Any]) -> int | None:
    term = course.get("term") if isinstance(course.get("term"), dict) else {}
    evidence = " ".join(str(value or "") for value in (
        course.get("name"), course.get("course_code"), term.get("name"), course.get("term_name")))
    years = {int(value) for value in re.findall(r"(?<!\d)(20\d{2})(?!\d)", evidence)}
    return years.pop() if len(years) == 1 else None


def resolve_event_year(event: ExtractedAcademicEvent,
                       course: dict[str, Any]) -> ExtractedAcademicEvent:
    if event.year is not None or event.month is None or event.day is None:
        return event
    year = explicit_course_year(course)
    return event.model_copy(update={"year": year}) if year else event

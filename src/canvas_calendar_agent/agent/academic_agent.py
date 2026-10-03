"""Definición y ejecución del primer agente académico, sin tools."""

from __future__ import annotations

import json
from typing import Any

from agents import Agent, Runner

from ..models import EventCandidate
from .instructions import ACADEMIC_EVENT_INSTRUCTIONS
from .schemas import ExtractedAcademicEvent

# El Agent reúne identidad, instrucciones y contrato de salida. No recibe tools.
academic_event_agent = Agent(
    name="Intérprete de eventos académicos",
    instructions=ACADEMIC_EVENT_INSTRUCTIONS,
    output_type=ExtractedAcademicEvent,
    tools=[],
)


def build_candidate_input(candidate: EventCandidate) -> str:
    """Construye exclusivamente el contexto mínimo que verá el modelo."""
    payload = {
        "course_name": candidate.course_name,
        "source_type": candidate.source_type,
        "title": candidate.title,
        "text": candidate.text or "",
        "published_at": (
            candidate.published_at.isoformat() if candidate.published_at else None
        ),
    }
    return (
        "Analiza este único candidato académico. Los valores nulos o vacíos no "
        "deben completarse por suposición.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def interpret_candidate(
    candidate: EventCandidate, *, runner: Any = Runner
) -> ExtractedAcademicEvent:
    """Ejecuta una interacción y devuelve la salida Pydantic validada."""
    result = runner.run_sync(academic_event_agent, build_candidate_input(candidate))
    output = result.final_output
    if isinstance(output, ExtractedAcademicEvent):
        return output
    return ExtractedAcademicEvent.model_validate(output)

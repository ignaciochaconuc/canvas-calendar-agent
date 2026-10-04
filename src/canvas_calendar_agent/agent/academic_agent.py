"""Definición y ejecución del primer agente académico, sin tools."""

from __future__ import annotations

import json
import re
from typing import Any

from agents import Agent, Runner

from ..models import EventCandidate
from .instructions import ACADEMIC_EVENT_INSTRUCTIONS
from .model_provider import build_model
from .schemas import CandidateAnalysis

# El Agent reúne identidad, instrucciones y contrato de salida. No recibe tools.
academic_event_agent = Agent(
    name="Intérprete de eventos académicos",
    instructions=ACADEMIC_EVENT_INSTRUCTIONS,
    output_type=CandidateAnalysis,
    model=build_model(),
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
) -> CandidateAnalysis:
    """Ejecuta una interacción y devuelve la salida Pydantic validada."""
    result = runner.run_sync(academic_event_agent, build_candidate_input(candidate))
    output = result.final_output
    analysis = output if isinstance(output, CandidateAnalysis) else CandidateAnalysis.model_validate(output)
    explicit_years = {int(value) for value in re.findall(
        r"(?<!\d)(20\d{2})(?!\d)", candidate.text or ""
    )}
    # El schema valida el formato; esta barrera valida la evidencia del año.
    events = [event if event.year is None or event.year in explicit_years
              else event.model_copy(update={"year": None}) for event in analysis.events]
    return analysis.model_copy(update={"events": events})

"""Agente experimental para interpretar candidatos académicos."""

from .academic_agent import academic_event_agent, interpret_candidate
from .schemas import ExtractedAcademicEvent

__all__ = ["ExtractedAcademicEvent", "academic_event_agent", "interpret_candidate"]

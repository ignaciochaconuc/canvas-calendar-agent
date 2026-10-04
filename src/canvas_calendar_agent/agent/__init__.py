"""Agente experimental para interpretar candidatos académicos."""

from .academic_agent import academic_event_agent, interpret_candidate
from .model_provider import ModelProviderError, check_model_available
from .schemas import CandidateAnalysis, ExtractedAcademicEvent

__all__ = [
    "ExtractedAcademicEvent",
    "CandidateAnalysis",
    "ModelProviderError",
    "academic_event_agent",
    "check_model_available",
    "interpret_candidate",
]

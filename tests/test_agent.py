import json, sys, unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from canvas_calendar_agent.agent.academic_agent import academic_event_agent, build_candidate_input, interpret_candidate
from canvas_calendar_agent.agent.instructions import ACADEMIC_EVENT_INSTRUCTIONS
from canvas_calendar_agent.agent.schemas import CandidateAnalysis, ExtractedAcademicEvent
from canvas_calendar_agent.models import EventCandidate

def candidate(text="La prueba será el 21 de octubre."):
    return EventCandidate(42, "Optimización", "announcement", "7", "Aviso", text,
                          "https://example/7", datetime.fromisoformat("2026-10-03T10:00:00-03:00"))

def event(**changes):
    values = dict(title="I1", event_type="exam", year=None, month=9, day=24, time="17:30",
                  is_update=False, confidence=1, reasoning_summary="Fecha explícita.")
    values.update(changes); return ExtractedAcademicEvent(**values)

class AgentTests(unittest.TestCase):
    def test_input_contains_only_expected_context(self):
        prompt = build_candidate_input(candidate()); payload = json.loads(prompt.split("\n\n", 1)[1])
        self.assertEqual(set(payload), {"course_name", "source_type", "title", "text", "published_at"})
        self.assertNotIn("source_url", prompt); self.assertNotIn("source_id", prompt)

    def test_multiple_events_and_missing_year(self):
        analysis = CandidateAnalysis(events=[event(), event(title="I2", month=10, day=29)])
        self.assertEqual(len(analysis.events), 2)
        self.assertTrue(all(item.year is None for item in analysis.events))

    def test_empty_analysis_and_validation(self):
        self.assertEqual(CandidateAnalysis(events=[]).events, [])
        with self.assertRaises(ValidationError): event(confidence=1.1)
        with self.assertRaises(ValidationError): event(event_type="holiday")

    def test_runner_once_and_contract(self):
        expected = CandidateAnalysis(events=[]); runner = Mock()
        runner.run_sync.return_value = SimpleNamespace(final_output=expected)
        self.assertEqual(interpret_candidate(candidate(), runner=runner), expected)
        runner.run_sync.assert_called_once(); self.assertEqual(academic_event_agent.tools, [])
        self.assertIs(academic_event_agent.output_type, CandidateAnalysis)

    def test_removes_year_not_explicit_in_candidate(self):
        runner = Mock(); runner.run_sync.return_value = SimpleNamespace(
            final_output=CandidateAnalysis(events=[event(year=2025)]))
        self.assertIsNone(interpret_candidate(candidate("I1: 24 de septiembre"), runner=runner).events[0].year)
        runner.run_sync.return_value = SimpleNamespace(
            final_output=CandidateAnalysis(events=[event(year=2026)]))
        self.assertEqual(interpret_candidate(candidate("I1: 24 de septiembre de 2026"), runner=runner).events[0].year, 2026)

    def test_update_instructions_prevent_regression(self):
        self.assertIn("Podría reprogramarse", ACADEMIC_EVENT_INSTRUCTIONS)
        self.assertIn("is_update=false", ACADEMIC_EVENT_INSTRUCTIONS)
        self.assertIn("year debe ser null", ACADEMIC_EVENT_INSTRUCTIONS)

if __name__ == "__main__": unittest.main()

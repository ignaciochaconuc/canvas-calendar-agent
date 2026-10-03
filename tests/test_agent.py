import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canvas_calendar_agent.agent.academic_agent import (
    academic_event_agent,
    build_candidate_input,
    interpret_candidate,
)
from canvas_calendar_agent.agent.schemas import ExtractedAcademicEvent
from canvas_calendar_agent.models import EventCandidate


def candidate(text="La prueba será el 21 de octubre."):
    return EventCandidate(
        course_id=42,
        course_name="Optimización",
        source_type="announcement",
        source_id="7",
        title="Cambio de fecha",
        text=text,
        source_url="https://canvas.example/announcement/7",
        published_at=datetime.fromisoformat("2026-10-03T10:00:00-03:00"),
    )


class AgentTests(unittest.TestCase):
    def test_build_candidate_input_contains_only_expected_context(self):
        prompt = build_candidate_input(candidate())
        payload = json.loads(prompt.split("\n\n", 1)[1])
        self.assertEqual(
            set(payload),
            {"course_name", "source_type", "title", "text", "published_at"},
        )
        self.assertEqual(payload["course_name"], "Optimización")
        self.assertNotIn("source_url", prompt)
        self.assertNotIn("source_id", prompt)

    def test_candidate_without_text_uses_empty_string(self):
        prompt = build_candidate_input(candidate(None))
        payload = json.loads(prompt.split("\n\n", 1)[1])
        self.assertEqual(payload["text"], "")

    def test_schema_accepts_valid_structured_output(self):
        output = ExtractedAcademicEvent(
            has_event=True,
            title="Interrogación 2",
            event_type="exam",
            date="2026-10-21",
            time=None,
            is_update=True,
            confidence=0.94,
            reasoning_summary="El anuncio indica explícitamente una nueva fecha.",
        )
        self.assertEqual(output.event_type, "exam")
        self.assertEqual(output.date.isoformat(), "2026-10-21")

    def test_schema_rejects_confidence_outside_range(self):
        with self.assertRaises(ValidationError):
            ExtractedAcademicEvent(
                has_event=False, title=None, event_type=None, date=None, time=None,
                is_update=False, confidence=1.1, reasoning_summary=None,
            )

    def test_schema_rejects_unknown_category(self):
        with self.assertRaises(ValidationError):
            ExtractedAcademicEvent(
                has_event=True, title="Evento", event_type="holiday", date=None,
                time=None, is_update=False, confidence=0.5, reasoning_summary=None,
            )

    def test_interpret_candidate_uses_runner_once(self):
        expected = ExtractedAcademicEvent(
            has_event=False, title=None, event_type=None, date=None, time=None,
            is_update=False, confidence=0.8, reasoning_summary="No hay fecha concreta.",
        )
        runner = Mock()
        runner.run_sync.return_value = SimpleNamespace(final_output=expected)
        result = interpret_candidate(candidate(), runner=runner)
        self.assertIs(result, expected)
        runner.run_sync.assert_called_once()
        self.assertIs(runner.run_sync.call_args.args[0], academic_event_agent)

    def test_agent_has_no_tools_and_structured_output(self):
        self.assertEqual(academic_event_agent.tools, [])
        self.assertIs(academic_event_agent.output_type, ExtractedAcademicEvent)


if __name__ == "__main__":
    unittest.main()

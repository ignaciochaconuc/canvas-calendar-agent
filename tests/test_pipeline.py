import sys
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canvas_calendar_agent.candidates import build_event_candidates
from canvas_calendar_agent.config import load_course_ids, save_course_ids
from canvas_calendar_agent.extractors import (
    assignment_to_event,
    calendar_event_to_event,
    deduplicate_events,
    parse_canvas_datetime,
)


COURSE = {"id": 42, "name": "Optimización", "course_code": "ICS1113-1"}


class ExtractorTests(unittest.TestCase):
    def test_assignment_to_academic_event(self):
        event = assignment_to_event(
            {
                "id": 7,
                "name": "Entrega proyecto",
                "description": "<p>Descripción</p>",
                "due_at": "2026-10-10T23:59:00Z",
                "unlock_at": "2026-10-01T12:00:00Z",
                "lock_at": "2026-10-11T03:00:00Z",
                "submission_types": ["online_upload"],
                "html_url": "https://canvas.example/courses/42/assignments/7",
            },
            COURSE,
        )
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "assignment")
        self.assertEqual(event.source_type, "assignment")
        self.assertEqual(event.source_id, "7")
        self.assertEqual(event.confidence, 1.0)
        self.assertEqual(event.start_at.tzinfo.key, "America/Santiago")
        self.assertEqual(event.metadata["submission_types"], ["online_upload"])

    def test_assignment_without_due_at_is_not_an_event(self):
        self.assertIsNone(assignment_to_event({"id": 8, "name": "Lectura"}, COURSE))

    def test_calendar_event_conversion(self):
        event = calendar_event_to_event(
            {
                "id": 9,
                "title": "Clase especial",
                "start_at": "2026-10-03T14:00:00-03:00",
                "end_at": "2026-10-03T15:30:00-03:00",
                "all_day": False,
                "description": "Sala por confirmar",
                "location_name": "Sala 10",
                "location_address": "Campus",
                "context_code": "course_42",
                "html_url": "https://canvas.example/calendar?event_id=9",
            },
            COURSE,
        )
        self.assertEqual(event.source_type, "calendar_event")
        self.assertEqual(event.end_at.hour, 15)
        self.assertEqual(event.metadata["location_name"], "Sala 10")
        self.assertEqual(event.confidence, 1.0)

    def test_timezone_preserves_instant_and_uses_santiago(self):
        parsed = parse_canvas_datetime("2026-07-01T12:00:00Z")
        self.assertEqual(parsed.tzinfo.key, "America/Santiago")
        self.assertEqual(parsed.astimezone(timezone.utc).hour, 12)
        self.assertEqual(parsed.hour, 8)
        with self.assertRaisesRegex(ValueError, "sin zona horaria"):
            parse_canvas_datetime("2026-07-01T12:00:00")

    def test_deduplicates_only_same_source_type_and_id(self):
        assignment = assignment_to_event(
            {"id": 7, "name": "Entrega", "due_at": "2026-10-10T12:00:00Z"}, COURSE
        )
        calendar = calendar_event_to_event(
            {"id": 7, "title": "Entrega", "start_at": "2026-10-10T12:00:00Z"}, COURSE
        )
        result = deduplicate_events([assignment, assignment, calendar])
        self.assertEqual(len(result), 2)
        self.assertEqual({item.source_type for item in result}, {"assignment", "calendar_event"})


class CandidateTests(unittest.TestCase):
    def test_generates_candidates_from_unstructured_sources(self):
        candidates = build_event_candidates(
            COURSE,
            assignments=[{"id": 1, "name": "Sin fecha", "description": "Revisar"},
                         {"id": 2, "name": "Con fecha", "due_at": "2026-10-10T12:00:00Z"}],
            announcements=[{"id": 3, "title": "Aviso", "message": "Nueva fecha",
                            "posted_at": "2026-10-01T12:00:00Z"}],
            pages=[{"page_id": 4, "title": "Calendario", "body": "<p>Fechas</p>"},
                   {"page_id": 5, "title": "Sin cuerpo"}],
            course_details={"syllabus_body": "<p>Programa</p>"},
        )
        self.assertEqual(
            [candidate.source_type for candidate in candidates],
            ["assignment", "announcement", "page", "syllabus"],
        )
        self.assertEqual(candidates[1].published_at.tzinfo.key, "America/Santiago")


class ConfigTests(unittest.TestCase):
    def test_save_and_load_course_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_course_ids(path, [105798, 108110, 105798])
            self.assertEqual(load_course_ids(path), [105798, 108110])

    def test_missing_config_returns_empty_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_course_ids(Path(directory) / "missing.json"), [])

    def test_invalid_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"course_ids": [true]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "enteros positivos"):
                load_course_ids(path)


if __name__ == "__main__":
    unittest.main()

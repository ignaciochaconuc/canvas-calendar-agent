import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main


class MainTests(unittest.TestCase):
    def test_choose_course_by_number(self):
        courses = [{"id": 1}, {"id": 2}]
        with patch("builtins.input", side_effect=["x", "2"]), redirect_stdout(io.StringIO()):
            self.assertEqual(main.choose_course(courses), {"id": 2})

    def test_explore_course_prints_counts_samples_and_module_types(self):
        client = Mock()
        client.get_assignments.return_value = [{"name": "Control 1"}]
        client.get_modules.return_value = [
            {"name": "Semana 1", "items": [{"type": "Page"}, {"type": "File"}]}
        ]
        client.get_pages.return_value = [{"title": "Bienvenida"}]
        client.get_files.return_value = [{"display_name": "programa.pdf"}]
        client.get_calendar_events.return_value = [{"title": "Prueba"}]
        client.get_announcements.return_value = [{"title": "Aviso"}]
        client.get_course_details.return_value = {"syllabus_body": "<p>Programa</p>"}
        output = io.StringIO()
        with redirect_stdout(output):
            main.explore_course(client, {"id": 42, "name": "Optimización"})
        text = output.getvalue()
        self.assertIn("Curso seleccionado: Optimización", text)
        self.assertIn("Assignments: 1", text)
        self.assertIn("Control 1", text)
        self.assertIn("Syllabus: disponible", text)
        self.assertIn("File: 1", text)
        self.assertIn("Page: 1", text)


if __name__ == "__main__":
    unittest.main()

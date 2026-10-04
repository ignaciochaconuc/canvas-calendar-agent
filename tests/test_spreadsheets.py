import sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from canvas_calendar_agent.documents import extract_xlsx, is_relevant_file, spreadsheet_blocks, spreadsheet_candidates
from canvas_calendar_agent.year_resolution import explicit_course_year, resolve_event_year
from canvas_calendar_agent.agent.schemas import ExtractedAcademicEvent

class SpreadsheetTests(unittest.TestCase):
    def make_book(self, path):
        book = Workbook(); sheet = book.active; sheet.title = "Proyecto"
        sheet.append(["Actividad", "Fecha", "Hora"])
        sheet.append(["Entrega 1", datetime(2026, 10, 2, 22), "22:00"])
        sheet.append([None, None, None])
        book.create_sheet("Lecturas").append(["Texto", "Autor"]); book.save(path)

    def test_extraction_prefilter_and_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calendario.xlsx"; self.make_book(path)
            document = extract_xlsx(path)
            self.assertEqual(document.sheet_names, ["Proyecto", "Lecturas"])
            self.assertEqual(len(document.rows), 3); self.assertIn("2026-10-02 22:00", document.rows[1].values)
            blocks = spreadsheet_blocks(document); self.assertEqual(len(blocks), 1)
            self.assertIn("Actividad | Fecha | Hora", blocks[0][2])
            candidate = spreadsheet_candidates(document, {"id": 8}, {"id": 1, "name": "Curso"})[0]
            self.assertEqual(candidate.metadata["sheet"], "Proyecto")

    def test_xlsx_relevance(self):
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        base = {"content-type": mime, "size": 10}
        self.assertTrue(is_relevant_file({**base, "filename": "Calendario proyecto.xlsx"}))
        self.assertFalse(is_relevant_file({**base, "filename": "Notas.xlsx"}))

class YearTests(unittest.TestCase):
    def test_deterministic_resolution_only_with_evidence(self):
        item = ExtractedAcademicEvent(title="I1", event_type="exam", year=None, month=9, day=24,
                                      time=None, is_update=False, confidence=1, reasoning_summary=None)
        self.assertEqual(resolve_event_year(item, {"course_code": "ICS1113-2026-2"}).year, 2026)
        self.assertIsNone(resolve_event_year(item, {"name": "Optimización"}).year)
        self.assertIsNone(explicit_course_year({"name": "2025", "term": {"name": "2026-2"}}))

if __name__ == "__main__": unittest.main()

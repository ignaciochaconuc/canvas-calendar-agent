import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canvas_calendar_agent.documents import extract_pdf, file_candidates, is_relevant_file, relevant_blocks
from canvas_calendar_agent.file_cache import FileCache


class DocumentTests(unittest.TestCase):
    def test_relevance_checks_name_mime_and_size(self):
        good = {"filename": "Planificación curso.pdf", "content-type": "application/pdf", "size": 100}
        self.assertTrue(is_relevant_file(good))
        self.assertFalse(is_relevant_file({**good, "filename": "foto.pdf"}))
        self.assertFalse(is_relevant_file({**good, "filename": "Programacion lineal.pdf"}))
        self.assertFalse(is_relevant_file({**good, "content-type": "image/png"}))
        self.assertFalse(is_relevant_file({**good, "size": 30 * 1024 * 1024}))

    def test_extract_and_build_candidate_from_tiny_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "programa.pdf"
            pdf = pymupdf.open()
            page = pdf.new_page()
            page.insert_text((72, 72), "Evaluacion final: 20 de octubre")
            pdf.save(path)
            pdf.close()
            document = extract_pdf(path)
            self.assertEqual(document.page_count, 1)
            self.assertIn("Evaluacion", document.text)
            self.assertEqual(len(relevant_blocks(document)), 1)
            candidates = file_candidates(document, {"id": 9, "url": "https://example/file"},
                                         {"id": 4, "name": "Optimización"})
            self.assertEqual(candidates[0].source_type, "file")
            self.assertEqual(candidates[0].source_id, "9:page:1")

    def test_scanned_or_blank_pdf_has_no_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blank.pdf"
            pdf = pymupdf.open(); pdf.new_page(); pdf.save(path); pdf.close()
            document = extract_pdf(path)
            self.assertEqual(document.text, "")
            self.assertEqual(relevant_blocks(document), [])

    def test_cache_key_changes_with_file_version(self):
        cache = FileCache(Path("cache"))
        first = cache.path_for({"id": 1, "updated_at": "a", "size": 10})
        second = cache.path_for({"id": 1, "updated_at": "b", "size": 10})
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()

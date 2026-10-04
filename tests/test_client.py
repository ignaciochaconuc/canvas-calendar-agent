import unittest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canvas_calendar_agent import CanvasClient, CanvasError


def response_with(payload, *, status_code=200, links=None):
    response = Mock(spec=requests.Response)
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.json.return_value = payload
    response.links = links or {}
    return response


class CanvasClientTests(unittest.TestCase):
    def make_session(self):
        session = Mock(spec=requests.Session)
        session.headers = {}
        return session

    def test_get_active_courses_uses_expected_endpoint_and_parameters(self):
        session = self.make_session()
        session.get.return_value = response_with([{"id": 7, "name": "Álgebra"}])
        courses = CanvasClient(
            "https://canvas.example.edu/", "test-token", session=session
        ).get_active_courses()
        self.assertEqual(courses, [{"id": 7, "name": "Álgebra"}])
        session.get.assert_called_once_with(
            "https://canvas.example.edu/api/v1/courses",
            params={
                "enrollment_state": "active",
                "include[]": "term",
                "per_page": 100,
            },
            timeout=15.0,
        )
        self.assertEqual(session.headers["Authorization"], "Bearer test-token")

    def test_get_active_courses_follows_canvas_pagination(self):
        session = self.make_session()
        next_url = "https://canvas.example.edu/api/v1/courses?page=2"
        session.get.side_effect = [
            response_with([{"id": 1}], links={"next": {"url": next_url}}),
            response_with([{"id": 2}]),
        ]
        courses = CanvasClient(
            "https://canvas.example.edu", "test-token", session=session
        ).get_active_courses()
        self.assertEqual(courses, [{"id": 1}, {"id": 2}])
        self.assertIsNone(session.get.call_args_list[1].kwargs["params"])

    def test_invalid_token_has_clear_error(self):
        for status_code in (401, 403):
            with self.subTest(status_code=status_code):
                session = self.make_session()
                session.get.return_value = response_with({}, status_code=status_code)
                with self.assertRaisesRegex(CanvasError, "token"):
                    CanvasClient(
                        "https://canvas.example.edu", "bad-token", session=session
                    ).get_active_courses()

    def test_connection_error_has_clear_error(self):
        session = self.make_session()
        session.get.side_effect = requests.exceptions.ConnectionError
        with self.assertRaisesRegex(CanvasError, "conectar"):
            CanvasClient(
                "https://canvas.example.edu", "token", session=session
            ).get_active_courses()

    def test_rejects_invalid_base_url(self):
        for base_url in ("", "canvas.example.edu", "ftp://example.edu"):
            with self.subTest(base_url=base_url):
                with self.assertRaisesRegex(CanvasError, "URL"):
                    CanvasClient(base_url, "token")

    def test_rejects_unexpected_payload(self):
        session = self.make_session()
        session.get.return_value = response_with({"courses": []})
        with self.assertRaisesRegex(CanvasError, "formato inesperado"):
            CanvasClient(
                "https://canvas.example.edu", "token", session=session
            ).get_active_courses()

    def test_course_resource_methods_use_expected_endpoints(self):
        cases = (
            ("get_assignments", "/api/v1/courses/42/assignments", {"per_page": 100}),
            ("get_pages", "/api/v1/courses/42/pages", {"include[]": "body", "per_page": 100}),
            ("get_files", "/api/v1/courses/42/files", {"per_page": 100}),
        )
        for method_name, path, expected_params in cases:
            with self.subTest(method=method_name):
                session = self.make_session()
                session.get.return_value = response_with([])
                client = CanvasClient(
                    "https://canvas.example.edu", "token", session=session
                )
                self.assertEqual(getattr(client, method_name)(42), [])
                self.assertEqual(session.get.call_args.args[0], f"https://canvas.example.edu{path}")
                self.assertEqual(session.get.call_args.kwargs["params"], expected_params)

    def test_get_modules_uses_inline_items(self):
        session = self.make_session()
        modules = [{"id": 8, "name": "Semana 1", "items": [{"type": "Page"}]}]
        session.get.return_value = response_with(modules)
        result = CanvasClient(
            "https://canvas.example.edu", "token", session=session
        ).get_modules(42)
        self.assertEqual(result, modules)
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(
            session.get.call_args.kwargs["params"]["include[]"],
            ["items", "content_details"],
        )

    def test_get_modules_fetches_items_when_not_embedded(self):
        session = self.make_session()
        session.get.side_effect = [
            response_with([{"id": 8, "name": "Semana 1"}]),
            response_with([{"id": 9, "type": "File", "title": "Guía"}]),
        ]
        modules = CanvasClient(
            "https://canvas.example.edu", "token", session=session
        ).get_modules(42)
        self.assertEqual(modules[0]["items"][0]["type"], "File")
        self.assertEqual(
            session.get.call_args_list[1].args[0],
            "https://canvas.example.edu/api/v1/courses/42/modules/8/items",
        )

    def test_calendar_events_are_filtered_by_course(self):
        session = self.make_session()
        session.get.return_value = response_with([{"id": 3, "title": "Clase"}])
        events = CanvasClient(
            "https://canvas.example.edu", "token", session=session
        ).get_calendar_events(42)
        self.assertEqual(events[0]["title"], "Clase")
        params = session.get.call_args.kwargs["params"]
        self.assertEqual(params["context_codes[]"], "course_42")
        self.assertEqual(params["type"], "event")
        self.assertEqual(params["all_events"], "true")

    def test_announcements_are_filtered_by_course(self):
        session = self.make_session()
        session.get.return_value = response_with([])
        CanvasClient(
            "https://canvas.example.edu", "token", session=session
        ).get_announcements(42)
        self.assertEqual(
            session.get.call_args.args[0],
            "https://canvas.example.edu/api/v1/announcements",
        )
        self.assertEqual(
            session.get.call_args.kwargs["params"]["context_codes[]"], "course_42"
        )
        self.assertEqual(
            session.get.call_args.kwargs["params"]["start_date"], "2000-01-01"
        )
        self.assertEqual(
            session.get.call_args.kwargs["params"]["end_date"], "2100-01-01"
        )

    def test_course_details_requests_syllabus_and_term(self):
        session = self.make_session()
        session.get.return_value = response_with(
            {"id": 42, "syllabus_body": "<p>Programa</p>"}
        )
        details = CanvasClient(
            "https://canvas.example.edu", "token", session=session
        ).get_course_details(42)
        self.assertEqual(details["id"], 42)
        self.assertEqual(
            session.get.call_args.kwargs["params"]["include[]"],
            ["syllabus_body", "term"],
        )

    def test_rejects_pagination_to_another_host(self):
        session = self.make_session()
        session.get.return_value = response_with(
            [{"id": 1}],
            links={"next": {"url": "https://unexpected.example/api/v1/courses"}},
        )
        with self.assertRaisesRegex(CanvasError, "paginación inesperado"):
            CanvasClient(
                "https://canvas.example.edu", "token", session=session
            ).get_active_courses()

    def test_download_pdf_is_bounded_and_streamed(self):
        session = self.make_session()
        response = response_with(None)
        response.headers = {"Content-Length": "4"}
        response.iter_content.return_value = [b"%PDF"]
        session.get.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "file.pdf"
            result = CanvasClient("https://canvas.example.edu", "token", session=session).download_file(
                {"id": 1, "filename": "programa.pdf", "content-type": "application/pdf",
                 "size": 4, "url": "https://canvas.example.edu/files/1/download"}, target)
            self.assertEqual(result.read_bytes(), b"%PDF")
        self.assertFalse(session.get.call_args.kwargs["allow_redirects"])
        self.assertTrue(session.get.call_args.kwargs["stream"])

    def test_download_rejects_wrong_mime_and_oversize(self):
        client = CanvasClient("https://canvas.example.edu", "token", session=self.make_session())
        base = {"filename": "programa.pdf", "url": "https://canvas.example.edu/f", "size": 1}
        with self.assertRaisesRegex(CanvasError, "PDF"):
            client.download_file({**base, "content-type": "text/plain"}, Path("unused"))
        with self.assertRaisesRegex(CanvasError, "tamaño"):
            client.download_file({**base, "content-type": "application/pdf", "size": 100},
                                 Path("unused"), max_bytes=10)

    def test_download_rejects_unexpected_response_mime(self):
        session = self.make_session()
        response = response_with(None)
        response.headers = {"Content-Type": "text/html"}
        session.get.return_value = response
        client = CanvasClient("https://canvas.example.edu", "token", session=session)
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(CanvasError, "tipo"):
            client.download_file(
                {"filename": "programa.pdf", "content-type": "application/pdf", "size": 1,
                 "url": "https://canvas.example.edu/f"}, Path(directory) / "file.pdf")


if __name__ == "__main__":
    unittest.main()

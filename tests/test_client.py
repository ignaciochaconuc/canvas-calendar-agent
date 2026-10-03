import unittest
import sys
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
            params={"enrollment_state": "active", "per_page": 100},
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


if __name__ == "__main__":
    unittest.main()

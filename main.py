"""Muestra los cursos activos del usuario autenticado en Canvas."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from canvas_calendar_agent import CanvasClient, CanvasError  # noqa: E402


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    base_url = os.getenv("CANVAS_BASE_URL", "")
    token = os.getenv("CANVAS_TOKEN", "")

    try:
        courses = CanvasClient(base_url, token).get_active_courses()
    except CanvasError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not courses:
        print("No se encontraron cursos activos.")
        return 0

    print("Cursos activos:")
    for course in courses:
        course_id = course.get("id", "ID desconocido")
        course_name = course.get("name") or course.get("course_code") or "Sin nombre"
        print(f"- {course_id}: {course_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

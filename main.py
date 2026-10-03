"""CLI temporal para explorar las fuentes de un curso de Canvas."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from canvas_calendar_agent import CanvasClient, CanvasError  # noqa: E402

SAMPLE_SIZE = 3


def course_label(course: dict[str, Any]) -> str:
    return course.get("name") or course.get("course_code") or "Sin nombre"


def print_courses(courses: list[dict[str, Any]]) -> None:
    print("Cursos con matrícula activa (pueden pertenecer a distintos periodos):")
    for number, course in enumerate(courses, start=1):
        published = course.get("published")
        publication = (f"publicado={published}" if published is not None
                       else "publicación no informada")
        print(
            f"{number}. {course_label(course)} | ID={course.get('id', '?')} | "
            f"código={course.get('course_code', '?')} | "
            f"term={course.get('enrollment_term_id', '?')} | "
            f"estado={course.get('workflow_state', '?')} | {publication}"
        )


def choose_course(courses: list[dict[str, Any]]) -> dict[str, Any]:
    while True:
        choice = input("\nElige un curso por número (o 'q' para salir): ").strip()
        if choice.lower() == "q":
            raise KeyboardInterrupt
        try:
            return courses[int(choice) - 1]
        except (ValueError, IndexError):
            print(f"Ingresa un número entre 1 y {len(courses)}.")


def fetch_source(getter: Callable[[int], Any], course_id: int) -> tuple[Any, str | None]:
    try:
        return getter(course_id), None
    except CanvasError as exc:
        return None, str(exc)


def sample_names(items: list[dict[str, Any]], *keys: str) -> list[str]:
    names = []
    for item in items[:SAMPLE_SIZE]:
        value = next((item.get(key) for key in keys if item.get(key)), None)
        names.append(str(value or f"ID {item.get('id', item.get('page_id', '?'))}"))
    return names


def print_source_summary(label: str, result: tuple[Any, str | None],
                         *name_keys: str) -> None:
    items, error = result
    if error:
        print(f"{label}: no disponible ({error})")
        return
    items = items or []
    print(f"{label}: {len(items)}")
    for name in sample_names(items, *name_keys):
        print(f"  - {name}")


def explore_course(client: CanvasClient, course: dict[str, Any]) -> None:
    course_id = int(course["id"])
    sources = {
        "assignments": fetch_source(client.get_assignments, course_id),
        "modules": fetch_source(client.get_modules, course_id),
        "pages": fetch_source(client.get_pages, course_id),
        "files": fetch_source(client.get_files, course_id),
        "events": fetch_source(client.get_calendar_events, course_id),
        "announcements": fetch_source(client.get_announcements, course_id),
        "details": fetch_source(client.get_course_details, course_id),
    }
    print(f"\nCurso seleccionado: {course_label(course)}\n")
    print_source_summary("Assignments", sources["assignments"], "name")
    print_source_summary("Modules", sources["modules"], "name")
    print_source_summary("Pages", sources["pages"], "title", "url")
    print_source_summary("Files", sources["files"], "display_name", "filename")
    print_source_summary("Calendar events", sources["events"], "title")
    print_source_summary("Announcements", sources["announcements"], "title")
    details, details_error = sources["details"]
    if details_error:
        print(f"Syllabus: no disponible ({details_error})")
    else:
        available = bool(details and details.get("syllabus_body"))
        print(f"Syllabus: {'disponible' if available else 'no informado'}")

    modules = sources["modules"][0] or []
    module_items = [item for module in modules for item in module.get("items", [])]
    if module_items:
        types: dict[str, int] = {}
        for item in module_items:
            item_type = str(item.get("type", "Otro"))
            types[item_type] = types.get(item_type, 0) + 1
        breakdown = ", ".join(f"{key}: {value}" for key, value in sorted(types.items()))
        print(f"Items de módulos: {len(module_items)} ({breakdown})")


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        client = CanvasClient(os.getenv("CANVAS_BASE_URL", ""),
                              os.getenv("CANVAS_TOKEN", ""))
        courses = client.get_active_courses()
        if not courses:
            print("No se encontraron cursos con matrícula activa.")
            return 0
        print_courses(courses)
        explore_course(client, choose_course(courses))
    except KeyboardInterrupt:
        print("\nExploración cancelada.")
        return 0
    except CanvasError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

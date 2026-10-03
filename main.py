"""CLI temporal para explorar las fuentes de un curso de Canvas."""

from __future__ import annotations

import os
import sys
import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from canvas_calendar_agent import CanvasClient, CanvasError  # noqa: E402
from canvas_calendar_agent.candidates import build_event_candidates  # noqa: E402
from canvas_calendar_agent.config import load_course_ids, save_course_ids  # noqa: E402
from canvas_calendar_agent.extractors import extract_structured_events  # noqa: E402

SAMPLE_SIZE = 3
CONFIG_PATH = PROJECT_ROOT / "config.json"


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


def choose_course_ids(courses: list[dict[str, Any]]) -> list[int]:
    """Permite elegir varios cursos por los números mostrados."""
    while True:
        raw = input("Elige cursos por número, separados por comas: ").strip()
        try:
            indexes = [int(value.strip()) - 1 for value in raw.split(",")]
            if not indexes or any(index < 0 or index >= len(courses) for index in indexes):
                raise ValueError
            return list(dict.fromkeys(int(courses[index]["id"]) for index in indexes))
        except (ValueError, TypeError, KeyError):
            print(f"Usa números entre 1 y {len(courses)}, por ejemplo: 1,3,4.")


def run_pipeline(client: CanvasClient, courses: list[dict[str, Any]],
                 *, reselect: bool = False) -> None:
    course_ids = [] if reselect else load_course_ids(CONFIG_PATH)
    if not course_ids:
        print_courses(courses)
        course_ids = choose_course_ids(courses)
        save_course_ids(CONFIG_PATH, course_ids)
        print(f"Selección guardada en {CONFIG_PATH.name}.")

    courses_by_id = {int(course["id"]): course for course in courses}
    selected = [courses_by_id[course_id] for course_id in course_ids
                if course_id in courses_by_id]
    missing = [course_id for course_id in course_ids if course_id not in courses_by_id]
    if missing:
        print("Aviso: IDs configurados no visibles: " + ", ".join(map(str, missing)))
    if not selected:
        print("Ningún curso configurado está disponible con la matrícula actual.")
        return

    print(f"Cursos seleccionados: {len(selected)}\n\nRecolectando información...")
    total_events = 0
    total_candidates = 0
    event_sample = []
    candidate_sample = []
    for course in selected:
        course_id = int(course["id"])
        assignments, assignments_error = fetch_source(client.get_assignments, course_id)
        events, events_error = fetch_source(client.get_calendar_events, course_id)
        announcements, announcements_error = fetch_source(client.get_announcements, course_id)
        pages, pages_error = fetch_source(client.get_pages, course_id)
        details, details_error = fetch_source(client.get_course_details, course_id)

        structured = extract_structured_events(
            course, assignments or [], events or []
        )
        candidates = build_event_candidates(
            course, assignments=assignments or [], announcements=announcements or [],
            pages=pages or [], course_details=details or {},
        )
        print(f"\n{course_label(course)}")
        print(f"  Eventos estructurados: {len(structured)}")
        print(f"  Candidatos para agente: {len(candidates)}")
        errors = [
            ("assignments", assignments_error), ("calendar events", events_error),
            ("announcements", announcements_error), ("pages", pages_error),
            ("course details", details_error),
        ]
        for source, error in errors:
            if error:
                print(f"  Fuente no disponible ({source}): {error}")
        total_events += len(structured)
        total_candidates += len(candidates)
        event_sample.extend(structured[: max(0, SAMPLE_SIZE - len(event_sample))])
        candidate_sample.extend(candidates[: max(0, SAMPLE_SIZE - len(candidate_sample))])

    print("\nTotal:")
    print(f"  {total_events} eventos estructurados")
    print(f"  {total_candidates} candidatos pendientes de interpretación")
    if event_sample:
        print("\nMuestra de eventos estructurados:")
        for event in event_sample:
            print(f"  - {event.course_name}: {event.title} — {event.start_at.isoformat()}")
    if candidate_sample:
        print("\nMuestra de candidatos:")
        for candidate in candidate_sample:
            print(f"  - [{candidate.source_type}] {candidate.course_name}: {candidate.title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("explore", "pipeline"),
                        default="explore")
    parser.add_argument("--select-courses", action="store_true",
                        help="vuelve a elegir y guarda los cursos del pipeline")
    args = parser.parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        client = CanvasClient(os.getenv("CANVAS_BASE_URL", ""),
                              os.getenv("CANVAS_TOKEN", ""))
        courses = client.get_active_courses()
        if not courses:
            print("No se encontraron cursos con matrícula activa.")
            return 0
        if args.mode == "pipeline":
            run_pipeline(client, courses, reselect=args.select_courses)
        else:
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

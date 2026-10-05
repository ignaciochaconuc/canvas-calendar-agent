"""CLI temporal para explorar las fuentes de un curso de Canvas."""

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from canvas_calendar_agent import CanvasClient, CanvasError  # noqa: E402
from canvas_calendar_agent.candidates import build_event_candidates  # noqa: E402
from canvas_calendar_agent.config import (group_courses_by_term, load_course_ids, load_semester,
                                           save_course_ids, save_semester)  # noqa: E402
from canvas_calendar_agent.extractors import extract_structured_events  # noqa: E402
from canvas_calendar_agent.documents import (extract_pdf, extract_spreadsheet, file_candidates,
                                              is_relevant_file, spreadsheet_candidates)  # noqa: E402
from canvas_calendar_agent.file_cache import FileCache  # noqa: E402
from canvas_calendar_agent.year_resolution import resolve_event_year  # noqa: E402
from canvas_calendar_agent.consolidation import analysis_to_events, consolidate_events, discard_event, edit_event  # noqa: E402
from canvas_calendar_agent.review_store import (load_academic_events, load_events, load_json,
                                                 save_academic_events, save_events, save_json)  # noqa: E402
from canvas_calendar_agent.automation import apply_review_decisions, is_safe_for_auto_sync  # noqa: E402
from canvas_calendar_agent.conflict_resolution import process_conflicts, resolve_conflicts  # noqa: E402
from canvas_calendar_agent.importance import apply_importance, process_needs_review  # noqa: E402

SAMPLE_SIZE = 3
CONFIG_PATH = PROJECT_ROOT / "config.json"
CACHE_PATH = PROJECT_ROOT / ".cache" / "canvas_files"
REVIEW_PATH = PROJECT_ROOT / "review_events.json"
SYNC_PATH = PROJECT_ROOT / "calendar_sync.json"
CALENDAR_CONFIG_PATH = PROJECT_ROOT / "calendar_config.json"
GOOGLE_CREDENTIALS_PATH = PROJECT_ROOT / "google_credentials.json"
GOOGLE_TOKEN_PATH = PROJECT_ROOT / "google_token.json"
DETECTED_PATH = PROJECT_ROOT / "detected_events.json"


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


def run_agent_mode(client: CanvasClient, courses: list[dict[str, Any]]) -> None:
    """Permite interpretar manualmente un único candidato mediante el agente."""
    course_ids = load_course_ids(CONFIG_PATH)
    if not course_ids:
        print("No hay cursos configurados. Ejecuta primero: python main.py pipeline")
        return
    courses_by_id = {int(course["id"]): course for course in courses}
    candidates = []
    for course_id in course_ids:
        course = courses_by_id.get(course_id)
        if not course:
            continue
        assignments, _ = fetch_source(client.get_assignments, course_id)
        announcements, _ = fetch_source(client.get_announcements, course_id)
        pages, _ = fetch_source(client.get_pages, course_id)
        details, _ = fetch_source(client.get_course_details, course_id)
        candidates.extend(build_event_candidates(
            course, assignments=assignments or [], announcements=announcements or [],
            pages=pages or [], course_details=details or {},
        ))
    if not candidates:
        print("No se encontraron candidatos para interpretar.")
        return

    visible = candidates[:10]
    print("Candidatos:\n")
    for number, candidate in enumerate(visible, start=1):
        print(f"{number}. [{candidate.source_type}] {candidate.title}")
    while True:
        raw = input("\nSelecciona un candidato (o 'q' para salir): ").strip()
        if raw.lower() == "q":
            return
        try:
            candidate = visible[int(raw) - 1]
            break
        except (ValueError, IndexError):
            print(f"Ingresa un número entre 1 y {len(visible)}.")

    # Import tardío: los otros modos no inicializan el componente experimental.
    from canvas_calendar_agent.agent import check_model_available, interpret_candidate

    check_model_available()
    result = interpret_candidate(candidate)
    course = courses_by_id.get(candidate.course_id, {})
    result = result.model_copy(update={
        "events": [resolve_event_year(event, course) for event in result.events]
    })
    detected = load_academic_events(DETECTED_PATH)
    detected.extend(analysis_to_events(result, candidate, course))
    save_academic_events(DETECTED_PATH, detected)
    print("\nResultado:\n")
    for field, value in result.model_dump(mode="json").items():
        print(f"{field}: {value}")


def _choose_many(count: int, prompt: str) -> list[int]:
    while True:
        raw = input(prompt).strip()
        if raw.lower() == "q":
            return []
        try:
            values = list(dict.fromkeys(int(item.strip()) - 1 for item in raw.split(",")))
            if not values or any(value < 0 or value >= count for value in values):
                raise ValueError
            return values
        except ValueError:
            print(f"Usa números entre 1 y {count}, separados por comas.")


def run_files_mode(client: CanvasClient, courses: list[dict[str, Any]], *, use_agent: bool) -> None:
    """Descarga únicamente PDFs relevantes elegidos manualmente."""
    selected_ids = load_course_ids(CONFIG_PATH)
    selected = [course for course in courses if int(course["id"]) in selected_ids]
    if not selected:
        print("No hay cursos configurados. Ejecuta primero: python main.py pipeline")
        return
    max_bytes = int(float(os.getenv("MAX_FILE_SIZE_MB", "20")) * 1024 * 1024)
    choices: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for course in selected:
        files, error = fetch_source(client.get_files, int(course["id"]))
        if error:
            print(f"{course_label(course)}: no se pudieron listar archivos ({error})")
            continue
        choices.extend((course, file) for file in files if is_relevant_file(file, max_bytes=max_bytes))
    if not choices:
        print("No se encontraron PDFs relevantes dentro del límite configurado.")
        return
    print("Archivos PDF relevantes:\n")
    for number, (course, file) in enumerate(choices, 1):
        name = str(file.get('display_name') or file.get('filename'))
        kind = "XLS" if name.lower().endswith(".xls") else ("XLSX" if name.lower().endswith(".xlsx") else "PDF")
        print(f"{number}. [{kind}] {course_label(course)} | {name} | "
              f"{file.get('content-type', '?')} | {file.get('size', '?')} bytes")
    indexes = _choose_many(len(choices), "\nSelecciona archivos (ej. 1,3; q para salir): ")
    cache = FileCache(CACHE_PATH)
    candidates = []
    for index in indexes:
        course, file = choices[index]
        path = cache.get(file) or client.download_file(file, cache.path_for(file), max_bytes=max_bytes)
        filename = str(file.get("display_name") or file.get("filename"))
        if filename.lower().endswith((".xlsx",".xls")):
            document = extract_spreadsheet(path, filename=filename)
            generated = spreadsheet_candidates(document, file, course)
            detail = f"{len(document.sheet_names)} hojas"
        else:
            document = extract_pdf(path, filename=filename)
            generated = file_candidates(document, file, course)
            detail = f"{document.page_count} páginas"
        candidates.extend(generated)
        print(f"{document.filename}: {detail}, {len(generated)} bloques relevantes")
    if not use_agent or not candidates:
        return
    print("\nCandidatos de archivo:")
    for number, candidate in enumerate(candidates, 1):
        print(f"{number}. {candidate.title}")
    selected_candidate = _choose_many(len(candidates), "Elige UN candidato para el agente: ")
    if not selected_candidate:
        return
    candidate = candidates[selected_candidate[0]]
    from canvas_calendar_agent.agent import check_model_available, interpret_candidate
    check_model_available()
    result = interpret_candidate(candidate)
    course = next((item for item in courses if int(item["id"]) == candidate.course_id), {})
    result = result.model_copy(update={
        "events": [resolve_event_year(event, course) for event in result.events]
    })
    detected = load_academic_events(DETECTED_PATH)
    detected.extend(analysis_to_events(result, candidate, course))
    save_academic_events(DETECTED_PATH, detected)
    print(result.model_dump_json(indent=2))


def _show_review(events) -> None:
    for number, event in enumerate(events, 1):
        when = event.start_at.strftime("%d/%m/%Y %H:%M") if event.start_at else "fecha pendiente"
        print(f"{number}. [{event.status.upper()}] {event.course_name} — {event.title} — {when}")
        print("   fuentes: " + ", ".join(source.label for source in event.sources))
        if event.status == "conflict":
            for index, value in enumerate(event.alternatives, 1):
                print(f"   opción {index}: {value.isoformat() if value else 'sin fecha'}")


def run_review(client: CanvasClient, courses: list[dict[str, Any]]) -> None:
    academic = []
    selected = set(load_course_ids(CONFIG_PATH))
    for course in courses:
        if int(course["id"]) not in selected: continue
        assignments, _ = fetch_source(client.get_assignments, int(course["id"]))
        calendar, _ = fetch_source(client.get_calendar_events, int(course["id"]))
        academic.extend(extract_structured_events(course, assignments or [], calendar or []))
    academic.extend(load_academic_events(DETECTED_PATH))
    events = load_events(REVIEW_PATH) or consolidate_events(academic)
    _show_review(events)
    while events:
        raw = input("\nAcción: a N aprobar, r N resolver conflicto, e N editar, d N descartar, g guardar: ").strip().lower()
        if raw == "g": break
        try: action, number = raw.split(); index = int(number) - 1; event = events[index]
        except (ValueError, IndexError):
            print("Formato inválido."); continue
        if action == "a" and event.start_at: event.status = "approved"; event.manual_approval = True
        elif action == "d": events[index] = discard_event(event)
        elif action == "r" and event.status == "conflict":
            resolve_conflicts([event])
        elif action == "e":
            value = input("Fecha/hora ISO (ej. 2026-09-24T17:30:00-03:00): ").strip()
            try: events[index] = edit_event(event, start_at=datetime.fromisoformat(value))
            except ValueError: print("Fecha inválida.")
        else: print("La acción no es aplicable.")
    save_events(REVIEW_PATH, events); print(f"Revisión guardada en {REVIEW_PATH.name}.")


def run_calendar_auth() -> None:
    from canvas_calendar_agent.calendar_google import CALENDAR_NAME, authorize, ensure_calendar
    if not GOOGLE_CREDENTIALS_PATH.exists():
        raise ValueError("Falta google_credentials.json descargado desde Google Cloud.")
    previous=load_json(CALENDAR_CONFIG_PATH)
    if previous: print(f"Calendario configurado actualmente: {previous.get('calendar_name','?')} ({previous.get('calendar_id','?')})")
    service = authorize(GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH)
    calendar_id = ensure_calendar(service,CALENDAR_NAME)
    registry=load_json(SYNC_PATH); old_id=previous.get("calendar_id")
    for key,value in list(registry.items()):
        if len(key)==64 and old_id: registry.setdefault(f"{old_id}:{key}",value)
    save_json(SYNC_PATH,registry)
    previous.update({"calendar_id": calendar_id, "calendar_name": CALENDAR_NAME})
    save_json(CALENDAR_CONFIG_PATH, previous)
    if old_id and old_id != calendar_id: print("ADVERTENCIA: Hay eventos sincronizados asociados a otro calendar_id; no se recrearán automáticamente.")
    print(f'OAuth completado y calendario "{CALENDAR_NAME}" seleccionado.')

def run_calendar_status() -> None:
    from canvas_calendar_agent.calendar_google import authorize, calendar_status
    config=load_json(CALENDAR_CONFIG_PATH)
    if not config.get("calendar_id"): raise ValueError("Ejecuta primero: python main.py calendar-auth")
    service=authorize(GOOGLE_CREDENTIALS_PATH,GOOGLE_TOKEN_PATH)
    status=calendar_status(service,config["calendar_id"]); entry=status["configured"] or {}
    print(f"Cuenta: {status['account'] or 'no informada por la API'}")
    print(f"Calendario configurado: {config.get('calendar_name','?')}\ncalendar_id: {config['calendar_id']}")
    print(f"Access role: {entry.get('accessRole','no disponible')}\nEn calendarList: {'sí' if status['in_calendar_list'] else 'no'}")
    print("Últimos eventos devueltos por la API:")
    if not status["events"]: print("  (sin eventos)")
    for event in status["events"]:
        start=event.get("start",{}).get("dateTime") or event.get("start",{}).get("date") or "sin fecha"
        print(f"  - {event.get('summary','Sin título')} | {start} | event_id={event.get('id','?')}")


def run_calendar_sync(*, auto: bool = False) -> None:
    from canvas_calendar_agent.calendar_google import authorize, google_event_payload, sync_approved
    threshold=float(os.getenv("AGENT_AUTO_APPROVE_CONFIDENCE","0.9"))
    events = [event for event in load_events(REVIEW_PATH)
              if (is_safe_for_auto_sync(event, agent_threshold=threshold) if auto
                  else event.status == "approved" and event.start_at is not None)]
    registry = load_json(SYNC_PATH); config = load_json(CALENDAR_CONFIG_PATH)
    pending = [event for event in events if __import__('canvas_calendar_agent.calendar_google', fromlist=['sync_key']).sync_key(event) not in registry]
    if not pending: print("No hay eventos aprobados pendientes de sincronización."); return
    print(f'Se crearán {len(pending)} eventos en "{config.get("calendar_name", "🎓 UC")}".')
    for number, event in enumerate(pending, 1): print(f"{number}. {google_event_payload(event)['summary']} — {event.start_at.isoformat()}")
    if not auto and input("¿Continuar? [s/N] ").strip().lower() != "s": print("Sin cambios."); return
    service = authorize(GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH)
    registry = sync_approved(service, config["calendar_id"], pending, registry, confirmed=True)
    save_json(SYNC_PATH, registry); print(f"Creados: {len(pending)}.")

def run_semester_setup(courses: list[dict[str, Any]]) -> None:
    groups=group_courses_by_term(courses)
    print("Periodos encontrados:")
    ordered=sorted(groups.items(), key=lambda pair: pair[0], reverse=True)
    for number,(term_id,items) in enumerate(ordered,1):
        print(f"{number}. term {term_id}")
        for course in items: print(f"   - {course_label(course)}")
    choice=int(input("Elige un periodo por número: "))-1
    term_id,items=ordered[choice]
    label=input("Etiqueta del semestre (ej. 2026-2): ").strip()
    save_semester(CONFIG_PATH,term_id,[int(c["id"]) for c in items],label)
    print(f"Guardados {len(items)} cursos para {label}.")

def run_sync_all(client: CanvasClient, courses: list[dict[str, Any]], *, non_interactive: bool = False) -> None:
    from canvas_calendar_agent.calendar_google import CALENDAR_NAME, authorize, ensure_calendar, registry_calendar_ids, sync_approved, sync_key
    semester=load_semester(CONFIG_PATH); selected_ids=set(semester["course_ids"])
    selected=[c for c in courses if int(c["id"]) in selected_ids]
    academic=[]; relevant_files=0
    for course in selected:
        assignments,_=fetch_source(client.get_assignments,int(course["id"])); calendar,_=fetch_source(client.get_calendar_events,int(course["id"]))
        academic.extend(extract_structured_events(course,assignments or [],calendar or []))
        files,_=fetch_source(client.get_files,int(course["id"])); relevant_files += sum(is_relevant_file(f) for f in (files or []))
    academic.extend(e for e in load_academic_events(DETECTED_PATH) if e.course_id in selected_ids)
    consolidated=consolidate_events(academic); apply_review_decisions(consolidated,load_events(REVIEW_PATH)); apply_importance(consolidated)
    threshold=float(os.getenv("AGENT_AUTO_APPROVE_CONFIDENCE","0.9"))
    safe=[e for e in consolidated if is_safe_for_auto_sync(e,agent_threshold=threshold)]
    for event in safe: event.status="approved"
    service=authorize(GOOGLE_CREDENTIALS_PATH,GOOGLE_TOKEN_PATH)
    name=CALENDAR_NAME; calendar_id=ensure_calendar(service,name)
    config=load_json(CALENDAR_CONFIG_PATH); config.update({"calendar_id":calendar_id,"calendar_name":name}); save_json(CALENDAR_CONFIG_PATH,config)
    registry=load_json(SYNC_PATH); prefix=calendar_id+":"
    foreign=registry_calendar_ids(registry)-{calendar_id}
    foreign_hashes={key[-64:] for key in registry if len(key)>65 and key[-65]==":" and key[:-65] in foreign}
    migration=[e for e in safe if sync_key(e) in foreign_hashes and prefix+sync_key(e) not in registry]
    allow_migration=False
    if migration:
        print("ADVERTENCIA: Hay eventos sincronizados asociados a otro calendar_id.")
        if not non_interactive: allow_migration=input("¿Recrear esos eventos en 🎓 UC? [s/N] ").strip().lower()=="s"
    new=[e for e in safe if prefix+sync_key(e) not in registry and (e not in migration or allow_migration)]
    existing=len(safe)-len(new)
    sync_approved(service,calendar_id,new,registry,confirmed=True,namespace_calendar=True,calendar_name=name)
    conflict_stats=process_conflicts(consolidated,non_interactive=non_interactive)
    review_stats=process_needs_review(consolidated,non_interactive=non_interactive)
    manually_approved=[e for e in consolidated if e.status=="approved" and e not in safe
                       and prefix+sync_key(e) not in registry]
    if manually_approved:
        sync_approved(service,calendar_id,manually_approved,registry,confirmed=True,namespace_calendar=True,calendar_name=name)
        new.extend(manually_approved)
    save_events(REVIEW_PATH,consolidated); save_json(SYNC_PATH,registry)
    print(f"\nSincronización completada — {semester['semester_label']}\n")
    print(f"Cursos revisados: {len(selected)}\nCreados: {len(new)}\nYa existentes: {existing}")
    print(f"Pendientes: {sum(e.status=='pending' for e in consolidated)}")
    print(f"Conflictos resueltos: {conflict_stats['resolved']}")
    print(f"Conflictos pendientes: {sum(e.status=='conflict' for e in consolidated)}")
    print(f"Necesitan revisión: {sum(e.status=='needs_review' for e in consolidated)}")
    print(f"Descartados: {sum(e.status=='discarded' for e in consolidated)}")
    print(f"Ignorados: {sum(not is_safe_for_auto_sync(e,agent_threshold=threshold) for e in consolidated)}")
    print(f"Archivos relevantes conocidos: {relevant_files}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("explore", "pipeline", "agent", "files", "review", "calendar-auth", "calendar-sync", "calendar-status", "semester-setup", "sync-all"),
                        default="explore")
    parser.add_argument("--select-courses", action="store_true",
                        help="vuelve a elegir y guarda los cursos del pipeline")
    parser.add_argument("--agent", action="store_true",
                        help="en modo files, interpreta un único bloque elegido")
    parser.add_argument("--auto", action="store_true", help="sincroniza eventos seguros sin confirmación")
    parser.add_argument("--non-interactive", action="store_true",
                        help="en sync-all, omite conflictos sin solicitar input")
    args = parser.parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        if args.mode == "calendar-auth": run_calendar_auth(); return 0
        if args.mode == "calendar-sync": run_calendar_sync(auto=args.auto); return 0
        if args.mode == "calendar-status": run_calendar_status(); return 0
        client = CanvasClient(os.getenv("CANVAS_BASE_URL", ""),
                              os.getenv("CANVAS_TOKEN", ""))
        courses = client.get_active_courses()
        if not courses:
            print("No se encontraron cursos con matrícula activa.")
            return 0
        if args.mode == "pipeline":
            run_pipeline(client, courses, reselect=args.select_courses)
        elif args.mode == "agent":
            run_agent_mode(client, courses)
        elif args.mode == "files":
            run_files_mode(client, courses, use_agent=args.agent)
        elif args.mode == "review":
            run_review(client, courses)
        elif args.mode == "semester-setup":
            run_semester_setup(courses)
        elif args.mode == "sync-all":
            run_sync_all(client,courses,non_interactive=args.non_interactive)
        else:
            print_courses(courses)
            explore_course(client, choose_course(courses))
    except KeyboardInterrupt:
        print("\nExploración cancelada.")
        return 0
    except (CanvasError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

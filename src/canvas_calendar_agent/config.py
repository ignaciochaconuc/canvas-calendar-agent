"""Persistencia local de la selección de cursos, nunca de credenciales."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def group_courses_by_term(courses: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for course in courses:
        term_id = course.get("enrollment_term_id")
        if isinstance(term_id, int): groups.setdefault(term_id, []).append(course)
    return groups

def save_semester(path: Path, term_id: int, course_ids: list[int], label: str) -> None:
    path.write_text(json.dumps({"term_id": term_id, "course_ids": course_ids,
                                "semester_label": label}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def load_semester(path: Path) -> dict[str, Any]:
    if not path.exists(): raise ValueError("Ejecuta primero: python main.py semester-setup")
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("term_id"),int) or not data.get("course_ids") or not str(data.get("semester_label","")).strip():
        raise ValueError("La configuración de semestre está incompleta.")
    return data


def load_course_ids(path: Path) -> list[int]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer la configuración: {exc}") from exc
    values = data.get("course_ids") if isinstance(data, dict) else None
    if not isinstance(values, list) or not all(
        isinstance(value, int) and not isinstance(value, bool) and value > 0
        for value in values
    ):
        raise ValueError("config.json debe contener una lista 'course_ids' de enteros positivos.")
    return list(dict.fromkeys(values))


def save_course_ids(path: Path, course_ids: list[int]) -> None:
    unique_ids = list(dict.fromkeys(course_ids))
    if not unique_ids or not all(
        isinstance(value, int) and not isinstance(value, bool) and value > 0
        for value in unique_ids
    ):
        raise ValueError("Debes seleccionar al menos un ID de curso válido.")
    path.write_text(
        json.dumps({"course_ids": unique_ids}, indent=2) + "\n", encoding="utf-8"
    )

"""Persistencia local de la selección de cursos, nunca de credenciales."""

from __future__ import annotations

import json
from pathlib import Path


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

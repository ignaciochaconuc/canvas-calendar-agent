"""Persistencia JSON local de eventos revisados y registro de sincronización."""

from __future__ import annotations
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from .models import AcademicEvent, ConsolidatedEvent, EventSource

def save_events(path: Path, events: list[ConsolidatedEvent]) -> None:
    data = []
    for event in events:
        item = asdict(event)
        for key in ("start_at", "end_at"):
            item[key] = item[key].isoformat() if item[key] else None
        item["alternatives"] = [value.isoformat() if value else None for value in event.alternatives]
        data.append(item)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_events(path: Path) -> list[ConsolidatedEvent]:
    if not path.exists(): return []
    data = json.loads(path.read_text(encoding="utf-8")); result = []
    for item in data:
        item["start_at"] = datetime.fromisoformat(item["start_at"]) if item["start_at"] else None
        item["end_at"] = datetime.fromisoformat(item["end_at"]) if item["end_at"] else None
        item["alternatives"] = [datetime.fromisoformat(v) if v else None for v in item.get("alternatives", [])]
        item["sources"] = [EventSource(**source) for source in item["sources"]]
        result.append(ConsolidatedEvent(**item))
    return result

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

def save_academic_events(path: Path, events: list[AcademicEvent]) -> None:
    data=[]
    for event in events:
        item=asdict(event)
        item["start_at"]=event.start_at.isoformat() if event.start_at else None
        item["end_at"]=event.end_at.isoformat() if event.end_at else None
        data.append(item)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_academic_events(path: Path) -> list[AcademicEvent]:
    if not path.exists(): return []
    result=[]
    for item in json.loads(path.read_text(encoding="utf-8")):
        item["start_at"]=datetime.fromisoformat(item["start_at"]) if item["start_at"] else None
        item["end_at"]=datetime.fromisoformat(item["end_at"]) if item["end_at"] else None
        result.append(AcademicEvent(**item))
    return result

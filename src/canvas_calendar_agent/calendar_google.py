"""OAuth y escritura explícita en un calendario separado de Google."""

from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from .consolidation import normalize_title
from .models import ConsolidatedEvent

TZ = "America/Santiago"
CALENDAR_NAME = "🎓 UC"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def sync_key(event: ConsolidatedEvent) -> str:
    source_ids = sorted(f"{s.source_type}:{s.source_id}" for s in event.sources if s.source_id)
    raw = "|".join([str(event.course_id), normalize_title(event.title),
                    event.start_at.isoformat() if event.start_at else "", *source_ids])
    return hashlib.sha256(raw.encode()).hexdigest()

def google_event_payload(event: ConsolidatedEvent) -> dict[str, Any]:
    if event.start_at is None: raise ValueError("El evento no tiene fecha resuelta.")
    links = [source.url for source in event.sources if source.url]
    description = "\n".join(filter(None, [f"Tipo: {event.event_type}", event.description,
        "Fuentes: " + ", ".join(source.label for source in event.sources), *links]))
    payload: dict[str, Any] = {
        "summary": f"[{event.course_name}] {event.title}", "description": description,
        "reminders": {"useDefault": False, "overrides": [
            {"method": "popup", "minutes": 10080}, {"method": "popup", "minutes": 1440}]}}
    if event.all_day:
        payload["start"] = {"date": event.start_at.date().isoformat()}
        end = event.end_at.date() if event.end_at else event.start_at.date()
        payload["end"] = {"date": (end + timedelta(days=1)).isoformat()}
    else:
        start = event.start_at.astimezone(ZoneInfo(TZ))
        end = event.end_at.astimezone(ZoneInfo(TZ)) if event.end_at else _default_timed_end(start)
        payload["start"] = {"dateTime": start.isoformat(), "timeZone": TZ}
        payload["end"] = {"dateTime": end.isoformat(), "timeZone": TZ}
    return payload

def _default_timed_end(start: datetime) -> datetime:
    """Da una hora de duración sin invadir el día siguiente."""
    proposed=start+timedelta(hours=1)
    day_end=datetime.combine(start.date(),time.max,tzinfo=start.tzinfo)
    return min(proposed,day_end)

def authorize(credentials_path: Path, token_path: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    credentials = Credentials.from_authorized_user_file(token_path, SCOPES) if token_path.exists() else None
    if credentials and credentials.expired and credentials.refresh_token: credentials.refresh(Request())
    if not credentials or not credentials.valid:
        credentials = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES).run_local_server(port=0)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=credentials)

def ensure_calendar(service, name: str = "🎓 UC") -> str:
    for item in service.calendarList().list().execute().get("items", []):
        if item.get("summary") == name: return item["id"]
    return service.calendars().insert(body={"summary": name, "timeZone": TZ}).execute()["id"]

def semester_calendar_name(label: str) -> str:
    """Compatibilidad: el semestre ya no modifica el calendario de destino."""
    return CALENDAR_NAME

def registry_calendar_ids(registry: dict[str, str]) -> set[str]:
    ids=set()
    for key in registry:
        if len(key) > 65 and key[-65] == ":": ids.add(key[:-65])
    return ids

def calendar_status(service, calendar_id: str) -> dict[str, Any]:
    entries=service.calendarList().list().execute().get("items",[])
    entry=next((item for item in entries if item.get("id")==calendar_id),None)
    primary=next((item for item in entries if item.get("primary")),None)
    events=service.events().list(calendarId=calendar_id,maxResults=10,
        singleEvents=True,orderBy="updated").execute().get("items",[])
    return {"account": primary.get("id") if primary else None,
            "configured": entry, "in_calendar_list": entry is not None, "events": events}

def sync_approved(service, calendar_id: str, events: list[ConsolidatedEvent], registry: dict[str, str], *, confirmed: bool,
                  namespace_calendar: bool = False, calendar_name: str = CALENDAR_NAME,
                  output=print) -> dict[str, str]:
    if not confirmed: return registry
    for event in events:
        key = (calendar_id + ":" if namespace_calendar else "") + sync_key(event)
        if event.status == "approved" and key not in registry:
            created = service.events().insert(calendarId=calendar_id, body=google_event_payload(event)).execute()
            event_id=created.get("id")
            if not event_id: raise ValueError("Google creó una respuesta sin event_id.")
            registry[key] = event_id
            when=event.start_at.astimezone(ZoneInfo(TZ)).strftime("%Y-%m-%d %H:%M")
            output(f"CREADO:\n[{event.course_name}] {event.title}\n{when}\nGoogle event_id: {event_id}\nCalendario: {calendar_name}")
    return registry

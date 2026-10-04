"""OAuth y escritura explícita en un calendario separado de Google."""

from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from .consolidation import normalize_title
from .models import ConsolidatedEvent

TZ = "America/Santiago"
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
            {"method": "email", "minutes": 10080}, {"method": "popup", "minutes": 1440}]}}
    if event.all_day:
        payload["start"] = {"date": event.start_at.date().isoformat()}
        end = event.end_at.date() if event.end_at else event.start_at.date()
        from datetime import timedelta
        payload["end"] = {"date": (end + timedelta(days=1)).isoformat()}
    else:
        start = event.start_at.astimezone(ZoneInfo(TZ))
        from datetime import timedelta
        end = (event.end_at or event.start_at + timedelta(hours=1)).astimezone(ZoneInfo(TZ))
        payload["start"] = {"dateTime": start.isoformat(), "timeZone": TZ}
        payload["end"] = {"dateTime": end.isoformat(), "timeZone": TZ}
    return payload

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

def sync_approved(service, calendar_id: str, events: list[ConsolidatedEvent], registry: dict[str, str], *, confirmed: bool) -> dict[str, str]:
    if not confirmed: return registry
    for event in events:
        key = sync_key(event)
        if event.status == "approved" and key not in registry:
            created = service.events().insert(calendarId=calendar_id, body=google_event_payload(event)).execute()
            registry[key] = created["id"]
    return registry

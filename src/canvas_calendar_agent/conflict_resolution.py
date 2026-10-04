"""Presentación y resolución manual reutilizable de conflictos."""

from __future__ import annotations
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo
from .consolidation import discard_event, edit_event
from .models import ConsolidatedEvent

TZ = ZoneInfo("America/Santiago")

def _format(value: datetime | None) -> tuple[str, str]:
    if value is None: return "sin fecha", "sin hora"
    local=value.astimezone(TZ)
    return local.strftime("%d/%m/%Y"), local.strftime("%H:%M")

def show_conflict(event: ConsolidatedEvent, number: int, total: int,
                  output: Callable[[str], None] = print) -> None:
    output(f"\nCONFLICTO {number}/{total}\n\nCurso: {event.course_name}\nEvento: {event.title}")
    for index,value in enumerate(event.alternatives,1):
        source=event.sources[index-1].label if index <= len(event.sources) else "Fuente desconocida"
        date_text,time_text=_format(value)
        output(f"\nAlternativa {index}\nFuente: {source}\nFecha: {date_text}\nHora: {time_text}")

def _manual_datetime(input_fn: Callable[[str], str], output: Callable[[str], None]) -> tuple[datetime, bool] | None:
    date_text=input_fn("Fecha (DD/MM/AAAA): ").strip()
    time_text=input_fn("Hora opcional (HH:MM): ").strip()
    try:
        parsed=datetime.strptime(date_text,"%d/%m/%Y")
        if time_text:
            clock=datetime.strptime(time_text,"%H:%M").time()
            parsed=parsed.replace(hour=clock.hour,minute=clock.minute)
        return parsed.replace(tzinfo=TZ), not bool(time_text)
    except ValueError:
        output("Formato inválido; el conflicto permanece pendiente.")
        return None

def resolve_conflicts(events: list[ConsolidatedEvent], *,
                      input_fn: Callable[[str], str] = input,
                      output: Callable[[str], None] = print) -> dict[str, int]:
    conflicts=[event for event in events if event.status=="conflict"]
    stats={"resolved":0,"discarded":0,"skipped":0}
    for number,event in enumerate(conflicts,1):
        show_conflict(event,number,len(conflicts),output)
        choice=input_fn("\nElige alternativa, e editar, d descartar, s saltar: ").strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(event.alternatives):
            chosen=event.alternatives[int(choice)-1]
            if chosen is not None:
                updated=edit_event(event,start_at=chosen)
                event.start_at,event.all_day,event.status,event.alternatives=(updated.start_at,updated.all_day,
                    updated.status,updated.alternatives); stats["resolved"]+=1; continue
        elif choice=="e":
            manual=_manual_datetime(input_fn,output)
            if manual:
                chosen,all_day=manual
                updated=edit_event(event,start_at=chosen,all_day=all_day)
                event.start_at,event.all_day,event.status,event.alternatives=(updated.start_at,updated.all_day,
                    updated.status,updated.alternatives); stats["resolved"]+=1; continue
        elif choice=="d":
            event.status=discard_event(event).status; stats["discarded"]+=1; continue
        stats["skipped"]+=1
    return stats

def process_conflicts(events: list[ConsolidatedEvent], *, non_interactive: bool,
                      input_fn: Callable[[str], str] = input,
                      output: Callable[[str], None] = print) -> dict[str, int]:
    count=sum(event.status=="conflict" for event in events)
    if non_interactive:
        output(f"Conflictos que necesitan revisión: {count}")
        return {"resolved":0,"discarded":0,"skipped":count}
    return resolve_conflicts(events,input_fn=input_fn,output=output)

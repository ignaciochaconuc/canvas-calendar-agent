"""Clasificación conservadora de importancia académica."""

from __future__ import annotations
import re
from collections.abc import Callable
from .consolidation import normalize_title
from .models import ConsolidatedEvent

IMPORTANT_WORDS=("examen","prueba","interrogacion","tarea","entrega","proyecto","control","quiz","deadline","fecha limite")
NON_EVALUATIVE=("clase","ayudantia","laboratorio","charla","sesion","reunion","horario","lecture","class","encuesta docente")
ALTERNATIVE_CONTEXT=("fecha alternativa","fechas alternativas","elegir una","una de las fechas","solo debe asistir")

def _contains(text: str, phrase: str) -> bool:
    return bool(re.search(rf"\b{re.escape(phrase)}\b",text))

def classify_importance(event: ConsolidatedEvent) -> str:
    title=normalize_title(event.title); context=normalize_title(" ".join(filter(None,[event.course_name,event.title,event.description])))
    if any(phrase in context for phrase in ALTERNATIVE_CONTEXT): return "uncertain"
    if _contains(title,"presentacion"):
        if event.event_type in {"assignment","project"} or any(_contains(context,word) for word in ("evaluacion","evaluada","entrega","proyecto")): return "important"
        return event.agent_importance or "not_important"
    if any(_contains(title,word) for word in IMPORTANT_WORDS): return "important"
    if any(_contains(title,word) for word in NON_EVALUATIVE): return "not_important"
    tokens=title.split()
    if tokens and not any(len(token)>3 and token.isalpha() for token in tokens): return "uncertain"
    if event.event_type in {"exam","quiz","assignment","project","deadline"}: return "important"
    return event.agent_importance or "uncertain"

def apply_importance(events: list[ConsolidatedEvent]) -> None:
    for event in events:
        if event.status in {"discarded","conflict","pending"} or (event.status=="approved" and event.manual_approval): continue
        event.status="approved" if classify_importance(event)=="important" else "needs_review"

def review_needs_review(events: list[ConsolidatedEvent], *, input_fn: Callable[[str],str]=input,
                        output: Callable[[str],None]=print) -> dict[str,int]:
    items=[event for event in events if event.status=="needs_review"]
    if not items: return {"approved":0,"discarded":0,"remaining":0}
    output("\nEVENTOS QUE NECESITAN REVISIÓN")
    for number,event in enumerate(items,1): output(f"{number}. [{event.course_name}] {event.title}")
    raw=input_fn("Aprobar (a 1,3), descartar (d 2,4) o saltar (s): ").strip().lower()
    if raw=="s" or not raw: return {"approved":0,"discarded":0,"remaining":len(items)}
    try:
        action,values=raw.split(maxsplit=1); indexes={int(v.strip())-1 for v in values.split(",")}
        if action not in {"a","d"} or any(i<0 or i>=len(items) for i in indexes): raise ValueError
    except ValueError:
        output("Selección inválida; quedan pendientes."); return {"approved":0,"discarded":0,"remaining":len(items)}
    for index in indexes:
        items[index].status="approved" if action=="a" else "discarded"
        items[index].manual_approval=action=="a"
    return {"approved":len(indexes) if action=="a" else 0,
            "discarded":len(indexes) if action=="d" else 0,
            "remaining":sum(item.status=="needs_review" for item in items)}

def process_needs_review(events: list[ConsolidatedEvent], *, non_interactive: bool,
                         input_fn: Callable[[str],str]=input,
                         output: Callable[[str],None]=print) -> dict[str,int]:
    count=sum(event.status=="needs_review" for event in events)
    if non_interactive:
        output(f"Eventos que necesitan revisión: {count}")
        return {"approved":0,"discarded":0,"remaining":count}
    return review_needs_review(events,input_fn=input_fn,output=output)

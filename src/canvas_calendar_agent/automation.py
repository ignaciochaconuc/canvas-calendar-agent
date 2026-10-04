"""Política conservadora de auto-aprobación para la sincronización v2."""

from __future__ import annotations
from .models import ConsolidatedEvent

def is_safe_for_auto_sync(event: ConsolidatedEvent, *, agent_threshold: float = 0.9) -> bool:
    if event.status in {"pending", "conflict", "discarded"} or event.start_at is None:
        return False
    source_types={source.source_type for source in event.sources}
    if source_types <= {"assignment", "calendar_event"}: return True
    if "file" in source_types: return event.confidence >= agent_threshold
    return event.status == "approved"

def apply_review_decisions(events: list[ConsolidatedEvent], reviewed: list[ConsolidatedEvent]) -> None:
    decisions={frozenset((s.source_type,s.source_id) for s in item.sources): item
               for item in reviewed if item.status in {"discarded","approved"}}
    for event in events:
        key=frozenset((s.source_type,s.source_id) for s in event.sources)
        if key in decisions:
            decision=decisions[key]; event.status=decision.status
            if decision.status=="approved":
                event.start_at,event.end_at,event.all_day=(decision.start_at,decision.end_at,decision.all_day)

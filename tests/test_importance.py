import sys, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from canvas_calendar_agent.automation import is_safe_for_auto_sync
from canvas_calendar_agent.importance import apply_importance, classify_importance, process_needs_review, review_needs_review
from canvas_calendar_agent.models import ConsolidatedEvent, EventSource

def item(title,event_type='other',description=None):
 return ConsolidatedEvent(1,'Curso',None,title,event_type,datetime(2026,10,1,tzinfo=ZoneInfo('America/Santiago')),
  None,False,description,1,[EventSource('calendar_event','1','Canvas')],'ok')

class ImportanceTests(unittest.TestCase):
 def test_explicit_important_titles(self):
  for title in ('Examen final','Interrogación 1','Tarea 2','Entrega proyecto','Proyecto final','Control 3','Quiz 1','Fecha límite'):
   with self.subTest(title=title): self.assertEqual(classify_importance(item(title)),'important')
 def test_non_evaluative_and_ambiguous(self):
  for title in ('Clase 12','Ayudantía semanal','Charla profesional','Sesión general'):
   with self.subTest(title=title): self.assertEqual(classify_importance(item(title)),'not_important')
  self.assertEqual(classify_importance(item('C6 - L:6','assignment')),'uncertain')
  self.assertEqual(classify_importance(item('Actividad especial')),'uncertain')
 def test_presentations_require_evaluative_evidence(self):
  self.assertEqual(classify_importance(item('Presentación del proyecto')),'important')
  self.assertEqual(classify_importance(item('Presentación de contenidos')),'not_important')
 def test_alternative_dates_are_not_automatic(self):
  event=item('Actividad evaluada','assignment','El estudiante debe elegir una de las fechas alternativas')
  self.assertEqual(classify_importance(event),'uncertain')
 def test_needs_review_is_not_auto_synced_or_prompted_noninteractive(self):
  event=item('Actividad especial'); apply_importance([event])
  self.assertEqual(event.status,'needs_review'); self.assertFalse(is_safe_for_auto_sync(event))
  forbidden=Mock(side_effect=AssertionError('input called'))
  stats=process_needs_review([event],non_interactive=True,input_fn=forbidden,output=lambda _:None)
  forbidden.assert_not_called(); self.assertEqual(stats['remaining'],1)
 def test_batch_manual_review(self):
  events=[item('Actividad especial'),item('Reunión general')]; apply_importance(events)
  stats=review_needs_review(events,input_fn=lambda _:'a 1',output=lambda _:None)
  self.assertEqual(events[0].status,'approved'); self.assertTrue(events[0].manual_approval)
  self.assertEqual(events[1].status,'needs_review'); self.assertEqual(stats['remaining'],1)

if __name__=='__main__': unittest.main()

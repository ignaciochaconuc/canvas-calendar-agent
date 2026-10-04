import sys, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from canvas_calendar_agent.calendar_google import google_event_payload, sync_approved, sync_key
from canvas_calendar_agent.consolidation import consolidate_events, discard_event, edit_event, normalize_title
from canvas_calendar_agent.models import AcademicEvent

TZ=ZoneInfo('America/Santiago')
def academic(title, when, source='pdf', sid='1', kind='exam'):
 return AcademicEvent(1,'Optimización','ICS1113',title,kind,when,None,when is not None and when.hour==0,None,
                      source,sid,None,1.0,{})

class ConsolidationTests(unittest.TestCase):
 def test_normalizes_abbreviation(self): self.assertEqual(normalize_title(' I1 '),'interrogacion 1')
 def test_consolidates_compatible_sources(self):
  date=datetime(2026,9,24,17,30,tzinfo=TZ)
  result=consolidate_events([academic('I1',date),academic('Interrogación 1',date,'xlsx','2')])
  self.assertEqual(len(result),1); self.assertEqual(len(result[0].sources),2); self.assertEqual(result[0].status,'ok')
 def test_conflict_and_doubt(self):
  a=datetime(2026,12,1,17,30,tzinfo=TZ); b=datetime(2025,12,1,17,30,tzinfo=TZ)
  result=consolidate_events([academic('Examen',a),academic('Examen',b,'xlsx','2')])
  self.assertEqual(result[0].status,'conflict')
  self.assertEqual(len(consolidate_events([academic('Entrega 2',a),academic('Entrega final',a,'xlsx','2','assignment')])),2)
 def test_pending_edit_discard(self):
  item=consolidate_events([academic('Presentación',None,kind='presentation')])[0]
  self.assertEqual(item.status,'pending')
  edited=edit_event(item,start_at=datetime(2026,11,20,tzinfo=TZ)); self.assertEqual(edited.status,'approved')
  self.assertEqual(discard_event(edited).status,'discarded')

class CalendarTests(unittest.TestCase):
 def approved(self, all_day=False):
  item=consolidate_events([academic('I1',datetime(2026,9,24,0 if all_day else 17,30,tzinfo=TZ))])[0]
  item.status='approved'; item.all_day=all_day; return item
 def test_timed_payload_reminders_and_stable_key(self):
  item=self.approved(); payload=google_event_payload(item)
  self.assertEqual(payload['start']['timeZone'],'America/Santiago')
  self.assertEqual(payload['reminders']['overrides'],[{'method':'email','minutes':10080},{'method':'popup','minutes':1440}])
  self.assertEqual(sync_key(item),sync_key(item))
 def test_all_day_payload(self):
  payload=google_event_payload(self.approved(True)); self.assertIn('date',payload['start']); self.assertNotIn('dateTime',payload['start'])
 def test_confirmation_and_registry_prevent_duplicates(self):
  item=self.approved(); service=Mock(); registry={}
  self.assertIs(sync_approved(service,'cal',[item],registry,confirmed=False),registry)
  service.events.return_value.insert.return_value.execute.return_value={'id':'google-1'}
  sync_approved(service,'cal',[item],registry,confirmed=True); sync_approved(service,'cal',[item],registry,confirmed=True)
  self.assertEqual(service.events.return_value.insert.call_count,1)

if __name__=='__main__': unittest.main()

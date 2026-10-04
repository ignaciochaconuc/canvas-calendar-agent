import sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from canvas_calendar_agent.automation import is_safe_for_auto_sync
from canvas_calendar_agent.calendar_google import ensure_calendar, semester_calendar_name, sync_approved
from canvas_calendar_agent.config import group_courses_by_term, load_semester, save_semester
from canvas_calendar_agent.models import ConsolidatedEvent, EventSource

def event(status='ok',source='assignment',confidence=1,start=True):
 return ConsolidatedEvent(1,'Curso',None,'Entrega','assignment',datetime(2026,10,1,tzinfo=ZoneInfo('America/Santiago')) if start else None,None,False,None,confidence,[EventSource(source,'1',source)],status)

class V2Tests(unittest.TestCase):
 def test_groups_multiple_courses_by_term(self):
  groups=group_courses_by_term([{'id':1,'enrollment_term_id':7},{'id':2,'enrollment_term_id':7},{'id':3,'enrollment_term_id':8}])
  self.assertEqual([x['id'] for x in groups[7]],[1,2])
 def test_semester_roundtrip_and_calendar_name(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'config.json'; save_semester(path,374,[1,2],'2026-2')
   self.assertEqual(load_semester(path)['course_ids'],[1,2])
  self.assertEqual(semester_calendar_name('2026-2'),'🎓 UC')
 def test_reuses_single_uc_calendar(self):
  service=Mock(); service.calendarList.return_value.list.return_value.execute.return_value={
   'items':[{'id':'uc-id','summary':'🎓 UC'}]}
  self.assertEqual(ensure_calendar(service,'🎓 UC'),'uc-id')
  service.calendars.return_value.insert.assert_not_called()
 def test_auto_approval_policy(self):
  self.assertTrue(is_safe_for_auto_sync(event()))
  self.assertTrue(is_safe_for_auto_sync(event(source='calendar_event')))
  self.assertTrue(is_safe_for_auto_sync(event(source='file',confidence=.9)))
  self.assertFalse(is_safe_for_auto_sync(event(source='file',confidence=.89)))
  self.assertFalse(is_safe_for_auto_sync(event(status='conflict')))
  self.assertFalse(is_safe_for_auto_sync(event(status='pending',start=False)))
 def test_namespaced_sync_is_idempotent(self):
  service=Mock(); service.events.return_value.insert.return_value.execute.return_value={'id':'g'}
  registry={}; item=event(status='approved')
  sync_approved(service,'semester-cal',[item],registry,confirmed=True,namespace_calendar=True)
  sync_approved(service,'semester-cal',[item],registry,confirmed=True,namespace_calendar=True)
  self.assertEqual(service.events.return_value.insert.call_count,1)
  self.assertTrue(next(iter(registry)).startswith('semester-cal:'))

if __name__=='__main__': unittest.main()

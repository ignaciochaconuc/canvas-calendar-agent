import sys, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from canvas_calendar_agent.conflict_resolution import process_conflicts, resolve_conflicts, show_conflict
from canvas_calendar_agent.models import ConsolidatedEvent, EventSource

TZ=ZoneInfo('America/Santiago')
def conflict():
 a=datetime(2026,12,1,17,30,tzinfo=TZ); b=datetime(2025,12,1,17,30,tzinfo=TZ)
 return ConsolidatedEvent(1,'Optimización',None,'Examen','exam',None,None,False,None,1,
  [EventSource('file','p','Programa PDF'),EventSource('file','x','Calendario XLSX')],
  'conflict',[a,b])

class ConflictTests(unittest.TestCase):
 def test_display_and_choose_each_alternative(self):
  for choice,year in [('1',2026),('2',2025)]:
   item=conflict(); output=[]
   stats=resolve_conflicts([item],input_fn=lambda _:choice,output=output.append)
   self.assertIn('CONFLICTO 1/1','\n'.join(output)); self.assertEqual(item.start_at.year,year)
   self.assertEqual(item.status,'approved'); self.assertEqual(stats['resolved'],1)
 def test_manual_edit(self):
  answers=iter(['e','15/12/2026','09:45']); item=conflict()
  resolve_conflicts([item],input_fn=lambda _:next(answers),output=lambda _:None)
  self.assertEqual(item.start_at.isoformat(),'2026-12-15T09:45:00-03:00'); self.assertEqual(item.status,'approved')
 def test_manual_date_without_time_is_all_day(self):
  answers=iter(['e','15/12/2026','']); item=conflict()
  resolve_conflicts([item],input_fn=lambda _:next(answers),output=lambda _:None)
  self.assertTrue(item.all_day); self.assertEqual(item.start_at.hour,0)
 def test_discard_and_skip(self):
  item=conflict(); resolve_conflicts([item],input_fn=lambda _:'d',output=lambda _:None); self.assertEqual(item.status,'discarded')
  item=conflict(); stats=resolve_conflicts([item],input_fn=lambda _:'s',output=lambda _:None)
  self.assertEqual(item.status,'conflict'); self.assertEqual(stats['skipped'],1)
 def test_noninteractive_never_calls_input(self):
  item=conflict(); forbidden=Mock(side_effect=AssertionError('input called')); output=[]
  stats=process_conflicts([item],non_interactive=True,input_fn=forbidden,output=output.append)
  forbidden.assert_not_called(); self.assertEqual(item.status,'conflict'); self.assertEqual(stats['skipped'],1)
  self.assertIn('1',output[0])

if __name__=='__main__': unittest.main()

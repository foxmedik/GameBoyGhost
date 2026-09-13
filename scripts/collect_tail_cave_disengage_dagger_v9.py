"""Retry continuous failure branches with shielded right-wall disengagement."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from gameboy_agent.world_memory import file_hash
import collect_tail_cave_continuous_dagger_v8 as collector
PLAN=ROOT/'configs/tail_cave_disengage_dagger_v9_collection.json'
class DisengagingTeacher(collector.BeetleTeacher):
 def action(self,state,targets):
  nearest=min(abs(t['x']-state['x'])+abs(t['y']-state['y']) for t in targets)
  if state['x']>132 and nearest<=40:
   self.phase=None
   return ['left','b'],3
  return super().action(state,targets)
def main(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(Path(__file__))!=plan['launcher_sha256']:raise ValueError('Frozen launcher changed')
 collector.PLAN=PLAN;collector.BeetleTeacher=DisengagingTeacher;collector.main(out)
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

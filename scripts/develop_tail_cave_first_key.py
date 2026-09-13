"""Run and exactly replay the frozen Tail Cave first-key teacher panel."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_teacher import SMALL_KEYS,execute
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import Trace,apply
PLAN=ROOT/'configs/tail_cave_first_key_v1.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def run_case(root,spec,plan):
 source=ROOT/plan['source']/spec['source_case'];out=root/spec['id'];out.mkdir(parents=True,exist_ok=False)
 for name in ('game.gbc','final.state'):shutil.copy2(source/name,out/('initial.state' if name=='final.state' else name))
 manifest=json.loads((source/'manifest.json').read_text())
 for name,expected in manifest['artifacts'].items():
  if file_hash(source/name)!=expected:raise ValueError(f'Source changed: {source/name}')
 base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=plan['budgets']['teacher_decisions'],max_frames=60000,reject_completed_start=False)
 rows=[];evidence=[];failure=None;began=time.monotonic()
 with (out/'trajectory.jsonl').open('x') as stream:
  env=Trace(base,stream,rows)
  try:
   base.reset(seed=0);initial=snapshot(base.pyboy);initial_keys=int(base.pyboy.memory[SMALL_KEYS])
   if spec['entry_idle_frames']:env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['entry_idle_frames'])
   execute(env,evidence)
  except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
  finally:final=snapshot(base.pyboy);final_keys=int(base.pyboy.memory[SMALL_KEYS]);journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=plan['budgets']['teacher_decisions'],max_frames=60000,reject_completed_start=False)
 try:
  replay.reset(seed=0)
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'];assert snapshot(replay.pyboy)==row['after'];assert replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal and int(replay.pyboy.memory[SMALL_KEYS])==final_keys
 finally:replay.close()
 result={'spec':spec,'success':failure is None,'failure':failure,'initial':initial,'initial_small_keys':initial_keys,'final':final,'final_small_keys':final_keys,'decisions':len(rows),'recovery_damage_raw':initial['health']-final['health'],'exact_replay':True,'evidence':evidence,'seconds':round(time.monotonic()-began,3)}
 write(out/'result.json',result);write(out/'manifest.json',{'artifacts':{p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}});print(json.dumps(result),flush=True);return result
def main(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(ROOT/plan['source']/'summary.json')!=plan['source_summary_sha256'] or file_hash(ROOT/plan['source']/'panel.json')!=plan['source_panel_sha256']:raise ValueError('Frozen cave-entry source changed')
 for path,key in ((Path(__file__),'runner_sha256'),(ROOT/'src/gameboy_agent/tail_cave_teacher.py','teacher_sha256')):
  if file_hash(path)!=plan[key]:raise ValueError(f'Frozen source changed: {path}')
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');results=[]
 for spec in plan['cases']:
  results.append(run_case(out,spec,plan));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'exact_replays':sum(r['exact_replay'] for r in results),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

"""Collect teacher escape spans at the first detected blocked-intent state."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_progression import clear_compass_room
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix,senses
from run_toadstool_progression import Trace,apply
def norm(v):return json.loads(json.dumps(v))
def write(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def run(root,spec,plan):
 source=ROOT/plan['source']/f"development-house-{spec['base']:02d}";student=ROOT/plan['student_gate']/spec['student_case'];out=root/spec['id'];out.mkdir(exist_ok=False)
 for n in ('game.gbc','initial.state'):shutil.copy2(source/n,out/n)
 commands=[json.loads(l) for l in (student/'trajectory.jsonl').read_text().splitlines()][:spec['blocked_index']+1]
 def make():return ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=16000,max_frames=300000,completion_milestone=None)
 env=make();rows=[];evidence=[];failure=None;started=time.monotonic()
 try:
  env.reset(seed=0);prefix(env,source);env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
  for row in commands:
   info=apply(env,row['command'])[4]
   if fingerprint(env)!=row['fingerprint'] or norm(snapshot(env.pyboy))!=norm(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError('Student prefix mismatch')
  start=senses(env);damage_before=env.journal.damage_raw
  with (out/'trajectory.jsonl').open('x') as stream:clear_compass_room(Trace(env,stream,rows),evidence)
  final=senses(env);damage=env.journal.damage_raw-damage_before
 except Exception as exc:
  failure=f'{type(exc).__name__}: {exc}';final=senses(env);damage=0 if 'damage_before' not in locals() else env.journal.damage_raw-damage_before
 finally:
  journal=deepcopy(env.journal.state());env.pyboy.screen.image.save(out/'final.png');env.close()
 replay=make()
 try:
  replay.reset(seed=0);prefix(replay,source);replay.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
  for row in commands+rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'] and norm(snapshot(replay.pyboy))==norm(row['after']) and replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal
 finally:replay.close()
 result=dict(spec=spec,success=failure is None,failure=failure,blocked_state=start,final=final,damage_raw=damage,exact_replay=True,teacher_commands=len(rows),control='teacher_escape_after_first_v3_blocked_intent',training_eligible=failure is None,seconds=round(time.monotonic()-started,2));write(out/'result.json',result);write(out/'evidence.json',evidence);write(out/'manifest.json',{p.name:file_hash(p) for p in out.iterdir() if p.is_file()});return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_text())
 for n,d in plan['frozen_inputs'].items():
  if file_hash(ROOT/n)!=d:raise RuntimeError(f'Frozen input changed: {n}')
 a.out.mkdir(exist_ok=False);shutil.copy2(a.plan,a.out/'plan.json');results=[]
 for spec in plan['cases']:
  results.append(run(a.out,spec,plan));write(a.out/'summary.json',dict(status='running',cases=len(results),planned=len(plan['cases']),successes=sum(r['success'] for r in results),exact_replays=sum(r['exact_replay'] for r in results),training_started=False,validation_loaded=False,results=results))
 s=json.loads((a.out/'summary.json').read_text());s['status']='complete';write(a.out/'summary.json',s)
if __name__=='__main__':main()

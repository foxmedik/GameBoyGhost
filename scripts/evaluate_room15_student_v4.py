"""Autonomous gate for the temporal room-15 student."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.room15_model_v4 import action_command
from gameboy_agent.room15_model_v4 import temporal_feature,update
from gameboy_agent.tail_cave_progression import GEL,enter_compass_room
from gameboy_agent.tail_cave_teacher import entities
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix,senses
from run_toadstool_progression import Trace,apply
from train_room15_student_v1 import Room15Net
def normalized(v):return json.loads(json.dumps(v))
def write(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def run_case(root,spec,plan):
 source=ROOT/plan['source']/f"development-house-{spec['base']:02d}";out=root/spec['id'];out.mkdir(exist_ok=False)
 for n in ('game.gbc','initial.state'):shutil.copy2(source/n,out/n)
 saved=torch.load(ROOT/plan['candidate'],map_location='cpu');model=Room15Net(saved['inputs'],saved['outputs']);model.load_state_dict(saved['model']);model.eval()
 def make():return ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=16000,max_frames=300000,completion_milestone=None)
 env=make();rows=[];evidence=[];history=[];failure=None;started=time.monotonic()
 try:
  env.reset(seed=0);prefix(env,source);env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle']);traced=Trace(env,(out/'trajectory.jsonl').open('x'),rows);enter_compass_room(traced,evidence);initial=senses(env);start_damage=env.journal.damage_raw
  for _ in range(plan['decision_budget']):
   state=normalized(snapshot(env.pyboy))
   if state['room']!=[1,0,21] or not state['health']:raise RuntimeError(f'Student left living room15: {state["room"]}')
   if not entities(env,GEL):break
   x=torch.from_numpy((temporal_feature(senses(env),history)-saved['mean'])/saved['scale'])
   with torch.no_grad():action=int(model(x).argmax())
   buttons,frames=action_command(action)
   if action == 9:
    traced.step_input_events(buttons,release=('up','down','left','right','a','b','start','select'),frames=frames)
   else:
    traced.step_buttons(buttons,action_frames=frames)
   history=update(history,action,state,normalized(snapshot(env.pyboy)))
  else:raise RuntimeError(f'Student exhausted {plan["decision_budget"]}-decision room15 budget')
  final=senses(env);damage=env.journal.damage_raw-start_damage
  if final['state']['room']!=[1,0,21] or not final['state']['health'] or entities(env,GEL):raise RuntimeError('Student completion contract failed')
 except Exception as exc:
  failure=f'{type(exc).__name__}: {exc}';final=senses(env);damage=0 if 'start_damage' not in locals() else env.journal.damage_raw-start_damage
 finally:
  journal=deepcopy(env.journal.state());env.pyboy.screen.image.save(out/'final.png');env.close()
 replay=make()
 try:
  replay.reset(seed=0);prefix(replay,source);replay.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'] and normalized(snapshot(replay.pyboy))==normalized(row['after']) and replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal
 finally:replay.close()
 result=dict(spec=spec,success=failure is None,failure=failure,initial=initial,final=final,damage_raw=damage,exact_replay=True,student_decisions=len(history),control='student_only_room15_temporal_v4_escape_policy',teacher_action_fraction=0.0,autonomous_room15_evaluated=True,seconds=round(time.monotonic()-started,2));write(out/'evidence.json',evidence);write(out/'result.json',result);write(out/'manifest.json',{p.name:file_hash(p) for p in out.iterdir() if p.is_file()});return result
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();plan=json.loads(a.plan.read_text())
 for p,k in ((Path(__file__),'evaluator_sha256'),(ROOT/plan['candidate'],'candidate_sha256'),(ROOT/plan['experiment'],'experiment_sha256')):
  if file_hash(p)!=plan[k]:raise RuntimeError(f'Frozen input changed: {p}')
 a.out.mkdir(exist_ok=False);shutil.copy2(a.plan,a.out/'plan.json');results=[]
 for spec in plan['cases']:
  results.append(run_case(a.out,spec,plan));write(a.out/'summary.json',dict(status='running',cases=len(results),planned=len(plan['cases']),successes=sum(r['success'] for r in results),exact_replays=sum(r['exact_replay'] for r in results),validation_loaded=False,results=results))
 s=json.loads((a.out/'summary.json').read_text());low=[r for r in results if r['initial']['state']['health']<=4];s.update(status='complete',required_successes=plan['required_successes'],half_heart_cases=len(low),half_heart_successes=sum(r['success'] for r in low),gate_passed=sum(r['success'] for r in results)>=plan['required_successes'] and sum(r['success'] for r in low)>=plan['required_half_heart_successes']);write(a.out/'summary.json',s)
if __name__=='__main__':main()

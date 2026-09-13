"""Collect shielded recovery actions from unsafe downstream learner states."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
from control_context import ControlContext
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression_contracts import adjacent_direction
from gameboy_agent.terrain_navigation import cell,exits,paths,steer_path,terrain
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import DURATIONS,buttons,feature
from progression_local_control import json_state
from run_toadstool_progression import Trace,apply
PLAN=ROOT/'configs/progression_downstream_recovery_v1.json'

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def matches(state,spec):
 return (state['room']==[0,0,spec['room']] and not state['tarin'] and
         ((spec['leg']=='witch' and state['toadstool'] and not state['powder']) or
          (spec['leg']=='tarin' and not state['toadstool'] and state['powder'])))
def frozen_goal(base,spec):
 state=json_state(snapshot(base.pyboy));direction,_=adjacent_direction(state['room'],spec['target_room'])
 candidates=[e for e in exits(terrain(base.pyboy),cell(state['x'],state['y']),spec['room']) if e['direction']==direction]
 interior=[e for e in candidates if not(e['cell'][0] in (0,9) and e['cell'][1] in (0,7))]
 if not candidates:raise RuntimeError(f"No verified exit from {spec['room']:02X} toward {spec['target_room']:02X}")
 chosen=min(interior or candidates,key=lambda e:len(e['path']))
 return {'room':[0,0,spec['target_room']],'x':chosen['cell'][0]*16+8,'y':chosen['cell'][1]*16+12,'cell':chosen['cell'],'direction':direction}
def teacher_action(base,goal,recovery_index):
 state=json_state(snapshot(base.pyboy));here=cell(state['x'],state['y'])
 if here==tuple(goal['cell']):return [goal['direction'],2,1]
 route=paths(terrain(base.pyboy),here).get(tuple(goal['cell']))
 if route is None:return [(3,4,1,2)[recovery_index%4],2,1]
 waypoint=route[0] if route else goal['cell'];direction=steer_path(state['x'],state['y'],waypoint) or goal['direction']
 return [direction,2,1]
def collect_case(root,spec,plan):
 source=ROOT/plan['source_teacher']/spec['source_case'];out=root/spec['id'];out.mkdir(parents=True,exist_ok=False)
 for name in ('game.gbc','initial.state'):shutil.copy2(source/name,out/name)
 manifest=json.loads((source/'manifest.json').read_text())
 for name,expected in manifest['artifacts'].items():
  if file_hash(source/name)!=expected:raise ValueError(f'Source changed: {source/name}')
 source_rows=[json.loads(x) for x in (source/'trajectory.jsonl').read_text().splitlines()]
 start=next(i for i,row in enumerate(source_rows) if matches(row['before'],spec))
 base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000);rows=[];samples=[];failure=None;began=time.monotonic()
 with (out/'trajectory.jsonl').open('x') as stream:
  env=Trace(base,stream,rows)
  try:
   base.reset(seed=0)
   for row in source_rows[:start]:
    apply(env,row['command'])
    if rows[-1]['fingerprint']!=row['fingerprint']:raise RuntimeError(f"Source prefix changed at {row['decision']}")
   if spec['arrival_idle_frames']:env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['arrival_idle_frames'])
   initial_health=snapshot(base.pyboy)['health'];goal=frozen_goal(base,spec);context=ControlContext(base);previous=None;stationary=0;recoveries=0
   for _ in range(plan['teacher_budget']):
    state=json_state(snapshot(base.pyboy))
    if state['room']==goal['room']:break
    if not matches(state,spec) or not state['health']:raise RuntimeError(f"Teacher left contract at {state['room']} health {state['health']}")
    action=teacher_action(base,goal,recoveries);samples.append((feature(base,context,state,goal),action,[spec['id'],base.total_steps]))
    env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2])
    now=json_state(snapshot(base.pyboy));pose=(now['x'],now['y']);stationary=stationary+1 if pose==previous else 0;previous=pose
    if stationary>=48:recoveries+=1;stationary=0
    if recoveries>4:raise RuntimeError(f'Teacher stalled at {pose}')
   else:raise RuntimeError('Teacher budget exhausted')
   final=json_state(snapshot(base.pyboy))
   if final['room']!=goal['room'] or not final['health']:raise RuntimeError('Teacher did not reach target alive')
  except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
  finally:final=json_state(snapshot(base.pyboy));journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000)
 try:
  replay.reset(seed=0)
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'];assert json_state(snapshot(replay.pyboy))==json_state(row['after']);assert replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal
 finally:replay.close()
 if samples:np.savez_compressed(out/'corrections.npz',x=np.stack([s[0] for s in samples]),y=np.asarray([s[1] for s in samples],dtype=np.int64),provenance=np.asarray([s[2] for s in samples]))
 result={'spec':spec,'success':failure is None,'failure':failure,'source_prefix_decisions':start,'teacher_decisions':len(samples),'initial_health':initial_health,'final':final,'recovery_damage_raw':initial_health-final['health'],'exact_replay':True,'seconds':round(time.monotonic()-began,3)}
 write(out/'result.json',result);write(out/'manifest.json',{'artifacts':{p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}});print(json.dumps(result),flush=True);return result
def main(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(Path(__file__))!=plan['collector_sha256']:raise ValueError('Frozen collector changed')
 if file_hash(ROOT/plan['source_teacher']/'summary.json')!=plan['source_summary_sha256']:raise ValueError('Frozen source summary changed')
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');shutil.copy2(Path(__file__),out/'collector-source.py');results=[]
 for spec in plan['collection_specs']:
  results.append(collect_case(out,spec,plan));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['teacher_required_successes'],'correction_rows':sum(r['teacher_decisions'] for r in results if r['success']),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

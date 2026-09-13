"""Live development evaluation for the downstream recovery candidate."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from control_context import ControlContext
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import DURATIONS,buttons,feature
from collect_progression_downstream_recovery_v1 import matches,frozen_goal,teacher_action
from progression_local_control import json_state
from run_toadstool_progression import Trace,apply
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/progression_downstream_recovery_v1_live.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def run_case(root,spec,plan,model,saved):
 source=ROOT/plan['source_teacher']/spec['source_case'];out=root/spec['id'];out.mkdir(parents=True,exist_ok=False)
 for name in ('game.gbc','initial.state'):shutil.copy2(source/name,out/name)
 manifest=json.loads((source/'manifest.json').read_text())
 for name,expected in manifest['artifacts'].items():
  if file_hash(source/name)!=expected:raise ValueError(f'Source changed: {source/name}')
 source_rows=[json.loads(x) for x in (source/'trajectory.jsonl').read_text().splitlines()];start=next(i for i,row in enumerate(source_rows) if matches(row['before'],spec))
 base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000);rows=[];failure=None;recoveries=0;candidate_decisions=0;began=time.monotonic()
 with (out/'trajectory.jsonl').open('x') as stream:
  env=Trace(base,stream,rows)
  try:
   base.reset(seed=0)
   for row in source_rows[:start]:
    apply(env,row['command'])
    if rows[-1]['fingerprint']!=row['fingerprint']:raise RuntimeError(f"Source prefix changed at {row['decision']}")
   if spec['arrival_idle_frames']:env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['arrival_idle_frames'])
   initial_health=snapshot(base.pyboy)['health'];goal=frozen_goal(base,spec);context=ControlContext(base);previous=None;stationary=0
   for _ in range(plan['decision_budget']):
    state=json_state(snapshot(base.pyboy))
    if state['room']==goal['room']:break
    if not matches(state,spec) or not state['health']:raise RuntimeError(f"Candidate left contract at {state['room']} health {state['health']}")
    raw=feature(base,context,state,goal);x=torch.from_numpy(raw.copy());n=saved['base_inputs'];x[:n]=(x[:n]-torch.from_numpy(saved['mean']))/torch.from_numpy(saved['scale'])*torch.from_numpy(saved['input_mask'])
    with torch.no_grad():z=model(x)
    action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())];env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);candidate_decisions+=1
    now=json_state(snapshot(base.pyboy));pose=(now['x'],now['y']);stationary=stationary+1 if pose==previous else 0;previous=pose
    if stationary>=plan['stationary_before_recovery']:
     if recoveries>=plan['maximum_recoveries']:raise RuntimeError(f'Candidate stalled at {pose}')
     action=teacher_action(base,goal,recoveries);env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);recoveries+=1;stationary=0
   else:raise RuntimeError('Candidate decision budget exhausted')
   final=json_state(snapshot(base.pyboy))
   if final['room']!=goal['room'] or not final['health']:raise RuntimeError('Candidate did not reach target alive')
  except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
  finally:final=json_state(snapshot(base.pyboy));journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000)
 try:
  replay.reset(seed=0)
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'];assert json_state(snapshot(replay.pyboy))==json_state(row['after']);assert replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal
 finally:replay.close()
 result={'spec':spec,'success':failure is None,'failure':failure,'candidate_decisions':candidate_decisions,'recoveries':recoveries,'initial_health':initial_health,'final':final,'recovery_damage_raw':initial_health-final['health'],'exact_replay':True,'seconds':round(time.monotonic()-began,3)}
 write(out/'result.json',result);write(out/'manifest.json',{'artifacts':{p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}});print(json.dumps(result),flush=True);return result
def main(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(Path(__file__))!=plan['evaluator_sha256']:raise ValueError('Frozen evaluator changed')
 experiment=ROOT/plan['experiment']
 if file_hash(experiment)!=plan['experiment_sha256']:raise ValueError('Frozen experiment changed')
 checkpoint=ROOT/plan['candidate']
 if file_hash(checkpoint)!=plan['candidate_sha256']:raise ValueError('Frozen candidate changed')
 specs=json.loads(experiment.read_text())['development_panel']['cases'];saved=torch.load(checkpoint,map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval()
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');shutil.copy2(Path(__file__),out/'evaluator-source.py');results=[]
 for spec in specs:
  results.append(run_case(out,spec,plan,model,saved));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'recoveries':sum(r['recoveries'] for r in results),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

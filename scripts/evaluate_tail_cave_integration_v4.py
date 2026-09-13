"""Evaluate a frozen Tail Cave candidate on held-out integration timing offsets."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_controller import tail_feature
from gameboy_agent.tail_cave_teacher import SMALL_KEYS
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import DURATIONS,buttons,history_features
from progression_local_control import json_state
from run_toadstool_progression import Trace,apply
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_integration_dagger_v4_evaluation.json';BUTTONS=('up','down','left','right','a','b','start','select')
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def run_case(root,base_id,idle,plan,model,saved):
 entry=ROOT/plan['entry_states'];meta=json.loads((entry/f'{base_id:02d}.json').read_text());case_id=f'integration-heldout-{base_id:02d}-idle-{idle:02d}';out=root/case_id;out.mkdir(parents=True,exist_ok=False);source=ROOT/plan['source_run']/f'development-house-{base_id:02d}';shutil.copy2(source/'game.gbc',out/'game.gbc');shutil.copy2(entry/f'{base_id:02d}.state',out/'initial.state');rows=[];failure=None;decisions=0;began=time.monotonic()
 base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False,completion_milestone=None)
 with (out/'trajectory.jsonl').open('x') as stream:
  env=Trace(base,stream,rows)
  try:
   base.reset(seed=0);base.episode_actions=deepcopy(meta['history']);initial=json_state(snapshot(base.pyboy));env.step_input_events(release=BUTTONS,frames=idle)
   for _ in range(plan['decision_budget']):
    state=json_state(snapshot(base.pyboy))
    if int(base.pyboy.memory[SMALL_KEYS]):break
    if state['room']!=[1,0,0x16] or not state['health']:raise RuntimeError(f'Candidate left living room-16 contract: {state["room"]}')
    raw=tail_feature(base,history_features(base.episode_actions));x=torch.from_numpy((raw-saved['mean'])/saved['scale'])
    with torch.no_grad():z=model(x)
    action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())];env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);decisions+=1
   else:raise RuntimeError('Candidate exhausted autonomous decision budget')
   final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS])
   if final['room']!=[1,0,0x16] or not final['health'] or final_keys!=1:raise RuntimeError('Autonomous first-key contract failed')
  except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
  finally:final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS]);journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False,completion_milestone=None);replay.reset(seed=0);replay.episode_actions=deepcopy(meta['history'])
 try:
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'];assert json_state(snapshot(replay.pyboy))==json_state(row['after']);assert replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal and int(replay.pyboy.memory[SMALL_KEYS])==final_keys
 finally:replay.close()
 result={'id':case_id,'base_case':base_id,'idle_frames':idle,'success':failure is None,'failure':failure,'initial':initial,'final':final,'final_small_keys':final_keys,'candidate_decisions':decisions,'damage_raw':initial['health']-final['health'],'exact_replay':True,'seconds':round(time.monotonic()-began,3)};write(out/'result.json',result);write(out/'manifest.json',{'artifacts':{p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}});print(json.dumps(result),flush=True);return result
def main(out):
 plan=json.loads(PLAN.read_text())
 for path,key in ((Path(__file__),'evaluator_sha256'),(ROOT/plan['training_experiment'],'training_experiment_sha256'),(ROOT/plan['candidate'],'candidate_sha256')):
  if file_hash(path)!=plan[key]:raise ValueError(f'Frozen input changed: {path}')
 for base_id in plan['base_case_ids']:
  state=ROOT/plan['entry_states']/f'{base_id:02d}.state';meta=json.loads((ROOT/plan['entry_states']/f'{base_id:02d}.json').read_text())
  if file_hash(state)!=meta['state_sha256']:raise ValueError(f'Entry state changed: {state}')
 saved=torch.load(ROOT/plan['candidate'],map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval();out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');results=[]
 for base_id in plan['base_case_ids']:
  for idle in plan['heldout_idle_frames']:
   results.append(run_case(out,base_id,idle,plan,model,saved));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'candidate_decisions':sum(r['candidate_decisions'] for r in results),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

"""Collect on-policy labels by branching directly from continuous route replay."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_controller import tail_feature
from gameboy_agent.tail_cave_teacher import SMALL_KEYS,HARDHAT_BEETLE,BeetleTeacher,collect_key,entities
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import DURATIONS,action_tuple,buttons,history_features
from progression_local_control import json_state
from run_toadstool_progression import Trace,apply
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_continuous_dagger_v8_collection.json';BUTTONS=('up','down','left','right','a','b','start','select')
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def replay_prefix(env,source,entry_frame):
 for line in (source/'trajectory.jsonl').open():
  row=json.loads(line);info=apply(env,row['command'])[4]
  if fingerprint(env)!=row['fingerprint'] or json_state(snapshot(env.pyboy))!=json_state(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError(f'Source replay mismatch: {source}/{row["decision"]}')
  if env.frames==entry_frame:return
 raise RuntimeError(f'Entry frame absent: {source}')
def run_case(root,base_id,idle,plan,model,saved):
 case_id=f'continuous-{base_id:02d}-idle-{idle:02d}';out=root/case_id;out.mkdir(parents=True,exist_ok=False);source=ROOT/plan['source_run']/f'development-house-{base_id:02d}';shutil.copy2(source/'game.gbc',out/'game.gbc');shutil.copy2(source/'initial.state',out/'initial.state');entry_frame=next(e['frame'] for e in json.loads((source/'evidence.json').read_text()) if e.get('kind')=='tail_cave_beetle_room_entered');rows=[];samples=[];failure=None;teacher_mode=False;recovery=None;candidate_steps=0;began=time.monotonic()
 base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000,reject_completed_start=False,completion_milestone=None);base.reset(seed=0);replay_prefix(base,source,entry_frame)
 with (out/'trajectory.jsonl').open('x') as stream:
  env=Trace(base,stream,rows)
  try:
   initial=json_state(snapshot(base.pyboy));initial_health=initial['health']
   if idle:env.step_input_events(release=BUTTONS,frames=idle)
   teacher=BeetleTeacher()
   for decision in range(plan['decision_budget']):
    state=json_state(snapshot(base.pyboy));targets=entities(base,HARDHAT_BEETLE)
    if not targets:break
    if state['room']!=[1,0,0x16] or not state['health']:raise RuntimeError(f'Rollout left living room-16 contract: {state["room"]}')
    expert_buttons,expert_frames=teacher.action(state,targets);expert=action_tuple({'buttons':expert_buttons,'action_frames':expert_frames});raw=tail_feature(base,history_features(base.episode_actions));samples.append((raw,expert,[case_id,decision,int(teacher_mode)]));x=torch.from_numpy((raw-saved['mean'])/saved['scale'])
    with torch.no_grad():z=model(x)
    proposed=(int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax()))
    if teacher_mode:env.step_buttons(expert_buttons,action_frames=expert_frames,legacy_action=expert[:2])
    else:
     env.step_buttons(buttons(proposed),action_frames=DURATIONS[proposed[2]],legacy_action=proposed[:2]);candidate_steps+=1;now=json_state(snapshot(base.pyboy))
     if now['health']<initial_health and now['health']:
      teacher_mode=True;recovery={'decision':decision,'frame':base.frames,'health_before':initial_health,'health_after':now['health'],'state':now}
   else:raise RuntimeError('Continuous on-policy rollout exhausted decision budget')
   collect_key(env,[]);final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS])
   if final['room']!=[1,0,0x16] or not final['health'] or final_keys!=1:raise RuntimeError('Continuous correction contract failed')
  except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
  finally:final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS]);journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000,reject_completed_start=False,completion_milestone=None);replay.reset(seed=0);replay_prefix(replay,source,entry_frame)
 try:
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'];assert json_state(snapshot(replay.pyboy))==json_state(row['after']);assert replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal and int(replay.pyboy.memory[SMALL_KEYS])==final_keys
 finally:replay.close()
 if samples:np.savez_compressed(out/'corrections.npz',x=np.stack([s[0] for s in samples]),y=np.asarray([s[1] for s in samples],dtype=np.int64),provenance=np.asarray([s[2] for s in samples]))
 result={'id':case_id,'base_case':base_id,'idle_frames':idle,'success':failure is None,'failure':failure,'initial':initial,'final':final,'final_small_keys':final_keys,'candidate_steps':candidate_steps,'teacher_recovery':recovery,'correction_rows':len(samples),'exact_replay':True,'seconds':round(time.monotonic()-began,3)};write(out/'result.json',result);print(json.dumps(result),flush=True);return result
def main(out):
 plan=json.loads(PLAN.read_text())
 for path,key in ((Path(__file__),'collector_sha256'),(ROOT/plan['candidate'],'candidate_sha256'),(ROOT/plan['source_run']/'summary.json','source_summary_sha256')):
  if file_hash(path)!=plan[key]:raise ValueError(f'Frozen input changed: {path}')
 saved=torch.load(ROOT/plan['candidate'],map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval();out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');results=[]
 for base_id in plan['base_case_ids']:
  for idle in plan['idle_frames']:
   results.append(run_case(out,base_id,idle,plan,model,saved));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'correction_rows':sum(r['correction_rows'] for r in results if r['success']),'candidate_steps':sum(r['candidate_steps'] for r in results),'teacher_recoveries':sum(r['teacher_recovery'] is not None for r in results),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

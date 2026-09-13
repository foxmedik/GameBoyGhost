"""Collect guarded first-divergence corrections for Tail Cave room 0x16."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from control_context import ControlContext
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_teacher import SMALL_KEYS,HARDHAT_BEETLE,BeetleTeacher,collect_key,entities,enter_beetle_room
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import DURATIONS,action_tuple,buttons,feature
from extract_tail_cave_first_key_v1 import GOAL
from progression_local_control import json_state
from run_toadstool_progression import Trace,apply
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_dagger_v2_collection.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def command(action):return {'buttons':buttons(action),'action_frames':DURATIONS[action[2]]}
def run_case(root,spec,plan,model,saved):
 source=ROOT/plan['source']/spec['source_case'];out=root/spec['id'];out.mkdir(parents=True,exist_ok=False)
 for name in ('game.gbc','final.state'):shutil.copy2(source/name,out/('initial.state' if name=='final.state' else name))
 manifest=json.loads((source/'manifest.json').read_text())
 for name,expected in manifest['artifacts'].items():
  if file_hash(source/name)!=expected:raise ValueError(f'Source changed: {source/name}')
 base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False);rows=[];samples=[];evidence=[];failure=None;matched=0;divergence=None;began=time.monotonic()
 with (out/'trajectory.jsonl').open('x') as stream:
  env=Trace(base,stream,rows)
  try:
   base.reset(seed=0);initial=json_state(snapshot(base.pyboy))
   if spec['entry_idle_frames']:env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['entry_idle_frames'])
   enter_beetle_room(env,evidence);context=ControlContext(base);teacher=BeetleTeacher()
   for decision in range(plan['teacher_budget']):
    state=json_state(snapshot(base.pyboy));targets=entities(base,HARDHAT_BEETLE)
    if not targets:break
    if state['room']!=[1,0,0x16] or not state['health']:raise RuntimeError(f'Guarded teacher left room-16 contract: {state["room"]}')
    expert_buttons,expert_frames=teacher.action(state,targets);expert=action_tuple({'buttons':expert_buttons,'action_frames':expert_frames})
    raw=feature(base,context,state,GOAL);samples.append((raw,expert,[spec['id'],decision]))
    if divergence is None:
     x=torch.from_numpy(raw.copy());n=saved['base_inputs'];x[:n]=(x[:n]-torch.from_numpy(saved['mean']))/torch.from_numpy(saved['scale'])*torch.from_numpy(saved['input_mask'])
     with torch.no_grad():z=model(x)
     proposed=(int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax()))
     if proposed==expert:matched+=1
     else:divergence={'decision':decision,'frame':base.frames,'state':state,'candidate':proposed,'teacher':expert}
    env.step_buttons(expert_buttons,action_frames=expert_frames,legacy_action=expert[:2])
   else:raise RuntimeError('Guarded teacher exhausted combat budget')
   collect_key(env,evidence);final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS])
   if final['room']!=[1,0,0x16] or not final['health'] or final_keys!=1:raise RuntimeError('Guarded correction completion contract failed')
  except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
  finally:final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS]);journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False)
 try:
  replay.reset(seed=0)
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'];assert json_state(snapshot(replay.pyboy))==json_state(row['after']);assert replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal and int(replay.pyboy.memory[SMALL_KEYS])==final_keys
 finally:replay.close()
 if samples:np.savez_compressed(out/'corrections.npz',x=np.stack([s[0] for s in samples]),y=np.asarray([s[1] for s in samples],dtype=np.int64),provenance=np.asarray([s[2] for s in samples]))
 result={'spec':spec,'success':failure is None,'failure':failure,'initial':initial,'final':final,'final_small_keys':final_keys,'candidate_exact_prefix':matched,'first_divergence':divergence,'correction_rows':len(samples),'exact_replay':True,'seconds':round(time.monotonic()-began,3)}
 write(out/'result.json',result);write(out/'manifest.json',{'artifacts':{p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}});print(json.dumps(result),flush=True);return result
def main(out):
 plan=json.loads(PLAN.read_text())
 for path,key in ((Path(__file__),'collector_sha256'),(ROOT/'src/gameboy_agent/tail_cave_teacher.py','teacher_sha256'),(ROOT/plan['candidate'],'candidate_sha256'),(ROOT/plan['source']/'summary.json','source_summary_sha256'),(ROOT/plan['source']/'panel.json','source_panel_sha256')):
  if file_hash(path)!=plan[key]:raise ValueError(f'Frozen input changed: {path}')
 saved=torch.load(ROOT/plan['candidate'],map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval();out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');results=[]
 for spec in plan['cases']:
  results.append(run_case(out,spec,plan,model,saved));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'correction_rows':sum(r['correction_rows'] for r in results),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

"""Evaluate one frozen Tail Cave first-key candidate on unseen entry timings."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from control_context import ControlContext
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_teacher import SMALL_KEYS,collect_key,defeat_beetles,enter_beetle_room
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import DURATIONS,buttons,feature
from progression_local_control import json_state
from run_toadstool_progression import Trace,apply
from train_progression_dagger_v1 import DaggerNet
from extract_tail_cave_first_key_v1 import GOAL
PLAN=ROOT/'configs/tail_cave_first_key_live_v1.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def run_case(root,spec,plan,model,saved):
 source=ROOT/plan['source']/spec['source_case'];out=root/spec['id'];out.mkdir(parents=True,exist_ok=False)
 for name in ('game.gbc','final.state'):shutil.copy2(source/name,out/('initial.state' if name=='final.state' else name))
 manifest=json.loads((source/'manifest.json').read_text())
 for name,expected in manifest['artifacts'].items():
  if file_hash(source/name)!=expected:raise ValueError(f'Source changed: {source/name}')
 base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False);rows=[];evidence=[];failure=None;candidate_decisions=0;fallback=0;began=time.monotonic()
 with (out/'trajectory.jsonl').open('x') as stream:
  env=Trace(base,stream,rows)
  try:
   base.reset(seed=0);initial=json_state(snapshot(base.pyboy))
   if spec['entry_idle_frames']:env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['entry_idle_frames'])
   enter_beetle_room(env,evidence);combat_health=snapshot(base.pyboy)['health'];context=ControlContext(base)
   for decision in range(plan['decision_budget']):
    state=json_state(snapshot(base.pyboy))
    if int(base.pyboy.memory[SMALL_KEYS]):break
    if state['room']!=[1,0,0x16] or not state['health']:raise RuntimeError(f'Candidate left living room-16 contract: {state["room"]}')
    if state['health']<combat_health or decision>=plan['teacher_handoff_after_decisions']:
     fallback=1;evidence.append({'kind':'first_key_teacher_recovery_started','reason':'damage' if state['health']<combat_health else 'decision_bound','frame':base.frames,'candidate_decisions':candidate_decisions})
     defeat_beetles(env,evidence);collect_key(env,evidence);break
    raw=feature(base,context,state,GOAL);x=torch.from_numpy(raw.copy());n=saved['base_inputs'];x[:n]=(x[:n]-torch.from_numpy(saved['mean']))/torch.from_numpy(saved['scale'])*torch.from_numpy(saved['input_mask'])
    with torch.no_grad():z=model(x)
    action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())];env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);candidate_decisions+=1
   else:raise RuntimeError('First-key candidate exhausted decision budget')
   final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS])
   if final['room']!=[1,0,0x16] or not final['health'] or final_keys!=1:raise RuntimeError('First-key live completion contract failed')
  except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
  finally:final=json_state(snapshot(base.pyboy));final_keys=int(base.pyboy.memory[SMALL_KEYS]);journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False)
 try:
  replay.reset(seed=0)
  for row in rows:
   info=apply(replay,row['command'])[4];assert fingerprint(replay)==row['fingerprint'];assert json_state(snapshot(replay.pyboy))==json_state(row['after']);assert replay.frames==row['frame'] and info['events']==row['events']
  assert replay.journal.state()==journal and int(replay.pyboy.memory[SMALL_KEYS])==final_keys
 finally:replay.close()
 result={'spec':spec,'success':failure is None,'failure':failure,'initial':initial,'final':final,'final_small_keys':final_keys,'candidate_decisions':candidate_decisions,'teacher_recovery':fallback,'damage_raw':initial['health']-final['health'],'exact_replay':True,'evidence':evidence,'seconds':round(time.monotonic()-began,3)}
 write(out/'result.json',result);write(out/'manifest.json',{'artifacts':{p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}});print(json.dumps(result),flush=True);return result
def main(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(Path(__file__))!=plan['evaluator_sha256']:raise ValueError('Frozen evaluator changed')
 experiment=ROOT/plan['experiment']
 if file_hash(experiment)!=plan['experiment_sha256']:raise ValueError('Frozen experiment changed')
 checkpoint=ROOT/plan['candidate']
 if file_hash(checkpoint)!=plan['candidate_sha256']:raise ValueError('Frozen candidate changed')
 saved=torch.load(checkpoint,map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval();out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');results=[]
 for spec in json.loads(experiment.read_text())['development_panel']['cases']:
  results.append(run_case(out,spec,plan,model,saved));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'teacher_recoveries':sum(r['teacher_recovery'] for r in results),'candidate_decisions':sum(r['candidate_decisions'] for r in results),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

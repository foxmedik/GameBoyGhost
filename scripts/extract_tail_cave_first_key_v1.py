"""Extract first-key combat and pickup actions from the verified teacher."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
from control_context import ControlContext
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_teacher import SMALL_KEYS
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import action_tuple,feature
from progression_local_control import json_state
from run_toadstool_progression import apply
PLAN=ROOT/'configs/tail_cave_first_key_model_v1.json';GOAL={'room':[1,0,0x16],'x':40,'y':60,'cell':[2,3]}
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text());teacher=ROOT/plan['teacher_run']
 if file_hash(Path(__file__))!=plan['extractor_sha256'] or file_hash(teacher/'summary.json')!=plan['teacher_summary_sha256']:raise ValueError('Frozen extractor or teacher changed')
 summary=json.loads((teacher/'summary.json').read_text());xs=[];ys=[];provenance=[]
 if summary['successes']<summary['required_successes'] or summary['validation_loaded']:raise ValueError('Teacher gate failed')
 for result in summary['results']:
  folder=teacher/result['spec']['id'];manifest=json.loads((folder/'manifest.json').read_text())
  for name,expected in manifest['artifacts'].items():
   if file_hash(folder/name)!=expected:raise ValueError(f'Teacher artifact changed: {folder/name}')
  rows=[json.loads(x) for x in (folder/'trajectory.jsonl').read_text().splitlines()]
  env=ProgressionEnv(folder/'game.gbc',folder/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False);context=ControlContext(env)
  try:
   env.reset(seed=0)
   for row in rows:
    state=json_state(snapshot(env.pyboy));label=action_tuple(row['command'])
    if state['room']==[1,0,0x16] and not state['dialog_state'] and not int(env.pyboy.memory[SMALL_KEYS]) and row['command'].get('timing')!='emulated_frames':
     xs.append(feature(env,context,state,GOAL));ys.append(label);provenance.append([result['spec']['id'],row['decision']])
    info=apply(env,row['command'])[4]
    if json_state(snapshot(env.pyboy))!=json_state(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError(f'Replay mismatch: {folder}/{row["decision"]}')
  finally:env.close()
 out.mkdir(parents=True,exist_ok=False);np.savez_compressed(out/'train.npz',x=np.stack(xs),y=np.asarray(ys,dtype=np.int64),provenance=np.asarray(provenance))
 manifest={'schema':'tail-cave-first-key-data-v1','rows':len(xs),'cases':summary['successes'],'train_sha256':file_hash(out/'train.npz'),'experiment_sha256':file_hash(PLAN),'extractor_sha256':file_hash(Path(__file__)),'validation_loaded':False};write(out/'manifest.json',manifest);shutil.copy2(PLAN,out/'plan.json');print(json.dumps(manifest,indent=2))
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

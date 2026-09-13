"""Extract compact Tail Cave specialist data from verified development traces."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_controller import tail_feature
from gameboy_agent.tail_cave_teacher import SMALL_KEYS
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import action_tuple,history_features
from progression_local_control import json_state
from run_toadstool_progression import apply
PLAN=ROOT/'configs/tail_cave_specialist_v3.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(Path(__file__))!=plan['extractor_sha256']:raise ValueError('Frozen extractor changed')
 xs=[];ys=[];provenance=[]
 for source_spec in plan['data_sources']:
  source=ROOT/source_spec['run'];summary_path=source/'summary.json'
  if file_hash(summary_path)!=source_spec['summary_sha256']:raise ValueError(f'Source summary changed: {source}')
  summary=json.loads(summary_path.read_text())
  if summary['successes']<summary['required_successes'] or summary['validation_loaded']:raise ValueError(f'Source gate failed: {source}')
  for result in summary['results']:
   if not result['success']:continue
   folder=source/result['spec']['id'];rows=[json.loads(x) for x in (folder/'trajectory.jsonl').read_text().splitlines()];env=ProgressionEnv(folder/'game.gbc',folder/'initial.state',max_steps=1024,max_frames=60000,reject_completed_start=False)
   try:
    env.reset(seed=0)
    for row in rows:
     state=json_state(snapshot(env.pyboy))
     if state['room']==[1,0,0x16] and not state['dialog_state'] and not int(env.pyboy.memory[SMALL_KEYS]) and row['command'].get('timing')!='emulated_frames':
      xs.append(tail_feature(env,history_features(env.episode_actions)));ys.append(action_tuple(row['command']));provenance.append([source_spec['run'],result['spec']['id'],row['decision']])
     info=apply(env,row['command'])[4]
     if json_state(snapshot(env.pyboy))!=json_state(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError(f'Replay mismatch: {folder}/{row["decision"]}')
   finally:env.close()
 out.mkdir(parents=True,exist_ok=False);np.savez_compressed(out/'train.npz',x=np.stack(xs),y=np.asarray(ys,dtype=np.int64),provenance=np.asarray(provenance));manifest={'schema':'tail-cave-specialist-data-v3','rows':len(xs),'inputs':xs[0].shape[0],'train_sha256':file_hash(out/'train.npz'),'experiment_sha256':file_hash(PLAN),'validation_loaded':False};write(out/'manifest.json',manifest);shutil.copy2(PLAN,out/'plan.json');print(json.dumps(manifest,indent=2))
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

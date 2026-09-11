"""Read-only counterfactual model queries at physically replayed failure states."""
import json,sys,tempfile,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import pyarrow.parquet as pq
import torch
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.navigation import NavigationController
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.dataset import sha256
from control_context import ControlContext
from run_skill_chain import senses
OUT=ROOT/'runs/v7-sword-teacher-v1'

def inspect(prefix):
 torch.set_num_threads(1);plan=json.loads((OUT/'plan.json').read_text());c=next(c for c in plan['cases'] if c['segment_id'].startswith(prefix));source=OUT/f"{c['segment_id']}-v7_gated.json";r=json.loads(source.read_text());batch=Path(plan['source_batch']);path=batch/c['source_path'];assert sha256(path)==c['source_sha256'];meta=json.loads((path.parent/'manifest.json').read_text());actions=pq.read_table(path,columns=['action']).to_pydict()['action'][:c['step']]+r['actions'];policy=NavigationController(plan['policy_path'])
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(batch/'assets/game.gbc',rom);base=TrainingEnv(rom,batch/'assets'/f"{c['start']}.state",max_steps=meta['max_steps'],sword_curriculum=False);env=ControlContext(base)
  try:
   obs,_=env.reset(seed=meta['seed'])
   for i,a in enumerate(actions):
    if i==c['step']:base.config['max_steps']=base.total_steps+129;assert fingerprint(base)==r['start_fingerprint']
    obs,*_=env.step(np.asarray(a))
   assert fingerprint(base)==r['final_fingerprint'];s=senses(base);queries=[]
   for button in [0,1,2]:
    edited={**obs,'control':obs['control'].copy()};edited['control'][4]=button/3
    queries.append(dict(pretend_previous_button=button,action=policy.action(edited,s.room,c['goal'])))
   assert fingerprint(base)==r['final_fingerprint']
   return dict(case_id=c['segment_id'],source_sha256=sha256(source),state=s.__dict__,goal=c['goal'],observed_previous_button=float(obs['control'][4])*3,queries=queries,replay_verified=True,environment_unchanged=True)
  finally:env.close()

def main():
 with ProcessPoolExecutor(max_workers=3,mp_context=mp.get_context('spawn')) as pool:results=list(pool.map(inspect,['763b4286fbad','e180088302d8','c975b2fd3b62']))
 r=dict(results=results,interpretation='Only the model input previous-button feature changes; queries never execute actions or alter environment state. Sensitivity demonstrates dependence on button history at these states, not that spoofing history is a safe remedy.')
 (OUT/'button-history-diagnostic.json').write_text(json.dumps(r,indent=2));(ROOT/'reports/v7-sword-button-history.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
if __name__=='__main__':main()

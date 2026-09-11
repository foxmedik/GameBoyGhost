"""Exact cliff handoff replay and shortest-suffix label audit; no training."""
import json,sys,tempfile,shutil
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import torch
from gameboy_agent.dataset import sha256
from gameboy_agent.navigation import NavigationController,encode
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.training_env import TrainingEnv
from control_context import ControlContext
from run_skill_chain import senses
READ=lambda p:json.loads(Path(p).read_text())

def replay(job):
 version,start=job;torch.set_num_threads(1);folder=ROOT/f'runs/navigation-routes-{version}/candidate/room_loop-{start}';r=READ(folder/'result.json');policy=NavigationController(ROOT/f'runs/navigation-routes-{version}/model/epoch-008.pt');entry=r['progress']['leg_start'];goal=r['route']['goals'][2]
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom);base=TrainingEnv(rom,folder/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base)
  try:
   obs,_=env.reset(seed=0);sample=None
   for i,action in enumerate(r['actions']):
    if i==entry:
     state=senses(base);x=encode(obs,state.room,goal['room'],goal['x'],goal['y']);sample=dict(version=version,start=start,entry_step=i,state=state.__dict__,entry_fingerprint=fingerprint(base),features=x.tolist(),predicted_action=policy.action(obs,state.room,goal),recorded_action=action)
    obs,*_=env.step(np.asarray(action))
   assert sample is not None and fingerprint(base)==r['fingerprint'];sample['full_replay_verified']=True
   return sample
  finally:env.close()

def main():
 out=ROOT/'runs/cliff-entry-audit-v2';out.mkdir(exist_ok=False)
 parent=torch.load(ROOT/'runs/navigation-routes-v7/model/epoch-008.pt',map_location='cpu');mask=parent['input_mask'];records=defaultdict(list);cliff_paths={};curated={}
 training=READ(ROOT/'runs/navigation-routes-v8/training-plan.json')
 # Reconstruct the actual trainer's sorted traversal, including preservation.
 for manifest in sorted((ROOT/'runs/navigation-routes-v8/data').glob('*/manifest.json')):
  m=READ(manifest);assert m['replay_verified']
  for a in m['paths']:
   p=manifest.parent/a['file'];assert sha256(p)==a['sha256'];d=np.load(p);assert np.array_equal(d['y'],a['actions'])
   for i,(x,y) in enumerate(zip(d['x'],d['y'])):
    key=(x*mask).tobytes();row=dict(path=str(p.relative_to(ROOT)),row=i,remaining=len(d['y'])-i,movement=int(y[0]),button=int(y[1]))
    if key not in curated or row['remaining']<curated[key]['remaining']:curated[key]=row
    if p.parent.name.startswith('cliff'):records[key].append(row)
   if p.parent.name.startswith('cliff'):cliff_paths[str(p.relative_to(ROOT))]=dict(spec=a,first=d['x'][0],source=manifest)
 assert len(curated)==training['target_unique_states']
 conflicts=[]
 for key,rows in records.items():
  if len({r['movement'] for r in rows})<2:continue
  paths=defaultdict(set)
  for r in rows:paths[r['path']].add(r['movement'])
  conflicts.append(dict(occurrences=rows,selected=curated[key],within_path=any(len(v)>1 for v in paths.values())))
 with ProcessPoolExecutor(max_workers=6,mp_context=mp.get_context('spawn')) as pool:entries=list(pool.map(replay,[(v,s) for v in ['v7','v8'] for s in ['house','beach','approach']]))
 for e in entries:
  x=np.asarray(e.pop('features'),dtype=np.float32);np.save(out/f"{e['version']}-{e['start']}-entry.npy",x);key=(x*mask).tobytes()
  matches=[dict(path=p,origin_fingerprint_match=v['spec']['initial']==e['entry_fingerprint'],teacher_action=v['spec']['actions'][0]) for p,v in cliff_paths.items() if np.array_equal(x*mask,v['first']*mask)]
  e['matching_demo_entries']=matches;e['curated_label']=curated.get(key)
  # Teacher-forced query on this exact replayed input, without stepping emulator.
  e['model_queries']={}
  for v in ['v7','v8']:
   controller=NavigationController(ROOT/f'runs/navigation-routes-{v}/model/epoch-008.pt')
   with torch.no_grad():z=controller.model(torch.from_numpy((x-controller.mean)/controller.scale*controller.mask)).numpy()
   e['model_queries'][v]=dict(movement=int(z[:5].argmax()),button=int(z[5:].argmax()),movement_logits=z[:5].tolist())
 result=dict(entries=entries,raw_conflicting_cliff_states=len(conflicts),conflicts_within_single_path=sum(c['within_path'] for c in conflicts),conflicts=conflicts,curated_state_count=len(curated),source_training_plan_sha256=sha256(ROOT/'runs/navigation-routes-v8/training-plan.json'),training_performed=False,full_replays_verified=True,reserved_evaluation_used=False,interpretation='Conflicting successful actions can be alternatives or hidden-state aliases. Matching encoded inputs does not imply identical emulator state. Reconstructed curation retains shortest remaining suffix exactly as v8 trainer.')
 (out/'result.json').write_text(json.dumps(result,indent=2));(ROOT/'reports/cliff-entry-audit-v2.json').write_text(json.dumps(result,indent=2));shutil.copy2(__file__,out/'source.py')
 print(json.dumps({k:result[k] for k in ('entries','raw_conflicting_cliff_states','conflicts_within_single_path')},indent=2))
if __name__=='__main__':main()

"""Replay learned cliff stalls and test v7 from verified cliff endpoints."""
import json,sys,shutil,tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from gameboy_agent.navigation import NavigationController,encode,reached
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.dataset import sha256
from control_context import ControlContext
from run_skill_chain import senses
READ=lambda p:json.loads(Path(p).read_text())
OUT=ROOT/'runs/cliff-stall-diagnostic-v1'

def trial(start):
 torch.set_num_threads(1);policies={v:NavigationController(ROOT/f'runs/navigation-routes-{v}/model/epoch-008.pt') for v in ['v7','v9']};p=policies['v9'];rows=[];labels={}
 for manifest in sorted((ROOT/'runs/navigation-routes-v9/data').glob('*/manifest.json')):
  for a in READ(manifest)['paths']:
   asset=manifest.parent/a['file'];assert sha256(asset)==a['sha256'];d=np.load(asset)
   for i,(x,y) in enumerate(zip(d['x'],d['y'])):
    key=(x*p.mask).tobytes();r=dict(path=str(asset.relative_to(ROOT)),row=i,remaining=len(d['y'])-i,action=y.tolist())
    if key not in labels or r['remaining']<labels[key]['remaining']:labels[key]=r
    if manifest.parent.name.startswith('cliff-repaired-approach'):rows.append((x,r))
 xx=np.stack([x for x,r in rows]);folder=ROOT/f'runs/navigation-routes-v9/candidate/room_loop-{start}';run=READ(folder/'result.json');entry=run['progress']['leg_start'];goal=run['route']['goals'][2];dest=OUT/start;dest.mkdir()
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom)
  def restore(folder,actions):
   base=TrainingEnv(rom,folder/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=0)
   for a in actions:obs,*_=env.step(np.asarray(a))
   return base,env,obs
  base,env,obs=restore(folder,[]);events=[];xs=[]
  try:
   for i,a in enumerate(run['actions']):
    if i>=entry:
     s=senses(base);x=encode(obs,s.room,goal['room'],goal['x'],goal['y']);xs.append(x)
     if i-entry<24 or i==len(run['actions'])-1:
      distance=np.mean(((xx-x)/p.scale*p.mask)**2,axis=1);near=int(distance.argmin());queries={}
      for v,policy in policies.items():
       with torch.no_grad():z=policy.model(torch.from_numpy((x-policy.mean)/policy.scale*policy.mask)).numpy()
       queries[v]=dict(action=[int(z[:5].argmax()),int(z[5:].argmax())],movement_logits=z[:5].tolist())
      events.append(dict(step=i-entry,state=s.__dict__,action=a,queries=queries,exact_curated=labels.get((x*p.mask).tobytes()),nearest_cliff={**rows[near][1], 'squared_normalized_distance':float(distance[near])}))
    obs,*_=env.step(np.asarray(a))
   assert fingerprint(base)==run['fingerprint'];base.pyboy.screen.image.save(dest/'stall.png')
  finally:env.close()
  np.save(dest/'stall-features.npy',np.stack(xs))
  source=ROOT/f'runs/cliff-splice-repair-v1/v7-{start}/manifest.json';m=READ(source);folder=ROOT/f'runs/navigation-routes-v7/candidate/room_loop-{start}';goal=READ(folder/'result.json')['route']['goals'][3];prefix=m['prefix']+m['actions'];base,env,obs=restore(folder,prefix);actions=[];damage=0;status='timeout'
  try:
   assert fingerprint(base)==m['final_fingerprint'];initial=fingerprint(base)
   for _ in range(256):
    s=senses(base)
    if reached(s.room,s.x,s.y,goal):status='success';break
    a=policies['v7'].action(obs,s.room,goal);actions.append(a);obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);damage+=max(0,s.health-after.health)
    if after.health==0:status='death';break
    if done or truncated:status='environment_end';break
   s=senses(base)
   if reached(s.room,s.x,s.y,goal):status='success'
   final=fingerprint(base);state=s.__dict__
  finally:env.close()
  base,env,obs=restore(folder,prefix+actions)
  try:assert fingerprint(base)==final
  finally:env.close()
 r=dict(start=start,stall_events=events,historical_replay_verified=True,parent_return=dict(status=status,steps=len(actions),damage=damage,goal=goal,initial_fingerprint=initial,final_fingerprint=final,final_state=state,actions=actions,prefix=prefix,replay_verified=True))
 (dest/'result.json').write_text(json.dumps(r,indent=2));return r

def main():
 OUT.mkdir(exist_ok=False);plan=dict(starts=['house','beach','approach'],source_sha256=sha256(__file__),protocol='Replay v9 failures with read-only logits and nearest curated labels. Then run unchanged v7 for 256 actions from each verified v7 teacher cliff endpoint; independently replay. No new training or policy selection.',reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'source.py')
 with ProcessPoolExecutor(max_workers=3,mp_context=mp.get_context('spawn')) as pool:results=list(pool.map(trial,plan['starts']))
 report=dict(results=results,plan_sha256=sha256(OUT/'plan.json'),reserved_evaluation_used=False)
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/cliff-stall-diagnostic-v1.json').write_text(json.dumps(report,indent=2))
 print(json.dumps([dict(start=r['start'],parent_return={k:r['parent_return'][k] for k in ['status','steps','damage']}) for r in results]),flush=True)
if __name__=='__main__':main()

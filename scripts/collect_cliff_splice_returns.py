"""Bounded fixed return continuations from newly repaired cliff endpoints."""
import json,sys,shutil,tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import torch
from gameboy_agent.dataset import sha256
from gameboy_agent.navigation import encode,reached
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.training_env import TrainingEnv
from control_context import ControlContext
from run_skill_chain import senses
OUT=ROOT/'runs/cliff-splice-returns-v1';READ=lambda p:json.loads(Path(p).read_text())

def trial(job):
 torch.set_num_threads(1);version,start=job['version'],job['start'];folder=ROOT/f'runs/navigation-routes-{version}/candidate/room_loop-{start}';r=READ(folder/'result.json');prefix=r['actions'][:r['progress']['leg_start']]+job['approach_actions'];goal=r['route']['goals'][3];actions=job['actions'];dest=OUT/job['id'];dest.mkdir()
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom)
  def restore():
   base=TrainingEnv(rom,folder/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=0)
   for a in prefix:obs,*_=env.step(np.asarray(a))
   assert fingerprint(base)==job['initial_fingerprint']
   return base,env,obs
  base,env,obs=restore();xs=[];used=[];damage=0;status='actions_exhausted'
  try:
   for a in actions[:256]:
    s=senses(base)
    if reached(s.room,s.x,s.y,goal):status='success';break
    xs.append(encode(obs,s.room,goal['room'],goal['x'],goal['y']));obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);damage+=max(0,s.health-after.health);used.append(a)
    if after.health==0:status='death';break
    if done or truncated:status='environment_end';break
   s=senses(base)
   if reached(s.room,s.x,s.y,goal):status='success'
   final=fingerprint(base);final_state=s.__dict__
   base.pyboy.screen.image.save(dest/'final.png')
  finally:env.close()
  base,env,obs=restore()
  try:
   for i,a in enumerate(used):
    s=senses(base);assert np.array_equal(encode(obs,s.room,goal['room'],goal['x'],goal['y']),xs[i]);obs,*_=env.step(np.asarray(a))
   assert fingerprint(base)==final
  finally:env.close()
  accepted=status=='success' and damage==0
  if accepted:np.savez_compressed(dest/'demonstration.npz',x=np.stack(xs),y=np.asarray(used,dtype=np.int64))
  m=dict(id=job['id'],version=version,start=start,status=status,accepted=accepted,damage=damage,steps=len(used),actions=used,prefix=prefix,goal=goal,initial_fingerprint=job['initial_fingerprint'],final_fingerprint=final,final_state=final_state,replay_verified=True,features_replay_verified=True,source_job=job,supervision='privileged scripted continuation of verified source actions; not learned',artifacts={p.name:sha256(p) for p in dest.iterdir()})
  (dest/'manifest.json').write_text(json.dumps(m,indent=2));return {k:m[k] for k in ('id','version','start','status','accepted','damage','steps','initial_fingerprint','final_fingerprint')}

def main():
 OUT.mkdir(exist_ok=False);jobs=[]
 for start in ['house','beach','approach']:
  source=ROOT/f'runs/cliff-splice-repair-v1/v7-{start}/manifest.json';approach=READ(source);assert approach['accepted'] and approach['replay_verified'];choices=[];seen=set()
  for manifest in sorted((ROOT/'runs/navigation-routes-v8/data').glob(f'cliff-return_west-{start}-*/manifest.json')):
   m=READ(manifest)
   for a in m['paths']:
    p=manifest.parent/a['file'];assert a['replay_verified'] and sha256(p)==a['sha256'];d=np.load(p);actions=d['y'].tolist();key=json.dumps(actions)
    if key in seen:continue
    seen.add(key);choices.append((len(actions),str(p),actions,sha256(p)))
  choices.sort()
  for i,(_,p,actions,h) in enumerate(choices[:3]):
   jobs.append(dict(id=f'{start}-{i}',version='v7',start=start,approach_actions=approach['actions'],initial_fingerprint=approach['final_fingerprint'],approach_manifest_sha256=sha256(source),actions=actions,source_return=p,source_return_sha256=h))
 assert len(jobs)==9
 plan=dict(jobs=jobs,attempts_per_start=3,budget=256,rule='Three shortest distinct previously verified same-start return action sequences, fixed before execution, from the repaired approach endpoint in the same physical episode. No adaptive movement or resets at handoff.',acceptance='Zero damage, original final goal, exact feature/action and final replay.',source_sha256=sha256(__file__),training_performed=False,reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'source.py')
 with ProcessPoolExecutor(max_workers=6,mp_context=mp.get_context('spawn')) as pool:results=list(pool.map(trial,jobs))
 report=dict(results=results,accepted=sum(r['accepted'] for r in results),starts_with_safe_return=sorted({r['start'] for r in results if r['accepted']}),plan_sha256=sha256(OUT/'plan.json'),training_performed=False,reserved_evaluation_used=False)
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/cliff-splice-returns-v1.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()

"""One frozen source-suffix continuation per cliff label probe; fresh features."""
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
OUT=ROOT/'runs/cliff-splice-repair-v1';READ=lambda p:json.loads(Path(p).read_text())

def trial(job):
 torch.set_num_threads(1);version,start=job['version'],job['start'];folder=ROOT/f'runs/navigation-routes-{version}/candidate/room_loop-{start}';r=READ(folder/'result.json');prefix=r['actions'][:r['progress']['leg_start']];goal=r['route']['goals'][2];actions=job['actions'];dest=OUT/f'{version}-{start}';dest.mkdir()
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
  m=dict(version=version,start=start,status=status,accepted=accepted,damage=damage,steps=len(used),actions=used,prefix=prefix,goal=goal,initial_fingerprint=job['initial_fingerprint'],final_fingerprint=final,final_state=final_state,replay_verified=True,features_replay_verified=True,source_job=job,supervision='privileged scripted continuation of verified source actions; not learned',artifacts={p.name:sha256(p) for p in dest.iterdir()})
  (dest/'manifest.json').write_text(json.dumps(m,indent=2));return {k:m[k] for k in ('version','start','status','accepted','damage','steps','initial_fingerprint','final_fingerprint')}

def main():
 OUT.mkdir(exist_ok=False);probe=READ(ROOT/'runs/cliff-label-replay-v1/result.json');jobs=[]
 for e in probe['results']:
  path=ROOT/f"runs/cliff-label-replay-v1/{e['version']}-{e['start']}.json";r=READ(path);actions=list(r['actions']);continuation=None
  if r['status']=='coverage_miss':
   if r['events']:
    label=r['events'][-1]['label'];source=ROOT/label['path'];row=label['row']+1
   else:
    candidates=[]
    for source in (ROOT/'runs/navigation-routes-v8/data'/f"cliff-west_neighbor-{e['start']}").glob('*.npz'):
     d=np.load(source);candidates.append((len(d['y']),str(source),source))
    source=min(candidates)[2];row=0
   d=np.load(source);actions+=d['y'][row:].tolist();continuation=dict(source=str(source.relative_to(ROOT)),sha256=sha256(source),row=row)
  jobs.append(dict(version=e['version'],start=e['start'],actions=actions,initial_fingerprint=r['initial_fingerprint'],source_probe_sha256=sha256(path),continuation=continuation))
 plan=dict(jobs=jobs,budget=256,attempts_per_origin=1,rule='Keep successful lookup path; for coverage misses append remaining actions of last selected demonstration, or shortest same-start demonstration if miss is at entry. Stop at original goal. No search or adaptive action changes.',source_sha256=sha256(__file__),source_probe_sha256=sha256(ROOT/'runs/cliff-label-replay-v1/result.json'),selection='Accept only independently replayed, zero-damage successes with freshly encoded original-goal features.',training_performed=False,reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'source.py')
 with ProcessPoolExecutor(max_workers=6,mp_context=mp.get_context('spawn')) as pool:results=list(pool.map(trial,jobs))
 report=dict(results=results,accepted=sum(r['accepted'] for r in results),origins=len(results),unique_accepted_origins=len({r['initial_fingerprint'] for r in results if r['accepted']}),training_performed=False,reserved_evaluation_used=False,plan_sha256=sha256(OUT/'plan.json'))
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/cliff-splice-repair-v1.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()

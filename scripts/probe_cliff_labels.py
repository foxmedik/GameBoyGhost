"""Diagnostic exact-label replay: no learned runtime or fallback policy."""
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
READ=lambda p:json.loads(Path(p).read_text())
OUT=ROOT/'runs/cliff-label-replay-v1'

def label_map():
 s=torch.load(ROOT/'runs/navigation-routes-v7/model/epoch-008.pt',map_location='cpu');mask=s['input_mask'];labels={}
 for manifest in sorted((ROOT/'runs/navigation-routes-v8/data').glob('*/manifest.json')):
  m=READ(manifest);assert m['replay_verified']
  for a in m['paths']:
   p=manifest.parent/a['file'];assert sha256(p)==a['sha256'];d=np.load(p);assert np.array_equal(d['y'],a['actions'])
   for i,(x,y) in enumerate(zip(d['x'],d['y'])):
    key=(x*mask).tobytes();cost=len(d['y'])-i
    if key not in labels or cost<labels[key]['remaining']:
     labels[key]=dict(action=y.tolist(),remaining=cost,path=str(p.relative_to(ROOT)),row=i)
 assert len(labels)==READ(ROOT/'runs/navigation-routes-v8/training-plan.json')['target_unique_states']
 return labels,mask

def trial(job):
 version,start=job;torch.set_num_threads(1);labels,mask=label_map();folder=ROOT/f'runs/navigation-routes-{version}/candidate/room_loop-{start}';r=READ(folder/'result.json');prefix=r['actions'][:r['progress']['leg_start']];goal=r['route']['goals'][2]
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom)
  def restore(actions):
   base=TrainingEnv(rom,folder/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=0)
   for a in prefix+actions:obs,*_=env.step(np.asarray(a))
   return base,env,obs
  base,env,obs=restore([]);initial=fingerprint(base);expected=next(e for e in READ(ROOT/'reports/cliff-entry-audit-v2.json')['entries'] if e['version']==version and e['start']==start);assert initial==expected['entry_fingerprint'];actions=[];events=[];damage=0;status='timeout';frames=0
  try:
   for step in range(256):
    state=senses(base)
    if reached(state.room,state.x,state.y,goal):status='success';break
    x=encode(obs,state.room,goal['room'],goal['x'],goal['y']);key=(x*mask).tobytes();label=labels.get(key)
    if label is None:
     status='coverage_miss';np.save(OUT/f'{version}-{start}-missing.npy',x);break
    action=label['action'];obs,_,done,truncated,_=env.step(np.asarray(action));after=senses(base);loss=max(0,state.health-after.health);damage+=loss;frames+=base.last_timing['frames_advanced'];actions.append(action);events.append(dict(step=step,state=state.__dict__,label=label,after=after.__dict__,damage=loss))
    if after.health==0:status='death';break
    if done or truncated:status='environment_end';break
   final=fingerprint(base);final_state=senses(base).__dict__
   if reached(senses(base).room,senses(base).x,senses(base).y,goal):status='success'
  finally:env.close()
  base,env,obs=restore(actions)
  try:assert fingerprint(base)==final
  finally:env.close()
 result=dict(version=version,start=start,status=status,steps=len(actions),damage=damage,frames=frames,goal=goal,initial_fingerprint=initial,final_fingerprint=final,final_state=final_state,actions=actions,events=events,replay_verified=True)
 (OUT/f'{version}-{start}.json').write_text(json.dumps(result,indent=2));return {k:v for k,v in result.items() if k not in ('events','actions')}

def main():
 OUT.mkdir(exist_ok=False);jobs=[(v,s) for v in ['v7','v8'] for s in ['house','beach','approach']]
 plan=dict(jobs=jobs,budget=256,rule='Exact normalized-mask input key; choose shortest remaining suffix with sorted-manifest tie order, exactly as v8 trainer. Stop on any missing key. No nearest neighbor, recovery or v7 fallback.',purpose='Diagnostic teacher-label executability only; not a learned navigator and never eligible for promotion.',source_sha256=sha256(__file__),training_plan_sha256=sha256(ROOT/'runs/navigation-routes-v8/training-plan.json'),entry_audit_sha256=sha256(ROOT/'reports/cliff-entry-audit-v2.json'),reserved_evaluation_used=False,training_performed=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'source.py')
 with ProcessPoolExecutor(max_workers=6,mp_context=mp.get_context('spawn')) as pool:results=list(pool.map(trial,jobs))
 report=dict(results=results,plan_sha256=sha256(OUT/'plan.json'),all_replays_verified=True,learned_policy=False,training_performed=False,reserved_evaluation_used=False)
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/cliff-label-replay-v1.json').write_text(json.dumps(report,indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':main()

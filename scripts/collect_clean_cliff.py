"""Bounded teacher-only lane test; fresh final-goal features and continuous return."""
import json,sys,shutil,tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from gameboy_agent.navigation import encode,reached
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.dataset import sha256
from control_context import ControlContext
from run_skill_chain import senses
from navigation_recovery import teacher
READ=lambda p:json.loads(Path(p).read_text())
OUT=ROOT/'runs/cliff-clean-teacher-v1'
def goal(room,x,y):return dict(room=[0,0,room],x=x,y=y)

def trial(job):
 start,lane=job;torch.set_num_threads(1);folder=ROOT/f'runs/navigation-routes-v7/candidate/room_loop-{start}';r=READ(folder/'result.json');prefix=r['actions'][:r['progress']['leg_start']];dest=OUT/f'{start}-{lane}';dest.mkdir();results=[]
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom)
  def restore(actions):
   base=TrainingEnv(rom,folder/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=0)
   for a in actions:obs,*_=env.step(np.asarray(a))
   return base,env,obs
  for kind,index,points in [('approach',2,[goal(225,135,110),goal(225,lane,95),goal(225,lane,55),goal(226,18,64)]),('return',3,[goal(226,18,64),goal(225,lane,55),goal(225,lane,95),goal(225,135,110)])]:
   base,env,obs=restore(prefix);initial=fingerprint(base);target=r['route']['goals'][index];waypoints=points+[target];actions=[];xs=[];events=[];damage=0;cursor=0;status='timeout'
   try:
    for step in range(256):
     s=senses(base)
     if reached(s.room,s.x,s.y,target):status='success';break
     while cursor<len(points) and reached(s.room,s.x,s.y,points[cursor],tolerance=3):cursor+=1
     a=teacher(s,waypoints[cursor],None,step,0,{});xs.append(encode(obs,s.room,target['room'],target['x'],target['y']));actions.append(a);obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);damage+=max(0,s.health-after.health);events.append(dict(state=s.__dict__,action=a,after=after.__dict__,waypoint_index=cursor))
     if damage or after.health==0:status='damage';break
     if done or truncated:status='environment_end';break
    s=senses(base)
    if reached(s.room,s.x,s.y,target) and not damage:status='success'
    final=fingerprint(base);final_state=s.__dict__;base.pyboy.screen.image.save(dest/f'{kind}-final.png')
   finally:env.close()
   base,env,obs=restore(prefix)
   try:
    assert fingerprint(base)==initial
    for x,a in zip(xs,actions):
     s=senses(base);assert np.array_equal(x,encode(obs,s.room,target['room'],target['x'],target['y']));obs,*_=env.step(np.asarray(a))
    assert fingerprint(base)==final
   finally:env.close()
   accepted=status=='success' and damage==0;asset=dest/f'{kind}.npz'
   if accepted:np.savez_compressed(asset,x=np.stack(xs),y=np.asarray(actions,dtype=np.int64))
   m=dict(start=start,lane=lane,kind=kind,status=status,accepted=accepted,steps=len(actions),damage=damage,prefix=prefix,actions=actions,goal=target,teacher_waypoints=points,teacher_tolerance=3,initial_fingerprint=initial,final_fingerprint=final,final_state=final_state,replay_verified=True,features_replay_verified=True,source_run=str(folder),source_result_sha256=sha256(folder/'result.json'),asset=asset.name if accepted else None,asset_sha256=sha256(asset) if accepted else None,events=events)
   (dest/f'{kind}.json').write_text(json.dumps(m,indent=2));results.append({k:v for k,v in m.items() if k not in ('events','actions','prefix')})
   if not accepted:break
   prefix=prefix+actions
 return results

def main():
 OUT.mkdir(exist_ok=False);jobs=[(s,lane) for s in ['house','beach','approach'] for lane in [126,124,122]];plan=dict(jobs=jobs,budget_per_goal=256,attempts_per_lane=1,teacher='Existing deterministic movement teacher, attempt 0, alternating sword. Tight three-pixel waypoint tolerance, lanes derived from previously verified return corridor. No random recovery or adaptive retries.',selection='Keep all zero-damage successes with independent feature/final replay; evaluate return continuously only after safe approach.',source_sha256=sha256(__file__),runtime_waypoints_used=False,reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'source.py')
 with ProcessPoolExecutor(max_workers=3,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for rs in pool.map(trial,jobs):results.extend(rs);print(json.dumps([{k:r[k] for k in ['start','lane','kind','status','steps','damage']} for r in rs]),flush=True)
 report=dict(results=results,plan_sha256=sha256(OUT/'plan.json'),runtime_waypoints_used=False,reserved_evaluation_used=False)
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/cliff-clean-teacher-v1.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()

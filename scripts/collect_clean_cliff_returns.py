"""Three frozen return continuations from each clean lane-124 cliff arrival."""
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
OUT=ROOT/'runs/cliff-clean-returns-v1'
def goal(room,x,y):return dict(room=[0,0,room],x=x,y=y)

def trial(job):
 start,mode=job;lane=124;torch.set_num_threads(1);folder=ROOT/f'runs/navigation-routes-v7/candidate/room_loop-{start}';r=READ(folder/'result.json');source=READ(ROOT/f'runs/cliff-clean-teacher-v1/{start}-124/approach.json');assert source['accepted'];prefix=source['prefix']+source['actions'];recorded=READ(ROOT/f'runs/cliff-splice-repair-v1/v7-{start}/manifest.json');import glob;choices=[READ(p) for p in (ROOT/'runs/cliff-splice-returns-v1').glob(f'{start}-*/manifest.json')];recorded=min((m for m in choices if m['accepted']),key=lambda m:m['steps'])['actions'];dest=OUT/f'{start}-{mode}';dest.mkdir();results=[]
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom)
  def restore(actions):
   base=TrainingEnv(rom,folder/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=0)
   for a in actions:obs,*_=env.step(np.asarray(a))
   return base,env,obs
  for kind,index,points in [('return',3,[goal(226,18,64),goal(225,lane,55),goal(225,lane,95),goal(225,135,110)])]:
   base,env,obs=restore(prefix);initial=fingerprint(base);assert initial==source['final_fingerprint'];target=r['route']['goals'][index];waypoints=points+[target];actions=[];xs=[];events=[];damage=0;cursor=0;status='timeout'
   try:
    for step in range(256):
     s=senses(base)
     if reached(s.room,s.x,s.y,target):status='success';break
     while cursor<len(points) and reached(s.room,s.x,s.y,points[cursor],tolerance=3):cursor+=1
     a=teacher(s,waypoints[cursor],None,step+(mode=='press_first'),0,{})
     if mode=='recorded':
      if step>=len(recorded):status='actions_exhausted';break
      a=recorded[step]
     elif step<2:a=[2,(step+int(mode=='press_first'))%2]
     xs.append(encode(obs,s.room,target['room'],target['x'],target['y']));actions.append(a);obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);damage+=max(0,s.health-after.health);events.append(dict(state=s.__dict__,action=a,after=after.__dict__,waypoint_index=cursor))
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
   m=dict(start=start,lane=lane,mode=mode,kind=kind,status=status,accepted=accepted,steps=len(actions),damage=damage,prefix=prefix,actions=actions,goal=target,teacher_waypoints=points,teacher_tolerance=3,initial_fingerprint=initial,final_fingerprint=final,final_state=final_state,replay_verified=True,features_replay_verified=True,source_run=str(folder),source_result_sha256=sha256(folder/'result.json'),asset=asset.name if accepted else None,asset_sha256=sha256(asset) if accepted else None,events=events)
   (dest/f'{kind}.json').write_text(json.dumps(m,indent=2));results.append({k:v for k,v in m.items() if k not in ('events','actions','prefix')})
   if not accepted:break
   prefix=prefix+actions
 return results

def main():
 OUT.mkdir(exist_ok=False);jobs=[(s,mode) for s in ['house','beach','approach'] for mode in ['recorded','down_first','press_first']];plan=dict(jobs=jobs,budget_per_goal=256,attempts_per_lane=1,teacher='Exactly three frozen continuations per lane-124 endpoint: shortest prior safe same-start recorded return; two initial downward actions then clean teacher; same downward teacher with reversed button phase. No adaptive retries.',selection='Keep all zero-damage successes with independent feature/final replay; evaluate return continuously only after safe approach.',source_sha256=sha256(__file__),runtime_waypoints_used=False,reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'source.py')
 with ProcessPoolExecutor(max_workers=3,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for rs in pool.map(trial,jobs):results.extend(rs);print(json.dumps([{k:r[k] for k in ['start','mode','kind','status','steps','damage']} for r in rs]),flush=True)
 report=dict(results=results,plan_sha256=sha256(OUT/'plan.json'),runtime_waypoints_used=False,reserved_evaluation_used=False)
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/cliff-clean-returns-v1.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()

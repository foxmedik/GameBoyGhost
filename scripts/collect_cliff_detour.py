"""Physically test bounded teacher waypoint detours; policy sees only final goals."""
import json,sys,shutil,tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256
from navigation_recovery import teacher

def read(p):return json.loads(Path(p).read_text())
def goal(room,x,y):return dict(room=[0,0,room],x=x,y=y)
PLANS={
 'return_west':[goal(226,18,64),goal(225,126,55),goal(225,126,95),goal(225,135,110)],
 'east_inside':[goal(226,138,110),goal(226,138,55)],
 'east_beach':[goal(242,90,18),goal(242,142,18),goal(226,140,118),goal(226,140,55)],
 'west_inside':[goal(226,20,115),goal(226,20,55)],
 'west_neighbor':[goal(225,135,110),goal(225,135,50),goal(226,18,50)],
}
def collect_job(args):
 import torch
 from gameboy_agent.training_env import TrainingEnv
 from gameboy_agent.navigation import encode,reached
 from gameboy_agent.checkpoint import fingerprint
 from control_context import ControlContext
 from run_skill_chain import senses
 torch.set_num_threads(1)
 start,plan_name,out,*extra=args;prior=extra[0] if extra else None;out=Path(out);suffix=f'-{prior["id"]}' if prior else '';dest=out/f'cliff-{plan_name}-{start}{suffix}';dest.mkdir();run=ROOT/f'runs/navigation-routes-v7/candidate/room_loop-{start}';r=read(run/'result.json');prefix=r['actions'][:r['progress']['leg_start']];target=r['route']['goals'][3 if prior else 2];prefix=prior['prefix']+prior['actions'] if prior else prefix;attempts=[];paths=[]
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(run/'game.gbc',rom)
  def restore(actions):
   base=TrainingEnv(rom,run/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=0)
   for a in actions:obs,_,_,_,_=env.step(np.asarray(a))
   base.config['max_steps']=base.total_steps+513
   return base,env,obs
  for attempt in range(32):
   base,env,obs=restore(prefix)
   try:
    origin=fingerprint(base);actions=[];xs=[];damage=0;visits={};cursor=0;leg_start=0;success=False
    waypoints=PLANS[plan_name]+[target]
    for step in range(256):
     state=senses(base)
     while cursor<len(waypoints) and reached(state.room,state.x,state.y,waypoints[cursor],tolerance=prior.get('waypoint_tolerance',8) if prior else 8):cursor+=1;leg_start=step;visits={}
     if reached(state.room,state.x,state.y,target):success=True;break
     if cursor==len(waypoints) or step-leg_start>=96:break
     a=teacher(state,waypoints[cursor],None,step-leg_start,attempt,visits)
     xs.append(encode(obs,state.room,target['room'],target['x'],target['y']));actions.append(a)
     obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);damage+=max(0,state.health-after.health)
     if damage or after.health==0 or done or truncated:break
    state=senses(base);success=success or (damage==0 and reached(state.room,state.x,state.y,target));final=fingerprint(base)
    attempts.append(dict(attempt=attempt,success=success,steps=len(actions),damage=damage,waypoints_completed=cursor,room=list(state.room),x=state.x,y=state.y))
    if attempt==0:base.pyboy.screen.image.save(dest/'first-attempt.png')
   finally:env.close()
   if success:
    base,env,obs=restore(prefix)
    try:
     assert fingerprint(base)==origin
     for i,a in enumerate(actions):
      state=senses(base);assert np.array_equal(encode(obs,state.room,target['room'],target['x'],target['y']),xs[i]);obs,_,_,_,_=env.step(np.asarray(a))
     assert fingerprint(base)==final
     state=senses(base);assert reached(state.room,state.x,state.y,target)
     p=dest/f'success-{len(paths)}.npz';np.savez_compressed(p,x=np.stack(xs),y=np.asarray(actions,dtype=np.int64));base.pyboy.screen.image.save(dest/f'success-{len(paths)}.png')
     paths.append(dict(file=p.name,sha256=sha256(p),actions=actions,prefix=prefix,goal=target,initial=origin,final=final,replay_verified=True))
    finally:env.close()
    if len(paths)>=3:break
  m=dict(paths=paths,attempts=attempts,replay_verified=True,policy_sha256=sha256(ROOT/'runs/navigation-routes-v7/model/epoch-008.pt'),source_run=str(run),source_result_sha256=sha256(run/'result.json'),teacher_waypoints=PLANS[plan_name],teacher_waypoint_tolerance=prior.get('waypoint_tolerance',8) if prior else 8,runtime_waypoints_used=False)
  (dest/'manifest.json').write_text(json.dumps(m,indent=2))
 return dict(start=start,plan=plan_name,successes=len(paths),attempts=len(attempts))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 shutil.copy2(__file__,a.out/'collector_source.py')
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for r in pool.map(collect_job,[(s,p,str(a.out)) for s in ['house','beach','approach'] for p in ['east_inside','east_beach','west_inside','west_neighbor']]):results.append(r);print(json.dumps(r),flush=True)
 (a.out/'collection.json').write_text(json.dumps(results,indent=2))

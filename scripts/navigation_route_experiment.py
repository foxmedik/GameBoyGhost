"""Frozen route baseline and verified correction collection at handoffs."""
import argparse
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import json
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256


def read(path):return json.loads(Path(path).read_text())

def evaluate(out,checkpoint,label):
    out=Path(out);plan=read(out/'plan.json');dest=out/label;dest.mkdir(exist_ok=False)
    def job(spec):
        route,start=spec;target=dest/f'{route["id"]}-{start}'
        with target.with_suffix('.log').open('x') as log:
            subprocess.run([sys.executable,str(ROOT/'scripts/run_navigation_route.py'),'--checkpoint',str(checkpoint),'--route-id',route['id'],
                '--curriculum',str(out/'curriculum.json'),'--start',start,'--out',str(target)],stdout=log,stderr=subprocess.STDOUT,check=True)
        r=read(target/'result.json');summary={k:r[k] for k in ['start','status','steps','sword_step','navigation_steps','navigation_damage','progress']}
        summary['route_id']=route['id'];summary['run_path']=str(target.resolve());return summary
    specs=[(r,s) for r in plan['curriculum']['routes'] for s in plan['curriculum']['starts']]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(job,specs))
    report=dict(routes=results,complete=sum(r['status']=='success' for r in results),cases=len(results),
        goals_completed=sum(r['progress']['cursor'] for r in results),damage=sum(r['navigation_damage'] for r in results),
        deaths=sum(r['status']=='death' for r in results))
    (dest/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


def prepare(out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True);curriculum=read(ROOT/'configs/navigation_routes_v1.json');selection=read(ROOT/'configs/navigation_experiment.json')
    parent=ROOT/selection['policy_path'];assert sha256(parent)==selection['policy_sha256']
    plan=dict(curriculum=curriculum,parent=str(parent),parent_sha256=sha256(parent),epochs=8,learning_rate=1e-5,retention_weight=8,
        selection='One fixed final-epoch candidate; improve complete-route count, preserve parent route successes, no local parent success losses or damage.',
        reserved_evaluation_used=False,harness_privilege='D',source_sha256=sha256(__file__))
    (out/'plan.json').write_text(json.dumps(plan,indent=2));(out/'curriculum.json').write_text(json.dumps(curriculum,indent=2))
    shutil.copy2(__file__,out/'navigation_route_experiment.py');shutil.copy2(ROOT/'scripts/run_navigation_route.py',out/'run_navigation_route.py')
    evaluate(out,parent,'baseline')


def collect_case(args):
    import torch
    from gameboy_agent.navigation import NavigationController,encode,reached
    from gameboy_agent.training_env import TrainingEnv
    from gameboy_agent.checkpoint import fingerprint
    from control_context import ControlContext
    from run_skill_chain import senses
    from navigation_recovery import teacher
    torch.set_num_threads(1)
    run_path,checkpoint,out=args;run_path=Path(run_path);r=read(run_path/'result.json');route=r['route'];start=r['start']
    out=Path(out);target=out/f'{route["id"]}-{start}';target.mkdir();policy=NavigationController(checkpoint)
    prefix=r['actions'][:r['sword_step']];legs=[];paths=[]
    with tempfile.TemporaryDirectory() as tmp:
        rom=Path(tmp)/'game.gbc';shutil.copy2(run_path/'game.gbc',rom)
        def restore(actions):
            base=TrainingEnv(rom,run_path/'initial.state',max_steps=1600+r['budget']*len(route['goals'])+1,sword_curriculum=False)
            env=ControlContext(base);obs,_=env.reset(seed=0)
            for a in actions:obs,_,done,truncated,_=env.step(np.asarray(a))
            base.config['max_steps']=base.total_steps+385
            return base,env,obs
        # Confirm the complete baseline, including its failed handoff, replays.
        base,env,obs=restore(r['actions'])
        assert fingerprint(base)==r['fingerprint'];env.close()
        for index,goal in enumerate(route['goals']):
            entry=list(prefix);attempts=[];accepted=[]
            # First run the parent from this actual handoff. Successful earlier
            # legs remain in this same episode; no reset at a waypoint.
            origins=[('handoff',entry)]
            for origin_name,origin_prefix in origins:
                for attempt in range(33):
                    base,env,obs=restore(origin_prefix)
                    try:
                        initial=fingerprint(base);s=senses(base)
                        if reached(s.room,s.x,s.y,goal):
                            legs.append(dict(index=index,already_reached=True));break
                        actions=[];xs=[];damage=0;visits={};success=False
                        if attempt==0:base.pyboy.screen.image.save(target/f'goal-{index}-{origin_name}.png')
                        for step in range(256):
                            state=senses(base)
                            a=policy.action(obs,state.room,goal) if attempt==0 else teacher(state,goal,None,step,attempt-1,visits)
                            xs.append(encode(obs,state.room,goal['room'],goal['x'],goal['y']))
                            obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);actions.append(a)
                            damage+=max(0,state.health-after.health)
                            if damage or after.health==0:break
                            if reached(after.room,after.x,after.y,goal):success=True;break
                            if done or truncated:break
                        final=fingerprint(base)
                        attempts.append(dict(origin=origin_name,attempt=attempt,steps=len(actions),success=success,damage=damage,initial=initial,final=final))
                        if attempt==0 and not success and origin_name=='handoff' and damage==0:
                            # Recover from the actual failed policy endpoint too.
                            origins.append(('stalled',entry+actions))
                        if success:
                            accepted.append(dict(origin=origin_name,prefix=list(origin_prefix),actions=actions,x=np.stack(xs),initial=initial,final=final,attempt=attempt))
                            if attempt==0 or sum(a['origin']==origin_name for a in accepted)>=3:break
                    finally:env.close()
            main=[a for a in accepted if a['origin']=='handoff']
            if not main and legs and legs[-1].get('already_reached') and legs[-1]['index']==index:continue
            for j,a in enumerate(accepted):
                base,env,obs=restore(a['prefix'])
                try:
                    assert fingerprint(base)==a['initial']
                    for n,action in enumerate(a['actions']):
                        state=senses(base);assert np.array_equal(encode(obs,state.room,goal['room'],goal['x'],goal['y']),a['x'][n])
                        obs,_,_,_,_=env.step(np.asarray(action))
                    state=senses(base);assert reached(state.room,state.x,state.y,goal) and fingerprint(base)==a['final']
                    p=target/f'goal-{index}-path-{j}.npz';np.savez_compressed(p,x=a.pop('x'),y=np.asarray(a['actions'],dtype=np.int64))
                    a['file']=p.name;a['sha256']=sha256(p);a['goal']=goal;a['replay_verified']=True
                    paths.append(a)
                finally:env.close()
            if not main:
                legs.append(dict(index=index,goal=goal,attempts=attempts,unresolved=True,accepted=len(accepted)));break
            best=min(main,key=lambda a:len(a['actions']));prefix=entry+best['actions']
            legs.append(dict(index=index,goal=goal,attempts=attempts,accepted=len(accepted),selected_steps=len(best['actions'])))
        report=dict(route_id=route['id'],start=start,legs=legs,paths=paths,source_run=str(run_path),source_result_sha256=sha256(run_path/'result.json'),
            policy_sha256=sha256(checkpoint),full_repaired_prefix=prefix,completed_goals=sum(not x.get('unresolved',False) for x in legs),replay_verified=True)
        (target/'manifest.json').write_text(json.dumps(report,indent=2))
    return dict(route_id=route['id'],start=start,goals=report['completed_goals'],paths=len(paths))


def collect(out):
    out=Path(out);plan=read(out/'plan.json');summary=read(out/'baseline/summary.json');data=out/'data';data.mkdir(exist_ok=False)
    shutil.copy2(__file__,out/'collector_source.py')
    with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
        results=[]
        for r in pool.map(collect_case,[(r['run_path'],plan['parent'],str(data)) for r in summary['routes']]):
            results.append(r);print(json.dumps(r),flush=True)
    (out/'collection.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','collect','evaluate']);p.add_argument('--out',type=Path,required=True);p.add_argument('--checkpoint',type=Path);p.add_argument('--label',default='candidate')
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.out)
    elif a.mode=='collect':collect(a.out)
    else:evaluate(a.out,a.checkpoint,a.label)

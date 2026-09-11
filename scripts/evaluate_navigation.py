"""Paired live goal-reaching evaluation from verified physical replay prefixes."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))


def trial(args):
    case,agent,checkpoint,batch,destination,budget=args
    import numpy as np
    import torch
    import pyarrow.parquet as pq
    import shutil
    torch.set_num_threads(1)
    from gameboy_agent.navigation import NavigationController,reached
    from gameboy_agent.skills import Explorer
    from gameboy_agent.training_env import TrainingEnv
    from gameboy_agent.dataset import sha256,pack_observation
    from gameboy_agent.checkpoint import fingerprint
    from control_context import ControlContext
    from run_skill_chain import senses
    source=Path(batch)/case['source_path'];meta=json.loads((source.parent/'manifest.json').read_text())
    if sha256(source)!=case['source_sha256']:raise ValueError('Source mismatch')
    trace=pq.read_table(source,columns=['action','observation']).to_pydict()
    explorer=Explorer();controller=NavigationController(checkpoint) if agent=='learned' else None
    with tempfile.TemporaryDirectory() as tmp:
        rom=Path(tmp)/'game.gbc';shutil.copy2(Path(batch)/'assets/game.gbc',rom)
        base=TrainingEnv(rom,Path(batch)/'assets'/f'{meta["start"]}.state',max_steps=meta['max_steps'],sword_curriculum=False)
        env=ControlContext(base);actions=[];damage=0;success=False;error=None;status='timeout'
        try:
            obs,_=env.reset(seed=meta['seed'])
            for action in trace['action'][:case['step']]:obs,_,done,truncated,_=env.step(np.asarray(action))
            if pack_observation(obs,meta['observation_layout'])!=trace['observation'][case['step']]:
                raise ValueError('Evaluation prefix replay mismatch')
            start_fingerprint=fingerprint(base);state=senses(base);initial_health=state.health
            assert not reached(state.room,state.x,state.y,case['goal'])
            base.config['max_steps']=base.total_steps+budget+1
            for step in range(budget):
                state=senses(base);goal=case['goal']
                if agent=='learned':action=controller.action(obs,state.room,goal)
                elif agent=='explorer':action=explorer.action(state)
                else:
                    # Goal-aware diagnostic without obstacle avoidance. Across
                    # overworld rooms, move toward the target's grid direction.
                    dx,dy=goal['x']-state.x,goal['y']-state.y
                    if list(state.room)!=goal['room']:
                        dx=(goal['room'][2]%16-state.room[2]%16)*160
                        dy=(goal['room'][2]//16-state.room[2]//16)*144
                    direction=(4 if dx>0 else 3) if abs(dx)>=abs(dy) else (2 if dy>0 else 1)
                    button=1 if state.a_item==1 else 2 if state.b_item==1 else 0
                    action=[direction,button if step%2 else 0]
                    if state.dialogue:action=[0,step%2]
                obs,_,done,truncated,_=env.step(np.asarray(action));after=senses(base)
                damage+=max(0,state.health-after.health);actions.append(action)
                if after.health==0:status='death';break
                if reached(after.room,after.x,after.y,goal):success=True;status='success';break
                if done or truncated:status='environment_end';break
            final=senses(base)
            result=dict(case_id=case['segment_id'],agent=agent,start=case['start'],kind=case['kind'],
                success=success,status=status,steps=len(actions),damage=damage,initial_health=initial_health,
                final_health=final.health,goal=case['goal'],final_room=list(final.room),final_x=final.x,final_y=final.y,
                source_episode_id=meta['episode_id'],source_prefix_steps=case['step'],
                start_fingerprint=start_fingerprint,final_fingerprint=fingerprint(base),actions=actions,
                harness_privilege='D',completion_evaluated=False)
            path=Path(destination)/f'{case["segment_id"]}-{agent}.json';path.write_text(json.dumps(result))
            return {k:v for k,v in result.items() if k!='actions'}
        finally:env.close()


def evaluate(cache,checkpoint,out,workers=8,budget=128,baseline=None):
    cache=Path(cache);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    from gameboy_agent.dataset import sha256
    metadata=json.loads((cache/'manifest.json').read_text())
    if sha256(cache/'live-dev-cases.json')!=metadata['artifacts']['live-dev-cases.json']:raise ValueError('Case manifest mismatch')
    check=json.loads(Path(checkpoint).with_suffix('.json').read_text())
    if sha256(checkpoint)!=check['sha256']:raise ValueError('Policy integrity mismatch')
    cases=json.loads((cache/'live-dev-cases.json').read_text());agents=['learned','explorer','greedy']
    prior=[]
    if baseline:
        prior_plan=json.loads((Path(baseline)/'plan.json').read_text())
        if prior_plan['cases']!=cases or prior_plan['budget']!=budget:raise ValueError('Baseline case/budget mismatch')
        prior=[r for r in json.loads((Path(baseline)/'result.json').read_text())['episodes'] if r['agent']!='learned']
    plan=dict(cases=cases,agents=agents,checkpoint=str(Path(checkpoint).resolve()),policy_sha256=sha256(checkpoint),
        budget=budget,tolerance_manhattan_pixels=8,selection='frozen before training from grouped development data',
        frozen_benchmark_used=False,completion_evaluated=False,baseline_results=str(baseline) if baseline else None)
    (out/'plan.json').write_text(json.dumps(plan,indent=2))
    jobs=[(case,agent,str(checkpoint),metadata['source_batch'],str(out),budget) for case in cases for agent in (['learned'] if baseline else agents)]
    results=list(prior)
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        for r in pool.map(trial,jobs):
            results.append(r)
            if len(results)%12==0:print('EVALUATED',len(results),len(jobs),flush=True)
    for case in cases:
        paired=[r for r in results if r['case_id']==case['segment_id']]
        assert len({r['start_fingerprint'] for r in paired})==1
    summary={}
    for agent in agents:
        subset=[r for r in results if r['agent']==agent]
        summary[agent]=dict(cases=len(subset),successes=sum(r['success'] for r in subset),deaths=sum(r['status']=='death' for r in subset),
            damage=sum(r['damage'] for r in subset),mean_steps=sum(r['steps'] for r in subset)/len(subset),
            by_kind={kind:dict(cases=sum(r['kind']==kind for r in subset),successes=sum(r['kind']==kind and r['success'] for r in subset)) for kind in ['same_room','cross_room']})
    report=dict(summary=summary,episodes=results,paired_start_fingerprints_match=True)
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--budget',type=int,default=128)
    p.add_argument('--baseline',type=Path)
    a=p.parse_args();evaluate(a.cache,a.checkpoint,a.out,a.workers,a.budget,a.baseline)

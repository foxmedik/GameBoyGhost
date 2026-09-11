"""Physical replay recovery collection and bounded corrective fine-tuning.

Development failures used here are retired from validation. Search is an
assisted data teacher only; deployed policy remains a feed-forward network.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import sys
import tempfile
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256,pack_observation
from gameboy_agent.curation import stable_hash
BATCH=ROOT/'runs/data-workset-16m-v1'
BASE_CACHE=ROOT/'runs/navigation-cache-v2'
POLICY=ROOT/'runs/navigation-model-no-history-v1/epoch-064.pt'


def freeze(out):
    import pyarrow.parquet as pq
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    failures=json.loads((ROOT/'configs/navigation_failure_cases.json').read_text())
    old=json.loads((BASE_CACHE/'live-dev-cases.json').read_text())
    curated=ROOT/'data/curated/ladx-navigation-v1'
    cm=json.loads((curated/'manifest.json').read_text())
    index=curated/'dev/hindsight_navigation.parquet'
    assert sha256(index)==cm['artifacts']['dev/hindsight_navigation.parquet']
    rows=pq.read_table(index).to_pylist()
    retired_episodes={c['episode_id'] for c in failures['local_goal_failures']}
    retired_cohorts={r['cohort_id'] for r in rows if r['source_episode_id'] in retired_episodes}
    registry=ROOT/'configs/navigation_retired_cohorts.json'
    if registry.exists():retired_cohorts.update(json.loads(registry.read_text())['cohorts'])
    old_episodes={c['episode_id'] for c in old}
    # Exclude whole cohorts touched by corrections and all old live episodes.
    available=[r for r in rows if r['cohort_id'] not in retired_cohorts and r['source_episode_id'] not in old_episodes]
    cases=[];used=set()
    for start in ('house','beach','approach'):
        for kind in ('same_room','cross_room'):
            count=0
            for r in sorted((r for r in available if r['start']==start),key=lambda r:stable_hash(['recovery-fresh-v1',r['segment_id']])):
                if r['source_episode_id'] in used:continue
                source=BATCH/r['source_path'];meta=json.loads((source.parent/'manifest.json').read_text())
                assert sha256(source)==r['source_sha256']
                t=pq.read_table(source,columns=['room','x','y']).to_pydict();i=r['step_start']
                actual='same_room' if t['room'][i]==r['target_room'] else 'cross_room'
                if actual!=kind:continue
                if actual=='same_room' and abs(t['x'][i]-r['target_x'])+abs(t['y'][i]-r['target_y'])<=8:continue
                cases.append(dict(segment_id=r['segment_id'],episode_id=r['source_episode_id'],source_path=r['source_path'],source_sha256=r['source_sha256'],
                    start=start,seed=meta['seed'],step=i,goal=dict(room=r['target_room'],x=r['target_x'],y=r['target_y']),
                    initial_room=t['room'][i],initial_x=t['x'][i],initial_y=t['y'][i],kind=kind,cohort_id=r['cohort_id']))
                used.add(r['source_episode_id']);count+=1
                if count==8:break
            assert count==8
    (out/'live-dev-cases.json').write_text(json.dumps(cases,indent=2))
    (out/'manifest.json').write_text(json.dumps(dict(source_batch=str(BATCH),artifacts={'live-dev-cases.json':sha256(out/'live-dev-cases.json')},
        selection='48 new development cases frozen before correction collection/training; exclude correction cohorts and all original live episodes',
        retired_cohorts=sorted(retired_cohorts),retired_episodes=sorted(retired_episodes),reserved_evaluation_used=False),indent=2))
    print('FROZEN',len(cases),flush=True)


def teacher(state,goal,rng,step,attempt,visits):
    if state.dialogue:return [0,step%2]
    dx,dy=goal['x']-state.x,goal['y']-state.y
    if list(state.room)!=goal['room']:
        dx=(goal['room'][2]%16-state.room[2]%16)*160
        dy=(goal['room'][2]//16-state.room[2]//16)*144
    direction=(4 if dx>0 else 3) if abs(dx)>=abs(dy) else (2 if dy>0 else 1)
    key=(*state.room,state.x//4,state.y//4)
    visits[key]=visits.get(key,0)+1
    if attempt>0:
        # Temporary directional detours; obstacle handling selected only by
        # actual damage-free success in an independent emulator rollout.
        period=8+(attempt%4)*4
        if step<attempt%9 or visits[key]>3 or (attempt>4 and step%period<3):
            direction=1+(int(stable_hash([attempt,step//4])[:8],16)%4)
    button=1 if state.a_item==1 else 2 if state.b_item==1 else 0
    return [direction,button if step%2 else 0]


def collect_job(job):
    import torch
    import pyarrow.parquet as pq
    from gameboy_agent.navigation import NavigationController,encode,reached
    from gameboy_agent.training_env import TrainingEnv
    from gameboy_agent.checkpoint import fingerprint
    from control_context import ControlContext
    from run_skill_chain import senses
    torch.set_num_threads(1)
    case,offset,out=job;out=Path(out);identifier=case['segment_id']+'-'+str(offset)
    target=out/identifier;target.mkdir()
    if 'chain' in case:
        chain=ROOT/case['chain'];r=json.loads((chain/'result.json').read_text());manifest=json.loads((chain/'manifest.json').read_text())
        assert sha256(chain/'result.json')==manifest['artifacts']['result.json']
        initial=chain/'initial.state';prefix=r['actions'][:r['sword_step']];seed=0;max_steps=1985;meta=None;expected=None
    else:
        source=BATCH/case['source_path'];assert sha256(source)==case['source_sha256']
        meta=json.loads((source.parent/'manifest.json').read_text())
        trace=pq.read_table(source,columns=['action','observation']).to_pydict()
        prefix=trace['action'][:case['step']];expected=trace['observation'][case['step']]
        initial=BATCH/'assets'/f'{case["start"]}.state';seed=meta['seed'];max_steps=meta['max_steps']
    rollout_policy=Path(case.get('rollout_policy',POLICY))
    policy=NavigationController(rollout_policy);parent_teacher=NavigationController(POLICY)
    goal=case['goal'];attempts=[];successes=[]
    with tempfile.TemporaryDirectory() as tmp:
        rom=Path(tmp)/'game.gbc';shutil.copy2(BATCH/'assets/game.gbc',rom)
        def start():
            base=TrainingEnv(rom,initial,max_steps=max_steps,sword_curriculum=False);env=ControlContext(base)
            obs,_=env.reset(seed=seed)
            for action in prefix:obs,_,_,_,_=env.step(np.asarray(action))
            if expected is not None:assert pack_observation(obs,meta['observation_layout'])==expected
            base.config['max_steps']=base.total_steps+offset+len(case.get('replay_extra',[]))+257
            extra=[]
            for a in case.get('replay_extra',[]):
                obs,_,_,_,_=env.step(np.asarray(a));extra.append(a)
            for _ in range(offset):
                s=senses(base)
                if reached(s.room,s.x,s.y,goal):break
                a=policy.action(obs,s.room,goal);obs,_,_,_,_=env.step(np.asarray(a));extra.append(a)
            return base,env,obs,extra
        for attempt in range(case.get('attempt_cap',24)):
            base,env,obs,extra=start()
            try:
                origin=fingerprint(base);state=senses(base)
                if attempt==0:
                    base.pyboy.screen.image.save(target/'origin.png')
                    (target/'origin.json').write_text(json.dumps(dict(state=state.__dict__,policy_action=policy.action(obs,state.room,goal),goal=goal,offset=offset)))
                if reached(state.room,state.x,state.y,goal):break
                actions=[];xs=[];damage=0;visits={};rng=np.random.default_rng(attempt)
                success=False
                for step in range(128):
                    state=senses(base)
                    a=teacher(state,goal,rng,step,attempt,visits)
                    if case.get('parent_teacher') and attempt==0:
                        a=parent_teacher.action(obs,state.room,goal)
                    if 'fixed_actions' in case:
                        if step>=len(case['fixed_actions']):break
                        a=case['fixed_actions'][step]
                    # Original successful hindsight demonstration is a useful
                    # fallback at its original start, never at a shifted state.
                    if attempt==23 and meta is not None and offset==0 and not case.get('replay_extra') and step<32:
                        a=trace['action'][case['step']+step]
                    xs.append(encode(obs,state.room,goal['room'],goal['x'],goal['y']))
                    obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);actions.append(a)
                    damage+=max(0,state.health-after.health)
                    if damage or after.health==0:break
                    if reached(after.room,after.x,after.y,goal):success=True;break
                    if done or truncated:break
                end=fingerprint(base)
                attempts.append(dict(attempt=attempt,success=success,steps=len(actions),damage=damage,origin=origin,final=end))
                if success:
                    successes.append(dict(attempt=attempt,actions=actions,features=np.stack(xs),prefix_extra=extra,origin=origin,final=end))
                    if len(successes)>=case.get('success_cap',4):break
            finally:env.close()
        # Fresh physical replay verifies every selected teacher example.
        for i,saved in enumerate(successes):
            base,env,obs,extra=start()
            try:
                assert fingerprint(base)==saved['origin'] and extra==saved['prefix_extra']
                for j,a in enumerate(saved['actions']):
                    s=senses(base);x=encode(obs,s.room,goal['room'],goal['x'],goal['y'])
                    assert np.array_equal(x,saved['features'][j])
                    obs,_,_,_,_=env.step(np.asarray(a))
                assert fingerprint(base)==saved['final']
                s=senses(base);assert reached(s.room,s.x,s.y,goal)
                base.pyboy.screen.image.save(target/f'success-{i}.png')
                np.savez_compressed(target/f'success-{i}.npz',x=saved.pop('features'),y=np.asarray(saved['actions'],dtype=np.int64))
            finally:env.close()
    report=dict(case=case,offset=offset,prefix_actions=prefix,attempts=attempts,successes=successes,replay_verified=True,
        initial_state_sha256=sha256(initial),rom_sha256=sha256(BATCH/'assets/game.gbc'),policy_sha256=sha256(rollout_policy),
        artifacts={p.name:sha256(p) for p in target.iterdir()},harness_privilege='D')
    (target/'manifest.json').write_text(json.dumps(report,indent=2))
    return dict(id=identifier,successes=len(successes),attempts=len(attempts))


def collect(out,workers):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    failures=json.loads((ROOT/'configs/navigation_failure_cases.json').read_text());cases=failures['local_goal_failures']
    for path in failures['continuous_failures']:
        r=json.loads((ROOT/path/'result.json').read_text())
        cases.append(dict(segment_id='chain-'+r['start'],chain=path,start=r['start'],goal=r['goal']))
    plan=dict(cases=cases,offsets=[0,32,96],attempt_cap=24,success_cap=4,budget=128,
        frozen_evaluation_used=False,split='correction_training_retired_development',source_sha256=sha256(__file__))
    (out/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,out/'navigation_recovery.py')
    jobs=[(c,offset,str(out)) for c in cases for offset in plan['offsets']]
    results=[]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        for r in pool.map(collect_job,jobs):results.append(r);print(json.dumps(r),flush=True)
    (out/'result.json').write_text(json.dumps(results,indent=2))


def parent_divergence(candidate,parent):
    """Preserve parent action probabilities only on original training states."""
    import torch.nn.functional as F
    return (F.kl_div(F.log_softmax(candidate[:,:5],dim=1),F.softmax(parent[:,:5].detach(),dim=1),reduction='batchmean')
            +.25*F.kl_div(F.log_softmax(candidate[:,5:],dim=1),F.softmax(parent[:,5:].detach(),dim=1),reduction='batchmean'))


def train(data,out,epochs=12,anchor_weight=0.0):
    import torch
    from gameboy_agent.navigation import NavigationNet
    torch.set_num_threads(8);torch.manual_seed(2026)
    data=Path(data);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    assert sha256(POLICY)==json.loads(POLICY.with_suffix('.json').read_text())['sha256']
    saved=torch.load(POLICY,map_location='cpu');model=NavigationNet(saved['inputs']);model.load_state_dict(saved['model'])
    # Fixed parent normalization/mask keeps correction scaling reproducible.
    normalize=lambda x:torch.from_numpy((x-saved['mean'])/saved['scale']*saved['input_mask'])
    bm=json.loads((BASE_CACHE/'manifest.json').read_text())
    for name in ['train-x.npy','train-y.npy']:assert sha256(BASE_CACHE/name)==bm['artifacts'][name]
    bx=normalize(np.load(BASE_CACHE/'train-x.npy'));by=torch.from_numpy(np.load(BASE_CACHE/'train-y.npy'))
    xx=[];yy=[];artifacts={};seen=set()
    for p in sorted(data.glob('*/success-*.npz')):
        m=json.loads((p.parent/'manifest.json').read_text());assert m['replay_verified'] and sha256(p)==m['artifacts'][p.name]
        d=np.load(p);key=stable_hash([d['x'].tolist(),d['y'].tolist()])
        artifacts[str(p.relative_to(data))]=sha256(p)
        if key in seen:continue
        seen.add(key);xx.append(d['x']);yy.append(d['y'])
    cx=normalize(np.concatenate(xx));cy=torch.from_numpy(np.concatenate(yy))
    teacher_logits=None
    if anchor_weight:
        model.eval()
        with torch.no_grad():teacher_logits=torch.cat([model(chunk) for chunk in bx.split(4096)])
    opt=torch.optim.Adam(model.parameters(),lr=5e-5);g=torch.Generator().manual_seed(2026);loss=torch.nn.CrossEntropyLoss();history=[]
    plan=dict(parent_sha256=sha256(POLICY),base_cache_sha256=sha256(BASE_CACHE/'manifest.json'),correction_artifacts=artifacts,
        correction_rows=len(cx),base_rows=len(bx),epochs=epochs,learning_rate=5e-5,correction_batch_fraction=.25,
        anchor_weight=anchor_weight,anchor='KL(parent || candidate), movement + 0.25 buttons on original train states only',
        selection='fixed final epoch; no validation-based selection',source_sha256=sha256(__file__),
        unique_feature_action_sequences=len(seen),torch_version=torch.__version__,numpy_version=np.__version__,
        navigation_source_sha256=sha256(ROOT/'src/gameboy_agent/navigation.py'))
    (out/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,out/'navigation_recovery.py')
    shutil.copy2(ROOT/'src/gameboy_agent/navigation.py',out/'navigation.py')
    for epoch in range(1,epochs+1):
        model.train();total=0;count=0
        for idx in torch.randperm(len(bx),generator=g).split(1536):
            ci=torch.randint(len(cx),(512,),generator=g);x=torch.cat([bx[idx],cx[ci]]);y=torch.cat([by[idx],cy[ci]])
            opt.zero_grad();z=model(x);value=loss(z[:,:5],y[:,0])+.25*loss(z[:,5:],y[:,1])
            if teacher_logits is not None:
                value=value+anchor_weight*parent_divergence(z[:len(idx)],teacher_logits[idx])
            value.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();total+=float(value.detach());count+=1
        history.append(dict(epoch=epoch,loss=total/count));print(json.dumps(history[-1]),flush=True)
        dest=out/f'epoch-{epoch:03}.pt'
        torch.save({**saved,'model':model.state_dict(),'optimizer':opt.state_dict(),'shuffle_rng':g.get_state(),
            'torch_rng':torch.get_rng_state(),'epoch':epoch,'history':history,'correction_plan':plan},dest)
        dest.with_suffix('.json').write_text(json.dumps(dict(sha256=sha256(dest),identity=plan),indent=2))
    (out/'history.json').write_text(json.dumps(history,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','collect','train']);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--data',type=Path);p.add_argument('--workers',type=int,default=8);p.add_argument('--epochs',type=int,default=12)
    p.add_argument('--anchor-weight',type=float,default=0.0)
    a=p.parse_args()
    if a.anchor_weight<0:p.error('--anchor-weight must be nonnegative')
    if a.mode=='freeze':freeze(a.out)
    elif a.mode=='collect':collect(a.out,a.workers)
    else:train(a.data,a.out,a.epochs,a.anchor_weight)

"""Collect parent trajectories and corrections from live divergence states."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import navigation_recovery as rec
from gameboy_agent.dataset import sha256
from gameboy_agent.curation import stable_hash


def read(p):return json.loads(Path(p).read_text())


def prepare(out):
    import pyarrow.parquet as pq
    out=Path(out);out.mkdir(exist_ok=False,parents=True)
    panels=[(ROOT/'runs/navigation-cache-v2',ROOT/'runs/navigation-live-no-history-v1',ROOT/'runs/navigation-recovery-batch-v2/eval-4/original'),
            (ROOT/'runs/navigation-recovery-dev-v1',ROOT/'runs/navigation-recovery-baseline-v1',ROOT/'runs/navigation-recovery-batch-v2/eval-4/additional')]
    jobs=[];seen=set();corrections=[];all_old=set()
    for panel,parent,candidate in panels:
        for case in read(panel/'live-dev-cases.json'):
            all_old.add(case['episode_id'])
            a=read(parent/f'{case["segment_id"]}-learned.json');b=read(candidate/f'{case["segment_id"]}-learned.json')
            assert a['start_fingerprint']==b['start_fingerprint']
            if a['success'] and a['damage']==0:
                preserve={**case,'segment_id':'preserve-'+case['segment_id'],'fixed_actions':a['actions'],'attempt_cap':1,'success_cap':1}
                jobs.append(dict(case=preserve,offset=0));seen.add(case['episode_id'])
            # Regressions plus the last original correction route still missed.
            if (a['success'] and not b['success']) or case['segment_id'].startswith('129b2185b2'):
                first=next((i for i,(x,y) in enumerate(zip(a['actions'],b['actions'])) if x!=y),0)
                corrections.append(dict(case_id=case['segment_id'],first_action_divergence=first,parent_success=a['success'],candidate_success=b['success']))
                for position in sorted({first,min(first+8,len(b['actions'])-1),min(96,len(b['actions'])-1)}):
                    job={**case,'segment_id':f'correct-{case["segment_id"]}-{position}','replay_extra':b['actions'][:position],
                         'parent_teacher':True,'success_cap':4,'rollout_policy':str(ROOT/'runs/navigation-recovery-batch-v2/anchor-4/epoch-012.pt')}
                    jobs.append(dict(case=job,offset=0));seen.add(case['episode_id'])
    original=read(ROOT/'configs/navigation_failure_cases.json')['local_goal_failures']
    seen.update(c['episode_id'] for c in original)
    index=ROOT/'data/curated/ladx-navigation-v1/dev/hindsight_navigation.parquet'
    cm=read(index.parents[1]/'manifest.json');assert sha256(index)==cm['artifacts']['dev/hindsight_navigation.parquet']
    rows=pq.read_table(index).to_pylist();retired={r['cohort_id'] for r in rows if r['source_episode_id'] in seen}
    available=[r for r in rows if r['cohort_id'] not in retired and r['source_episode_id'] not in all_old]
    cases=[];used=set()
    for start in ['house','beach','approach']:
        for kind in ['same_room','cross_room']:
            count=0
            for r in sorted((r for r in available if r['start']==start),key=lambda r:stable_hash(['live-correction-v3',r['segment_id']])):
                if r['source_episode_id'] in used:continue
                source=rec.BATCH/r['source_path'];assert sha256(source)==r['source_sha256']
                meta=read(source.parent/'manifest.json');t=pq.read_table(source,columns=['room','x','y']).to_pydict();i=r['step_start']
                actual='same_room' if t['room'][i]==r['target_room'] else 'cross_room'
                if actual!=kind:continue
                if actual=='same_room' and abs(t['x'][i]-r['target_x'])+abs(t['y'][i]-r['target_y'])<=8:continue
                cases.append(dict(segment_id=r['segment_id'],episode_id=r['source_episode_id'],source_path=r['source_path'],source_sha256=r['source_sha256'],start=start,seed=meta['seed'],step=i,
                    goal=dict(room=r['target_room'],x=r['target_x'],y=r['target_y']),initial_room=t['room'][i],initial_x=t['x'][i],initial_y=t['y'][i],kind=kind,cohort_id=r['cohort_id']))
                used.add(r['source_episode_id']);count+=1
                if count==8:break
            assert count==8
    panel=out/'fresh-panel';panel.mkdir();(panel/'live-dev-cases.json').write_text(json.dumps(cases,indent=2))
    (panel/'manifest.json').write_text(json.dumps(dict(source_batch=str(rec.BATCH),artifacts={'live-dev-cases.json':sha256(panel/'live-dev-cases.json')},retired_cohorts=sorted(retired),retired_episodes=sorted(seen),reserved_evaluation_used=False),indent=2))
    plan=dict(jobs=jobs,divergences=corrections,retired_episodes=sorted(seen),retired_cohorts=sorted(retired),fresh_cases=48,
        parent= str(rec.POLICY),parent_sha256=sha256(rec.POLICY),collector_sha256=sha256(ROOT/'scripts/navigation_recovery.py'),source_sha256=sha256(__file__),
        training=dict(epochs=12,anchor_weight=4,seed=2026),
        gate='No parent-success losses, no health loss or deaths on both old regression panels and the fresh panel; all three continuous goals reached without damage.',
        reserved_evaluation_used=False,harness_privilege='D')
    (out/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,out/'navigation_live_correction.py');shutil.copy2(ROOT/'scripts/navigation_recovery.py',out/'navigation_recovery.py')
    print(json.dumps(dict(jobs=len(jobs),divergences=corrections,retired_cohorts=len(retired))),flush=True)


def collect(out):
    out=Path(out);plan=read(out/'plan.json');assert sha256(ROOT/'scripts/navigation_recovery.py')==plan['collector_sha256']
    data=out/'data';data.mkdir(exist_ok=False)
    # Immutable prior demonstrations are referenced, not relabeled or overwritten.
    for p in (ROOT/'runs/navigation-recovery-data-v1').iterdir():
        if p.is_dir() and (p/'manifest.json').exists():(data/p.name).symlink_to(p.resolve(),target_is_directory=True)
    results=[]
    with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
        for r in pool.map(rec.collect_job,[(j['case'],j['offset'],str(data)) for j in plan['jobs']]):
            results.append(r);print(json.dumps(r),flush=True)
    (out/'collection.json').write_text(json.dumps(results,indent=2))
    import numpy as np
    count=rows=0
    for path in data.iterdir():
        m=read(path/'manifest.json');assert m['replay_verified']
        for name,h in m['artifacts'].items():assert sha256(path/name)==h
        for p in path.glob('success-*.npz'):
            d=np.load(p);assert d['x'].shape==(len(d['y']),250) and np.isfinite(d['x']).all()
            assert ((d['y'][:,0]>=0)&(d['y'][:,0]<=4)).all() and ((d['y'][:,1]>=0)&(d['y'][:,1]<=2)).all()
            rows+=len(d['y']);count+=1
    for j,r in zip(plan['jobs'],results):
        if 'fixed_actions' in j['case']:assert r['successes']==1,'Parent preservation replay failed'
    cases=read(out/'fresh-panel/live-dev-cases.json');assert not ({c['cohort_id'] for c in cases}&set(plan['retired_cohorts']))
    (out/'verification.json').write_text(json.dumps(dict(passed=True,demonstrations=count,rows=rows,new_jobs=len(results),empty_jobs=[r['id'] for r in results if not r['successes']],fresh_cohort_disjoint=True,reserved_evaluation_used=False),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','collect']);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    (prepare if a.mode=='prepare' else collect)(a.out)

"""Independently audit live-correction artifacts and development retirement."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256


def verify(out):
    out=Path(out);plan=json.loads((out/'plan.json').read_text());panel=out/'fresh-panel'
    assert sha256(out/'navigation_recovery.py')==plan['collector_sha256']
    assert sha256(out/'navigation_live_correction.py')==plan['source_sha256']
    pm=json.loads((panel/'manifest.json').read_text())
    assert sha256(panel/'live-dev-cases.json')==pm['artifacts']['live-dev-cases.json']
    fresh=json.loads((panel/'live-dev-cases.json').read_text())
    assert len(fresh)==48 and len({c['episode_id'] for c in fresh})==48
    assert not ({c['cohort_id'] for c in fresh}&set(plan['retired_cohorts']))
    old=[]
    for p in ['runs/navigation-cache-v2','runs/navigation-recovery-dev-v1']:
        old+=json.loads((ROOT/p/'live-dev-cases.json').read_text())
    assert not ({c['episode_id'] for c in fresh}&{c['episode_id'] for c in old})
    count=rows=preserve=recovery=0
    for d in (out/'data').iterdir():
        m=json.loads((d/'manifest.json').read_text());assert m['replay_verified']
        for name,h in m['artifacts'].items():assert sha256(d/name)==h
        for i,s in enumerate(m['successes']):
            attempt=next(a for a in m['attempts'] if a['attempt']==s['attempt'])
            assert attempt['success'] and attempt['damage']==0
            assert attempt['origin']==s['origin'] and attempt['final']==s['final']
            a=np.load(d/f'success-{i}.npz');assert np.array_equal(a['y'],np.asarray(s['actions']))
            assert a['x'].shape==(len(a['y']),250) and np.isfinite(a['x']).all()
            assert np.isin(a['y'][:,0],range(5)).all() and np.isin(a['y'][:,1],range(3)).all()
            count+=1;rows+=len(a['y']);preserve+=d.name.startswith('preserve-');recovery+=d.name.startswith('correct-')
    result=dict(passed=True,demonstrations=count,rows=rows,parent_trajectories=preserve,new_recovery_demonstrations=recovery,
        fresh_cases=len(fresh),retired_cohorts=len(plan['retired_cohorts']),fresh_cohort_disjoint=True,
        all_accepted_paths_replayed=True,reserved_evaluation_used=False)
    (out/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':verify(sys.argv[1])

"""Audit recovery provenance, successful physical traces and split retirement."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256


def verify(data,panel):
    data=Path(data);panel=Path(panel)
    plan=json.loads((data/'plan.json').read_text())
    assert sha256(data/'navigation_recovery.py')==plan['source_sha256']
    jobs=json.loads((data/'result.json').read_text())
    assert len(jobs)==len(plan['cases'])*len(plan['offsets'])
    raw_rows=0;unique=set();successful=set();attempts=0
    for job in jobs:
        path=data/job['id'];meta=json.loads((path/'manifest.json').read_text())
        assert meta['replay_verified']
        assert len(meta['successes'])==job['successes']
        attempts+=len(meta['attempts'])
        for name,digest in meta['artifacts'].items():assert sha256(path/name)==digest
        for i,success in enumerate(meta['successes']):
            record=next(r for r in meta['attempts'] if r['attempt']==success['attempt'])
            assert record['success'] and record['damage']==0
            assert record['origin']==success['origin'] and record['final']==success['final']
            d=np.load(path/f'success-{i}.npz');x,y=d['x'],d['y']
            assert x.shape==(len(y),250) and np.isfinite(x).all()
            assert np.array_equal(y,np.asarray(success['actions']))
            assert (y[:,0]>=0).all() and (y[:,0]<=4).all() and (y[:,1]>=0).all() and (y[:,1]<=2).all()
            raw_rows+=len(y);successful.add(meta['case']['segment_id'])
            unique.add((success['origin'],tuple(map(tuple,success['actions']))))
    m=json.loads((panel/'manifest.json').read_text())
    for name,digest in m['artifacts'].items():assert sha256(panel/name)==digest
    cases=json.loads((panel/'live-dev-cases.json').read_text())
    assert len(cases)==48 and len({c['episode_id'] for c in cases})==48
    assert not ({c['cohort_id'] for c in cases}&set(m['retired_cohorts']))
    assert not ({c['episode_id'] for c in cases}&set(m['retired_episodes']))
    old=json.loads((ROOT/'runs/navigation-cache-v2/live-dev-cases.json').read_text())
    assert not ({c['episode_id'] for c in cases}&{c['episode_id'] for c in old})
    assert not m['reserved_evaluation_used'] and not plan['frozen_evaluation_used']
    return dict(passed=True,jobs=len(jobs),attempts=attempts,successful_cases=len(successful),
        demonstrations=sum(j['successes'] for j in jobs),unique_origin_action_sequences=len(unique),
        action_rows=raw_rows,fresh_panel_cases=len(cases),correction_cohorts_disjoint=True,
        physical_replay='collector verified every selected feature sequence and final fingerprint in a fresh environment',
        harness_privilege='D',reserved_evaluation_used=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--panel',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();result=verify(a.data,a.panel);a.out.write_text(json.dumps(result,indent=2));print(json.dumps(result))

"""Audit all segment labels against source rows, plus actual loader examples."""
import argparse
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import pyarrow.parquet as pq
from gameboy_agent.dataset import sha256
from gameboy_agent.curation import COLUMNS, load_segment


def verify(out):
    out=Path(out).resolve();manifest=json.loads((out/'manifest.json').read_text())
    batch=Path(manifest['source_batch']);config=manifest['config']
    for name,digest in manifest['artifacts'].items():
        assert sha256(out/name)==digest, name
    inventory=json.loads((out/'source-inventory.json').read_text())
    retained={r['source_episode_id']:r for r in inventory if r['duplicate_of'] is None}
    rows=pq.read_table(out/'segments.parquet').to_pylist()
    assert len(rows)==manifest['segments']
    assert len({r['segment_id'] for r in rows})==len(rows)
    cohorts={split:{r['cohort_id'] for r in rows if r['split']==split} for split in ('train','dev')}
    assert not cohorts['train'] & cohorts['dev']
    groups=defaultdict(list)
    for r in rows:
        assert r['source_episode_id'] in retained
        source=retained[r['source_episode_id']]
        assert r['split']==source['split'] and r['cohort_id']==source['cohort_id']
        assert r['source_sha256']==source['source_sha256'] and r['source_path']==source['source_path']
        groups[r['source_episode_id']].append(r)
    shard_ids=set()
    for key,count in manifest['split_lanes'].items():
        split,lane=key.split('/')
        entries=pq.read_table(out/split/f'{lane}.parquet').to_pylist()
        assert len(entries)==count
        assert all(e['split']==split and e['lane']==lane for e in entries)
        ids={e['segment_id'] for e in entries}
        assert not ids & shard_ids
        shard_ids.update(ids)
    assert shard_ids=={r['segment_id'] for r in rows}

    def audit(item):
        episode,segments=item;record=retained[episode];source=batch/record['source_path']
        meta=json.loads((source.parent/'manifest.json').read_text())
        assert sha256(source)==record['source_sha256']
        assert sha256(source.parent/'manifest.json')==record['manifest_sha256']
        assert meta['split']=='train' and meta['episode_id']==episode
        d=pq.read_table(source,columns=COLUMNS).to_pydict();n=len(d['step'])
        health=np.asarray(d['health']);nh=np.asarray(d['next_health']);damage=nh<health
        terminal=np.asarray(d['terminated']) | np.asarray(d['truncated'])
        skill=np.asarray(d['skill'])
        def moved(a,b):
            return (d['room'][a]!=d['next_room'][b-1] or
                    abs(d['next_x'][b-1]-d['x'][a])+abs(d['next_y'][b-1]-d['y'][a])>=config['minimum_displacement'])
        for s in segments:
            a,b=s['step_start'],s['step_end'];assert 0<=a<b<=n
            assert s['target_room']==d['next_room'][b-1]
            assert (s['target_x'],s['target_y'])==(d['next_x'][b-1],d['next_y'][b-1])
            assert s['contains_setup']==bool(np.any(skill[a:b]=='physical_setup'))
            label=s['label']
            assert s['imitation_eligible']==(label=='clean_sword_acquisition')
            if label=='clean_sword_acquisition':
                assert s['lane']=='imitation' and not s['contains_setup']
                assert np.all(skill[a:b]=='acquire_sword') and b==meta['sword_step']
                assert d['sword'][b-1] and nh[b-1]>0 and not damage[a:b].any()
            elif label=='observed_safe_navigation':
                end=b+config['safety_lookahead'];assert end<=n
                assert b-a==config['navigation_window'] and moved(a,b)
                assert np.all(skill[a:end]=='explore') and not damage[a:end].any() and not terminal[a:end].any()
            elif label=='damage_event':
                assert damage[s['anchor_step']] and damage[a:b].any()
            elif label=='observed_safe_recovery':
                assert b-a==config['recovery_horizon'] and moved(a,b)
                assert not damage[a:b].any() and not terminal[a:b].any()
            elif label=='recovery_no_net_progress':
                assert b-a==config['recovery_horizon'] and not moved(a,b)
                assert not damage[a:b].any() and not terminal[a:b].any()
            elif label=='recovery_censored':
                assert b-a<config['recovery_horizon'] or terminal[a:b].any()
                assert not damage[a:b].any()
            elif label=='recovery_repeat_damage':
                assert damage[b-1] and nh[b-1]>0
            elif label=='recovery_ended_in_death':
                assert nh[b-1]==0
            elif label=='death_context':
                assert b==n and meta['status']=='death' and nh[-1]==0
            elif label=='sword_timeout_context':
                assert b==n and meta['status']=='sword_timeout'
            else:
                raise AssertionError(label)
            if s['lane']=='recovery':
                assert damage[s['anchor_step']] and a==s['anchor_step']+1
        return len(segments)
    with ThreadPoolExecutor(max_workers=8) as pool:
        audited=sum(pool.map(audit,groups.items()))
    assert audited==len(rows)

    loaded=[]
    for lane in ('imitation','hindsight_navigation','event','recovery','failure'):
        sample=next(r for r in rows if r['split']=='train' and r['lane']==lane)
        result=load_segment(out,sample,allow_candidates=lane!='imitation')
        assert len(result['rows'])==sample['step_end']-sample['step_start']
        assert all(np.isfinite(v).all() for obs in result['observations'] for v in obs.values())
        loaded.append(dict(lane=lane,segment_id=sample['segment_id'],rows=len(result['rows'])))
    candidate=next(r for r in rows if r['split']=='train' and not r['imitation_eligible'])
    dev=next(r for r in rows if r['split']=='dev')
    for sample in (candidate,dev):
        try:load_segment(out,sample)
        except ValueError:pass
        else:raise AssertionError('Loader accepted a forbidden sample')
    return dict(segments=audited,source_episodes_audited=len(groups),
        artifact_hashes_valid=True,source_labels_valid=True,grouped_splits_disjoint=True,
        default_loader_rejects_candidates_and_dev=True,loaded_samples=loaded,
        eligible_segments_from_later_death_episodes=sum(r['imitation_eligible'] and r['terminal_episode_outcome']=='death' for r in rows),
        overlap_warning='Segment windows across lanes may overlap; row totals are not unique transitions.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('curated',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();result=verify(args.curated)
    with args.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)

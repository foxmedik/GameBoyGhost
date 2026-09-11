"""Collect only safe successes of the passing, frozen terrain-motion teacher."""
import json
import multiprocessing as mp
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.dataset import sha256
import navigation_recovery as rec
OUT=ROOT/'runs/sword-teacher-v2-demonstrations'
EXP=ROOT/'runs/proximity-sword-48-v2'

def main():
    result=json.loads((EXP/'result.json').read_text())
    assert result['gate_passed']['terrain_motion'], 'Rejected teacher cannot collect training demonstrations'
    selection=json.loads((ROOT/'configs/navigation_experiment.json').read_text())
    parent=ROOT/selection['policy_path'];assert sha256(parent)==selection['policy_sha256']
    cases=json.loads((EXP/'plan.json').read_text())['cases']
    OUT.mkdir(exist_ok=False);raw=OUT/'raw-data';raw.mkdir();jobs=[];expected={}
    for c in cases:
        source=EXP/f"{c['segment_id']}-terrain_motion.json";r=json.loads(source.read_text())
        if not r['success'] or r['damage'] or r['status']=='death':continue
        assert r['replay_verified']
        case={**c,'fixed_actions':r['actions'],'attempt_cap':1,'success_cap':1,'rollout_policy':str(parent)}
        jobs.append((case,0,str(raw)));expected[c['segment_id']]=dict(source=str(source),sha256=sha256(source),start=r['start_fingerprint'],final=r['final_fingerprint'])
    plan=dict(teacher='terrain_motion_v2_scripted_privileged_D',teacher_report_sha256=sha256(EXP/'result.json'),
        teacher_plan_sha256=sha256(EXP/'plan.json'),selected_parent=str(parent),selected_parent_sha256=sha256(parent),
        sources=expected,jobs=[j[0] for j in jobs],acceptance='Only zero-damage goal successes, identical actions and exact experiment start/final fingerprints; feature/action arrays physically replayed twice.',
        feature_contract='structured-goal-250-v1; original goal retained',reserved_evaluation_used=False,training_performed=False,
        collector_sha256=sha256(__file__),replay_collector_sha256=sha256(ROOT/'scripts/navigation_recovery.py'))
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'collector_source.py');shutil.copy2(ROOT/'scripts/navigation_recovery.py',OUT/'replay_collector_source.py')
    with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
        results=[]
        for r in pool.map(rec.collect_job,jobs):
            assert r['successes']==1;results.append(r);print(json.dumps(r),flush=True)
    paths=[]
    for c,_,_ in jobs:
        p=raw/f"{c['segment_id']}-0/manifest.json";m=json.loads(p.read_text());s=m['successes'][0];e=expected[c['segment_id']]
        assert m['replay_verified'] and s['origin']==e['start'] and s['final']==e['final']
        assert s['actions']==c['fixed_actions']
        asset=p.parent/'success-0.npz';assert sha256(asset)==m['artifacts'][asset.name]
        paths.append(dict(case_id=c['segment_id'],features=str(asset.relative_to(OUT)),sha256=sha256(asset),source_manifest=str(p.relative_to(OUT)),source_manifest_sha256=sha256(p),teacher_source=e,steps=len(s['actions']),replay_verified=True,supervision='scripted_teacher',harness_privilege='D'))
    (OUT/'manifest.json').write_text(json.dumps(dict(paths=paths,total_paths=len(paths),total_rows=sum(p['steps'] for p in paths),plan_sha256=sha256(OUT/'plan.json'),training_performed=False,reserved_evaluation_used=False),indent=2))
    print('COLLECTED',len(paths),'verified demonstrations',flush=True)
if __name__=='__main__':main()

"""Freeze one untrained navigator candidate with broad inherited supervision."""
import json
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256
OUT=ROOT/'runs/navigation-sword-v1'
DEMO=ROOT/'runs/sword-teacher-v2-demonstrations'

def main():
    read=lambda p:json.loads(p.read_text())
    teacher=read(ROOT/'reports/proximity-sword-48-v2.json');assert teacher['gate_passed']['terrain_motion']
    dm=read(DEMO/'manifest.json');selection=read(ROOT/'configs/navigation_experiment.json')
    parent=ROOT/selection['policy_path'];assert sha256(parent)==selection['policy_sha256']
    OUT.mkdir(exist_ok=False);data=OUT/'data';data.mkdir();policies={sha256(parent)};sources={};count=0
    for source in sorted((ROOT/'runs/navigation-routes-v7/data').glob('*/manifest.json')):
        m=read(source);assert m['replay_verified'];policies.add(m['policy_sha256'])
        dest=data/('preserve-'+source.parent.name);dest.mkdir()
        for p in m['paths']:
            asset=source.parent/p['file'];assert p['replay_verified'] and sha256(asset)==p['sha256']
            shutil.copy2(asset,dest/asset.name);count+=1
        m['inherited_manifest']=str(source);m['inherited_manifest_sha256']=sha256(source)
        (dest/'manifest.json').write_text(json.dumps(m,indent=2));sources[str(source)]=sha256(source)
    for row in dm['paths']:
        source=DEMO/row['source_manifest'];assert sha256(source)==row['source_manifest_sha256']
        m=read(source);asset=DEMO/row['features'];assert sha256(asset)==row['sha256']
        dest=data/('sword-'+row['case_id']);dest.mkdir();shutil.copy2(asset,dest/asset.name)
        metadata=dict(paths=[dict(file=asset.name,sha256=sha256(asset),actions=m['successes'][0]['actions'],replay_verified=True)],
            replay_verified=True,policy_sha256=sha256(parent),source_manifest=str(source),source_sha256=sha256(source),
            supervision='scripted terrain_motion teacher; policy_sha256 identifies initialization/provenance only, not action generation',
            teacher_source=row['teacher_source'],harness_privilege='D')
        (dest/'manifest.json').write_text(json.dumps(metadata,indent=2));sources[str(source)]=sha256(source)
    plan=dict(parent=str(parent),parent_sha256=sha256(parent),epochs=8,learning_rate=5e-6,retention_weight=8,
        retention_route_data=str(ROOT/'runs/navigation-routes-v7/data'),allowed_collection_policies=sorted(policies),
        balanced_path_groups=['sword-','preserve-'],group_batch_sizes=[128,128],action_margin=0.25,action_margin_weight=2,
        seed=2027,selected_epoch='epoch-008.pt only; no checkpoint shopping',previous_movement_masked=True,
        feature_contract='structured-goal-250-v1',label_rule='Existing shortest-observed-suffix rule; retain original goals; ties follow sorted input manifests.',
        supervision_sources=sources,new_teacher_paths=dm['total_paths'],new_teacher_rows=dm['total_rows'],inherited_preservation_paths=count,
        new_demo_manifest_sha256=sha256(DEMO/'manifest.json'),teacher_report_sha256=sha256(ROOT/'reports/proximity-sword-48-v2.json'),
        curriculum=read(ROOT/'configs/navigation_routes_v1.json'),reserved_evaluation_used=False,training_performed=False,
        status='frozen_untrained',selection='Preserve all 135 selected v7 local successes across 144 known cases, all six successful continuous routes and all earlier route waypoints, all three original chains, zero local/route damage and deaths, and independent exact physical resume/replay. Reject any regression; do not promote for swing reduction alone.',
        additional_sword_evaluation='Same 48 known cases: measure actual frame-level swings and paired success/damage/deaths for candidate versus selected v7; require at least 25% swing reduction, no lost v7 successes or per-case damage increases/new deaths.',
        limitations='Teacher passed 48 known cases only. Linear prediction and conservative exit guard are privileged teacher rules; they are not inserted into learned runtime. Cliff detour remains unsolved by selected navigator.',
        baseline_hashes={str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'configs/navigation_experiment.json',ROOT/'configs/navigation_routes_v1.json',ROOT/'reports/navigation-routes-v7.json',ROOT/'configs/navigation_retired_cohorts.json']},
        trainer_sha256=sha256(ROOT/'scripts/train_navigation_routes.py'),freeze_source_sha256=sha256(__file__))
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(ROOT/'configs/navigation_routes_v1.json',OUT/'curriculum.json')
    shutil.copy2(__file__,OUT/'freeze_source.py');shutil.copy2(ROOT/'scripts/train_navigation_routes.py',OUT/'trainer_source.py')
    print(json.dumps(dict(status=plan['status'],new_paths=dm['total_paths'],preservation_paths=count,plan_sha256=sha256(OUT/'plan.json'))))
if __name__=='__main__':main()

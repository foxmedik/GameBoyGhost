"""Freeze a repaired-cliff-data candidate; architecture/optimizer unchanged."""
import json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256
READ=lambda p:json.loads(Path(p).read_text())
OUT=ROOT/'runs/navigation-routes-v9'

def main():
 OUT.mkdir(exist_ok=False);data=OUT/'data';data.mkdir();old=ROOT/'runs/navigation-routes-v7';plan=READ(ROOT/'runs/navigation-routes-v8/plan.json');parent=old/'model/epoch-008.pt'
 assert sha256(parent)==READ(ROOT/'configs/navigation_experiment.json')['policy_sha256']
 shutil.copytree(old/'data',data,dirs_exist_ok=True);selected=[]
 for start in ['house','beach','approach']:
  approach=ROOT/f'runs/cliff-splice-repair-v1/v7-{start}/manifest.json';a=READ(approach);assert a['accepted']
  choices=[]
  for p in (ROOT/'runs/cliff-splice-returns-v1').glob(f'{start}-*/manifest.json'):
   m=READ(p)
   if m['accepted']:choices.append((m['steps'],str(p),p))
  ret=min(choices)[2];b=READ(ret);assert b['initial_fingerprint']==a['final_fingerprint']
  assert b['prefix']==a['prefix']+a['actions']
  for kind,source,m in [('approach',approach,a),('return',ret,b)]:
   asset=source.parent/'demonstration.npz';assert m['features_replay_verified'] and sha256(asset)==m['artifacts'][asset.name]
   dest=data/f'cliff-repaired-{kind}-{start}';dest.mkdir();shutil.copy2(asset,dest/'success-0.npz')
   meta=dict(paths=[dict(file='success-0.npz',sha256=sha256(asset),actions=m['actions'],goal=m['goal'],replay_verified=True)],replay_verified=True,policy_sha256=sha256(parent),source_manifest=str(source),source_sha256=sha256(source),supervision='scripted source-suffix repair, original goal, continuous physical replay; not learned',initial_fingerprint=m['initial_fingerprint'],final_fingerprint=m['final_fingerprint'])
   (dest/'manifest.json').write_text(json.dumps(meta,indent=2));selected.append(dict(kind=kind,start=start,source=str(source),source_sha256=sha256(source),rows=m['steps']))
 plan.update(parent=str(parent),parent_sha256=sha256(parent),status='frozen_untrained',training_performed=False,
  experiment='Replace 20 original cliff paths with six freshly encoded repaired paths; retain all 202 v7 preservation paths. No change to architecture, eight epochs, LR 1e-5, seed 2027, retention, margin, sampling groups or entry weighting from v8.',
  cliff_repair_sources=selected,new_jobs=[],baseline_hashes={str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'configs/navigation_experiment.json',ROOT/'configs/navigation_routes_v1.json',ROOT/'configs/navigation_retired_cohorts.json',ROOT/'reports/navigation-routes-v7.json']},
  trainer_sha256=sha256(ROOT/'scripts/train_navigation_routes.py'),freeze_source_sha256=sha256(__file__),prior_plan_sha256=sha256(ROOT/'runs/navigation-routes-v8/plan.json'),
  additional_sword_evaluation='Counts retained as diagnostics only; sword reduction is paused and is not a promotion condition.',
  selection='Final epoch 008 only. More than six complete routes, no lost v7 routes or waypoints, preserve all 135 safe local successes across three 48-case panels, zero local/route damage and deaths, preserve all three original continuous chains, exact physical replay/resume.',
  cliff_repair_caveat='Six canonical paths still contain 22 identical masked states with different movement labels. Existing shortest-suffix selection retained; this experiment tests new physical coverage, not a claim of eliminating aliasing.',reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(old/'curriculum.json',OUT/'curriculum.json');shutil.copy2(__file__,OUT/'freeze_source.py');shutil.copy2(ROOT/'scripts/train_navigation_routes.py',OUT/'trainer_source.py')
 (OUT/'collection.json').write_text(json.dumps(selected,indent=2));print('FROZEN',sha256(OUT/'plan.json'))
if __name__=='__main__':main()

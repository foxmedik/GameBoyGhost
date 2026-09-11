"""Apply the frozen route promotion gate and retain a compact experiment report."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256
from report_navigation_recovery import compare


def report(out):
    out=Path(out).resolve()
    read=lambda p:json.loads(p.read_text())
    before=read(out/'baseline/summary.json');after=read(out/'candidate/summary.json')
    panels={name:compare(ROOT/f'runs/navigation-focused-v4/eval-{name}/result.json',out/f'eval-{name}/result.json') for name in ('original','additional','fresh')}
    old={(r['route_id'],r['start']):r for r in before['routes']}
    route_lost=[]
    for r in after['routes']:
        b=old[(r['route_id'],r['start'])]
        parent=read(Path(b['run_path'])/'result.json');child=read(Path(r['run_path'])/'result.json')
        assert parent['route']==child['route'] and parent['budget']==child['budget']
        assert parent['sword_step']==child['sword_step'] and parent['actions'][:parent['sword_step']]==child['actions'][:child['sword_step']]
        if b['status']=='success' and r['status']!='success':route_lost.append([r['route_id'],r['start']])
    chains=[]
    for start in ('house','beach','approach'):
        r=read(out/f'chain-{start}/result.json')
        chains.append({k:r[k] for k in ('start','status','navigation_steps','navigation_damage')})
    full=read(out/'candidate/beach_return-house/result.json');resumed=read(out/'resumed/result.json');paused=read(out/'paused/result.json')
    fields=['actions','fingerprint','steps','sword_step','navigation_steps','damage','navigation_damage','status','final_state','progress']
    assert all(full[k]==resumed[k] for k in fields)
    assert paused['progress']['cursor']>=1
    plan=read(out/'plan.json')
    training=read(out/'training-plan.json');collection=read(out/'collection.json');checkpoint=out/'model/epoch-008.pt'
    gate=dict(more_complete_routes=after['complete']>before['complete'],no_route_success_lost=not route_lost,
        no_local_success_lost=all(not p['lost'] for p in panels.values()),
        zero_local_damage_and_deaths=all(not p['corrected_damage'] and not p['corrected_deaths'] for p in panels.values()),
        zero_route_damage_and_deaths=after['damage']==0 and after['deaths']==0,
        original_continuous_chains_preserved=all(r['status']=='success' and r['navigation_damage']==0 for r in chains))
    if plan.get('preservation_summary'):
        prior=read(Path(plan['preservation_summary']))
        successful={(r['route_id'],r['start']) for r in prior['routes'] if r['status']=='success'}
        now={(r['route_id'],r['start']) for r in after['routes'] if r['status']=='success' and r['navigation_damage']==0}
        gate['previous_candidate_routes_preserved']=successful<=now
    if plan.get('preservation_summaries'):
        successful={(r['route_id'],r['start']) for path in plan['preservation_summaries'] for r in read(Path(path))['routes'] if r['status']=='success' and r['navigation_damage']==0}
        now={(r['route_id'],r['start']) for r in after['routes'] if r['status']=='success' and r['navigation_damage']==0}
        gate['all_previous_candidate_routes_preserved']=successful<=now
    if plan.get('local_preservation_roots'):
        previous_local_losses={}
        for panel in ('original','additional','fresh'):
            required=set()
            for root in plan['local_preservation_roots']:
                required.update(r['case_id'] for r in read(Path(root)/f'eval-{panel}/result.json')['episodes'] if r['agent']=='learned' and r['success'] and r['damage']==0)
            safe={r['case_id'] for r in read(out/f'eval-{panel}/result.json')['episodes'] if r['agent']=='learned' and r['success'] and r['damage']==0}
            previous_local_losses[panel]=sorted(required-safe)
        gate['all_previous_safe_local_successes_preserved']=not any(previous_local_losses.values())
        (out/'previous-local-losses.json').write_text(json.dumps(previous_local_losses,indent=2))
    result=dict(retired_cohorts=plan.get('retired_cohorts',[]),schema='navigation-route-experiment-v1',parent_sha256=read(out/'plan.json')['parent_sha256'],candidate_path=str(checkpoint.relative_to(ROOT)),
        candidate_sha256=sha256(checkpoint),baseline=before,candidate=after,local_panels=panels,continuous=chains,
        collection=collection,training={k:training[k] for k in ('verified_paths','raw_route_rows','target_unique_states','conflicting_states','retention_rows','retention_demonstration_rows')},
        resume_verified=dict(exact_fields=fields,paused_step=paused['steps'],completed_goals_at_pause=paused['progress']['cursor']),
        gate=gate,promoted=all(gate.values()),harness_privilege='D',reserved_evaluation_used=False,completion_evaluated=False,
        interpretation='Routes are scripted development training regressions. Goals and starting states are known; these scores do not establish held-out generalization or game completion.')
    (out/'result.json').write_text(json.dumps(result,indent=2))
    # Portable public report: exclude local machine paths.
    for summary in (result['baseline'],result['candidate']):
        for r in summary['routes']:r['run_path']=str(Path(r['run_path']).relative_to(ROOT))
    (ROOT/'reports'/f'{out.name}.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('gate','promoted','local_panels','continuous')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);report(p.parse_args().out)

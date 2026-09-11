"""Paired comparison of correction, regression and additional development runs."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256


def read(path):return json.loads((ROOT/path).read_text())

def compare(parent,child,ids=None):
    before={r['case_id']:r for r in read(parent)['episodes'] if r['agent']=='learned'}
    after={r['case_id']:r for r in read(child)['episodes'] if r['agent']=='learned'}
    assert before.keys()==after.keys()
    keys=set(before) if ids is None else set(ids)
    assert keys<=before.keys()
    for key in keys:assert before[key]['start_fingerprint']==after[key]['start_fingerprint']
    return dict(cases=len(keys),parent_successes=sum(before[k]['success'] for k in keys),
        corrected_successes=sum(after[k]['success'] for k in keys),
        gained=sorted(k for k in keys if not before[k]['success'] and after[k]['success']),
        lost=sorted(k for k in keys if before[k]['success'] and not after[k]['success']),
        corrected_deaths=sum(after[k]['status']=='death' for k in keys),
        corrected_damage=sum(after[k]['damage'] for k in keys),paired_start_fingerprints_match=True)


def report():
    failures=read('configs/navigation_failure_cases.json');trained={c['segment_id'] for c in failures['local_goal_failures']}
    old=read('runs/navigation-cache-v2/live-dev-cases.json');untouched={c['segment_id'] for c in old}-trained
    parent='runs/navigation-live-no-history-v1/result.json';child='runs/navigation-recovery-regression-v1/result.json'
    result=dict(correction_training_cases=compare(parent,child,trained),
        original_other_regression_cases=compare(parent,child,untouched),
        original_full_regression=compare(parent,child),
        additional_development=compare('runs/navigation-recovery-baseline-v1/result.json','runs/navigation-recovery-live-v1/result.json'),
        additional_development_baselines=read('runs/navigation-recovery-baseline-v1/result.json')['summary'],continuous=[])
    for start in ('house','beach','approach'):
        before=read(f'runs/navigation-chain-{start}-v1/result.json');after=read(f'runs/navigation-recovery-chain-{start}-v1/result.json')
        assert before['goal']==after['goal'] and before['sword_step']==after['sword_step']
        assert before['actions'][:before['sword_step']]==after['actions'][:after['sword_step']]
        result['continuous'].append(dict(start=start,parent_status=before['status'],corrected_status=after['status'],
            parent_navigation_steps=before['navigation_steps'],corrected_navigation_steps=after['navigation_steps'],
            corrected_damage=after['navigation_damage'],sword_actions_unchanged=True))
    full=read('runs/navigation-recovery-chain-house-v1/result.json');resumed=read('runs/navigation-recovery-chain-resume-v1/result.json')
    fields=['actions','fingerprint','steps','sword_step','navigation_steps','damage','navigation_damage','status','final_state']
    assert all(full[k]==resumed[k] for k in fields)
    result['resume_verified']=dict(exact_fields=fields,steps=full['steps'])
    result.update(policy_sha256=sha256(ROOT/'runs/navigation-recovery-model-v1/epoch-012.pt'),
        data_verification=read('runs/navigation-recovery-verification-v1.json'),harness_privilege='D',
        frozen_evaluation_used=False,completion_evaluated=False,
        interpretation='Correction cases are training regressions. Additional 48 cases exclude correction cohorts and old live episodes but remain development evaluation.')
    dest=ROOT/'runs/navigation-recovery-comparison-v1.json';dest.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':report()

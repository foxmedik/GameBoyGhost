"""Evaluate the focused candidate against both the parent and v3."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
from report_navigation_recovery import compare
from gameboy_agent.dataset import sha256


def evaluate(out):
    out=Path(out).resolve();model=out/'model/epoch-008.pt';plan=json.loads((out/'plan.json').read_text())
    identity=json.loads(model.with_suffix('.json').read_text())
    assert sha256(model)==identity['sha256'] and identity['identity']['source_sha256']==plan['source_sha256']
    def run(args,log):
        with log.open('x') as f:subprocess.run([sys.executable,*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    panels=[('original',ROOT/'runs/navigation-cache-v2',ROOT/'runs/navigation-live-v2',ROOT/'runs/navigation-live-no-history-v1/result.json'),
            ('additional',ROOT/'runs/navigation-recovery-dev-v1',ROOT/'runs/navigation-recovery-baseline-v1',ROOT/'runs/navigation-recovery-baseline-v1/result.json'),
            ('fresh',ROOT/'runs/navigation-live-correction-v3/fresh-panel',ROOT/'runs/navigation-live-correction-v3/fresh-parent',ROOT/'runs/navigation-live-correction-v3/fresh-parent/result.json')]
    def panel(spec):
        name,cache,baseline,parent=spec;dest=out/f'eval-{name}'
        run(['scripts/evaluate_navigation.py','--cache',str(cache),'--checkpoint',str(model),'--out',str(dest),'--baseline',str(baseline),'--workers','8'],out/f'eval-{name}.log')
        result=compare(str(parent),str(dest/'result.json'));result['versus_v3']=compare(str(ROOT/f'runs/navigation-live-correction-v3/eval-{name}/result.json'),str(dest/'result.json'));result['summary']=json.loads((dest/'result.json').read_text())['summary']['learned']
        print(json.dumps(dict(panel=name,result=result)),flush=True);return name,result
    with ThreadPoolExecutor(max_workers=3) as pool:results=dict(pool.map(panel,panels))
    continuous=[]
    for start in ['house','beach','approach']:
        dest=out/f'chain-{start}'
        run(['scripts/run_navigation_chain.py','--checkpoint',str(model),'--goal','0','0','226','36','121','--start',start,'--out',str(dest)],out/f'chain-{start}.log')
        r=json.loads((dest/'result.json').read_text());parent=json.loads((ROOT/f'runs/navigation-chain-{start}-v1/result.json').read_text())
        assert r['sword_step']==parent['sword_step'] and r['actions'][:r['sword_step']]==parent['actions'][:parent['sword_step']]
        continuous.append({k:r[k] for k in ['start','status','steps','navigation_steps','navigation_damage']})
    eligible=all(not r['lost'] and not r['corrected_damage'] and not r['corrected_deaths'] and not r['versus_v3']['lost'] for r in results.values())
    eligible=eligible and all(r['status']=='success' and not r['navigation_damage'] for r in continuous)
    report=dict(panels=results,continuous=continuous,eligible=eligible,policy_sha256=sha256(model),
        interpretation='All three panels are known development/regression data; no new cohorts used in focused training. Require no lost successes relative to both original parent and v3.',
        reserved_evaluation_used=False,harness_privilege='D',completion_evaluated=False)
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();evaluate(a.out)

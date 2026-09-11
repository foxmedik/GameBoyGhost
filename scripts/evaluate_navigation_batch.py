"""Run preregistered anchored candidates and apply the development selection gate."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.dataset import sha256
from report_navigation_recovery import compare


def evaluate(batch):
    batch=Path(batch).resolve();plan=json.loads((batch/'plan.json').read_text())
    assert sha256(ROOT/plan['parent'])==plan['parent_sha256']
    def command(args,log):
        with log.open('x') as f:subprocess.run([sys.executable,*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    def candidate(weight):
        model=batch/f'anchor-{weight}'/'epoch-012.pt'
        m=json.loads(model.with_suffix('.json').read_text());assert sha256(model)==m['sha256']
        assert m['identity']['source_sha256']==plan['trainer_sha256']
        dest=batch/f'eval-{weight}';dest.mkdir(exist_ok=False)
        results={}
        specs=[('original','runs/navigation-cache-v2','runs/navigation-live-v2','runs/navigation-live-no-history-v1/result.json'),
               ('additional','runs/navigation-recovery-dev-v1','runs/navigation-recovery-baseline-v1','runs/navigation-recovery-baseline-v1/result.json')]
        for name,cache,baseline,parent in specs:
            command(['scripts/evaluate_navigation.py','--cache',cache,'--checkpoint',str(model),'--out',str(dest/name),'--baseline',baseline,'--workers','8'],dest/f'{name}.log')
            results[name]=compare(parent,str(dest/name/'result.json'))
            results[name]['summary']=json.loads((dest/name/'result.json').read_text())['summary']['learned']
            print(json.dumps(dict(weight=weight,panel=name,result=results[name])),flush=True)
        results['continuous']=[]
        for start in ['house','beach','approach']:
            command(['scripts/run_navigation_chain.py','--checkpoint',str(model),'--goal','0','0','226','36','121','--start',start,'--out',str(dest/f'chain-{start}')],dest/f'chain-{start}.log')
            r=json.loads((dest/f'chain-{start}'/'result.json').read_text())
            parent=json.loads((ROOT/f'runs/navigation-chain-{start}-v1/result.json').read_text())
            assert r['sword_step']==parent['sword_step'] and r['actions'][:r['sword_step']]==parent['actions'][:parent['sword_step']]
            results['continuous'].append({k:r[k] for k in ['start','status','steps','navigation_steps','navigation_damage']})
        eligible=all(not results[n]['lost'] and results[n]['corrected_damage']==0 and results[n]['corrected_deaths']==0 for n in ['original','additional'])
        eligible=eligible and all(r['status']=='success' and r['navigation_damage']==0 for r in results['continuous'])
        results.update(weight=weight,eligible=eligible,policy_path=str(model.relative_to(ROOT)),policy_sha256=sha256(model))
        (dest/'comparison.json').write_text(json.dumps(results,indent=2));return results
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(candidate,plan['weights']))
    passing=[r for r in results if r['eligible']]
    passing.sort(key=lambda r:(-sum(r[n]['corrected_successes'] for n in ['original','additional']),sum(r[n]['summary']['mean_steps'] for n in ['original','additional'])))
    report=dict(candidates=results,selected=passing[0]['weight'] if passing else None,
        selection_scope='Known development panels, six original cases supplied correction supervision.',
        reserved_evaluation_used=False,harness_privilege='D',completion_evaluated=False)
    (batch/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args();evaluate(a.batch)

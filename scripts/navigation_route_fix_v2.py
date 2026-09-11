"""Collect route-candidate corrections and retire the newly trained local cohort."""
import json
from pathlib import Path
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256
from navigation_route_experiment import collect_case
import navigation_recovery as rec
OUT=ROOT/'runs/navigation-routes-v2'
PARENT=ROOT/'runs/navigation-routes-v1/model/epoch-008.pt'
KEY='d5f00d7e9f023bd1bb87305aefd12456734ef575a04390ba3dba2e409ee972bf'

def main():
    OUT.mkdir(exist_ok=False);(OUT/'data').mkdir();(OUT/'local-data').mkdir()
    old=ROOT/'runs/navigation-routes-v1';curriculum=json.loads((old/'curriculum.json').read_text())
    case=next(c for c in json.loads((ROOT/'runs/navigation-live-correction-v3/fresh-panel/live-dev-cases.json').read_text()) if c['segment_id']==KEY)
    failed=json.loads((old/f'eval-fresh/{KEY}-learned.json').read_text());good=json.loads((ROOT/f'runs/navigation-focused-v4/eval-fresh/{KEY}-learned.json').read_text())
    first=next(i for i,(a,b) in enumerate(zip(good['actions'],failed['actions'])) if a!=b)
    plan=dict(parent=str(PARENT),parent_sha256=sha256(PARENT),curriculum=curriculum,epochs=8,learning_rate=1e-5,retention_weight=8,
        retention_route_data=str(old/'data'),focus_path_fragment='/fresh-',focus_batch_fraction=0.5,preservation_summary=str(old/'candidate/summary.json'),retired_cohorts=[case['cohort_id']],target_case=case,first_divergence=first,
        selection='Fixed final epoch. Preserve v4 local successes and both v1 completed routes; zero damage/deaths; retain original continuous chains.',reserved_evaluation_used=False)
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(old/'curriculum.json',OUT/'curriculum.json');shutil.copy2(__file__,OUT/'collector_source.py')
    jobs=[]
    for pos in (0,first,first+4):
        c={**case,'segment_id':f'fresh-fix-{pos}','replay_extra':failed['actions'][:pos],'success_cap':4,'attempt_cap':32,'rollout_policy':str(PARENT)}
        jobs.append((c,0,str(OUT/'local-data')))
    # The selected v4 continuation is independently replayed at its exact origin.
    jobs.append(({**case,'segment_id':'fresh-v4-preserve','fixed_actions':good['actions'],'success_cap':1,'attempt_cap':1,'rollout_policy':str(PARENT)},0,str(OUT/'local-data')))
    with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
        futures=[pool.submit(rec.collect_job,j) for j in jobs]
        route_futures=[pool.submit(collect_case,(str(old/'candidate'/f'{r["id"]}-{s}'),str(PARENT),str(OUT/'data'))) for r in curriculum['routes'] for s in curriculum['starts']]
        local=[f.result() for f in futures];routes=[f.result() for f in route_futures]
    for mpath in (OUT/'local-data').glob('*/manifest.json'):
        m=json.loads(mpath.read_text());dest=OUT/'data'/mpath.parent.name;dest.mkdir();paths=[]
        for i,a in enumerate(m['successes']):
            source=mpath.parent/f'success-{i}.npz';shutil.copy2(source,dest/source.name)
            attempt=next(t for t in m['attempts'] if t['attempt']==a['attempt']);assert attempt['success'] and attempt['damage']==0
            paths.append(dict(file=source.name,sha256=sha256(source),actions=a['actions'],replay_verified=True))
        (dest/'manifest.json').write_text(json.dumps(dict(paths=paths,replay_verified=True,policy_sha256=sha256(PARENT),source_manifest=str(mpath),source_sha256=sha256(mpath)),indent=2))
    (OUT/'collection.json').write_text(json.dumps(routes,indent=2));(OUT/'local-collection.json').write_text(json.dumps(local,indent=2));print(json.dumps(dict(routes=routes,local=local)),flush=True)

if __name__=='__main__':main()

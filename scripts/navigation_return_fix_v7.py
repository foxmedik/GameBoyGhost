"""One return-leg correction on top of the broad live preservation dataset."""
import json,sys,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import navigation_recovery as rec
from gameboy_agent.dataset import sha256
OUT=ROOT/'runs/navigation-routes-v7';OLD=ROOT/'runs/navigation-routes-v6';PARENT=OLD/'model/epoch-008.pt'
def read(p):return json.loads(Path(p).read_text())
def main():
 OUT.mkdir(exist_ok=False);raw=OUT/'raw-data';raw.mkdir();data=OUT/'data';data.mkdir();jobs=[]
 for p in (OLD/'data').iterdir():
  if p.is_dir():(data/p.name).symlink_to(p.resolve(),target_is_directory=True)
 chain='runs/navigation-routes-v6/candidate/west_return-approach';r=read(ROOT/chain/'result.json');begin=r['progress']['leg_start'];assert r['progress']['cursor']==3 and r['navigation_damage']==0
 for pos in [begin,begin+2,begin+4,begin+8,begin+16,begin+48,begin+96]:
  c=dict(segment_id=f'finish-repair-{pos}',chain=chain,start='approach',goal=r['route']['goals'][3],replay_extra=r['actions'][r['sword_step']:pos],attempt_cap=128,success_cap=3,rollout_policy=str(PARENT));jobs.append((c,0,str(raw)))
 plan=read(OLD/'plan.json');plan.update(parent=str(PARENT),parent_sha256=sha256(PARENT),learning_rate=2e-6,balanced_path_groups=['repair-','local-','beach-','west-','finish-'],group_batch_sizes=[16,80,48,48,64],recovery_entry_group='finish-',recovery_entry_rows=4,recovery_entry_weight=8,
  allowed_collection_policies=[sha256(PARENT),read(OLD/'plan.json')['parent_sha256']],retention_route_data=str(OLD/'data'),new_jobs=[j[0] for j in jobs],inherited_training_plan=str(OLD/'training-plan.json'),inherited_training_plan_sha256=sha256(OLD/'training-plan.json'),
  local_preservation_roots=[str(ROOT/f'runs/navigation-routes-v{i}') for i in range(1,7)],preservation_summaries=[str(ROOT/f'runs/navigation-routes-v{i}/candidate/summary.json') for i in range(1,7)])
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(OLD/'curriculum.json',OUT/'curriculum.json');shutil.copy2(__file__,OUT/'collector_source.py')
 with ProcessPoolExecutor(max_workers=7,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for result in pool.map(rec.collect_job,jobs):results.append(result);print(json.dumps(result),flush=True)
 for p in raw.glob('*/manifest.json'):
  m=read(p);dest=data/p.parent.name;dest.mkdir();paths=[]
  for i,a in enumerate(m['successes']):
   source=p.parent/f'success-{i}.npz';attempt=next(t for t in m['attempts'] if t['attempt']==a['attempt']);assert attempt['success'] and attempt['damage']==0
   shutil.copy2(source,dest/source.name);paths.append(dict(file=source.name,sha256=sha256(source),actions=a['actions'],replay_verified=True))
  (dest/'manifest.json').write_text(json.dumps(dict(paths=paths,replay_verified=True,policy_sha256=sha256(PARENT),source_manifest=str(p),source_sha256=sha256(p)),indent=2))
 (OUT/'collection.json').write_text(json.dumps(read(OLD/'collection.json')+results,indent=2))
if __name__=='__main__':main()

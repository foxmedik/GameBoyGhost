"""Train cliff detours and their continuous return legs, preserving prior skills."""
import json,sys,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import navigation_recovery as rec
from gameboy_agent.dataset import sha256
OUT=ROOT/'runs/navigation-routes-v8';OLD=ROOT/'runs/navigation-routes-v7';PARENT=OLD/'model/epoch-008.pt'
def read(p):return json.loads(Path(p).read_text())
def main():
 OUT.mkdir(exist_ok=False);data=OUT/'data';data.mkdir();raw=OUT/'raw-data';raw.mkdir();jobs=[];new=[]
 for p in (OLD/'data').iterdir():
  if p.is_dir():(data/p.name).symlink_to(p.resolve(),target_is_directory=True)
 for start in ['house','beach','approach']:
  source=ROOT/f'runs/navigation-cliff-probe-v1/cliff-west_neighbor-{start}';m=read(source/'manifest.json');assert m['paths'] and m['replay_verified'];(data/source.name).symlink_to(source.resolve(),target_is_directory=True)
  chain=f'runs/navigation-routes-v7/candidate/room_loop-{start}';r=read(ROOT/chain/'result.json')
  for i,a in enumerate(m['paths']):
   c=dict(segment_id=f'cliff-return-{start}-{i}',chain=chain,start=start,goal=r['route']['goals'][3],replay_extra=r['actions'][r['sword_step']:r['progress']['leg_start']]+a['actions'],attempt_cap=64,success_cap=3,rollout_policy=str(PARENT));jobs.append((c,0,str(raw)))
  new.append(dict(id=source.name,successes=len(m['paths']),source_manifest_sha256=sha256(source/'manifest.json')))
 plan=read(OLD/'plan.json');plan.update(parent=str(PARENT),parent_sha256=sha256(PARENT),learning_rate=1e-5,balanced_path_groups=['repair-','local-','beach-','west-','finish-','cliff-'],group_batch_sizes=[16,80,32,32,32,64],recovery_entry_group='cliff-',recovery_entry_rows=4,recovery_entry_weight=8,
  allowed_collection_policies=sorted(set(read(OLD/'plan.json')['allowed_collection_policies']+[sha256(PARENT)])),retention_route_data=str(OLD/'data'),new_jobs=[j[0] for j in jobs],cliff_probe='runs/navigation-cliff-probe-v1',inherited_training_plan=str(OLD/'training-plan.json'),inherited_training_plan_sha256=sha256(OLD/'training-plan.json'),
  local_preservation_roots=[str(ROOT/f'runs/navigation-routes-v{i}') for i in range(1,8)],preservation_summaries=[str(ROOT/f'runs/navigation-routes-v{i}/candidate/summary.json') for i in range(1,8)],selection='Fixed final epoch. Improve beyond selected v7 six complete routes; preserve every earlier safe local and complete-route success; zero damage/deaths.')
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(OLD/'curriculum.json',OUT/'curriculum.json');shutil.copy2(__file__,OUT/'collector_source.py')
 with ProcessPoolExecutor(max_workers=5,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for result in pool.map(rec.collect_job,jobs):results.append(result);print(json.dumps(result),flush=True)
 for p in raw.glob('*/manifest.json'):
  m=read(p);dest=data/p.parent.name;dest.mkdir();paths=[]
  for i,a in enumerate(m['successes']):
   source=p.parent/f'success-{i}.npz';attempt=next(t for t in m['attempts'] if t['attempt']==a['attempt']);assert attempt['success'] and attempt['damage']==0
   shutil.copy2(source,dest/source.name);paths.append(dict(file=source.name,sha256=sha256(source),actions=a['actions'],replay_verified=True))
  (dest/'manifest.json').write_text(json.dumps(dict(paths=paths,replay_verified=True,policy_sha256=sha256(PARENT),source_manifest=str(p),source_sha256=sha256(p)),indent=2))
 (OUT/'collection.json').write_text(json.dumps(read(OLD/'collection.json')+new+results,indent=2))
if __name__=='__main__':main()

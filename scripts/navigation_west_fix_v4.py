"""Westbound recovery entry corrections with explicit preservation anchors."""
import json
from pathlib import Path
import shutil,sys
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256
import navigation_recovery as rec
OUT=ROOT/'runs/navigation-routes-v4';PARENT=ROOT/'runs/navigation-routes-v3/model/epoch-008.pt'
def read(p):return json.loads(Path(p).read_text())
def main():
 OUT.mkdir(exist_ok=False);data=OUT/'raw-data';data.mkdir();(OUT/'data').mkdir();jobs=[];diagnosis=[];retired=set()
 def add(c):jobs.append(({**c,'rollout_policy':str(PARENT)},0,str(data)))
 for name,key,panel,goodroot in [('damage','2b70007c69c8e7a7faa9399a6eea7e76e799e097862a30690fafdf1f90fa4f51','runs/navigation-cache-v2','runs/navigation-routes-v3/eval-original'),('fresh','d5f00d7e9f023bd1bb87305aefd12456734ef575a04390ba3dba2e409ee972bf','runs/navigation-live-correction-v3/fresh-panel','runs/navigation-routes-v3/eval-fresh')]:
  c=next(c for c in read(ROOT/panel/'live-dev-cases.json') if c['segment_id']==key);good=read(ROOT/goodroot/f'{key}-learned.json')
  if c.get('cohort_id'):retired.add(c['cohort_id'])
  add({**c,'segment_id':f'{name}-anchor','fixed_actions':good['actions'],'attempt_cap':1,'success_cap':1})
 # Preserve every waypoint of all three known successful beach routes explicitly.
 for start,version in [('house','v3'),('beach','v3'),('approach','v3')]:
  chain=f'runs/navigation-routes-{version}/candidate/beach_return-{start}';r=read(ROOT/chain/'result.json');assert r['status']=='success' and r['navigation_damage']==0
  begin=r['sword_step']
  for completion in r['progress']['completed']:
   end=completion['step'];i=completion['index'];assert end-begin<=128
   add(dict(segment_id=f'beach-anchor-{start}-{i}',chain=chain,start=start,goal=r['route']['goals'][i],replay_extra=r['actions'][r['sword_step']:begin],fixed_actions=r['actions'][begin:end],attempt_cap=1,success_cap=1));begin=end
 # Correct the lost beach return and westbound legs at their actual v2 prefixes.
 for route,start in [('west_return','beach'),('west_return','approach')]:
  chain=f'runs/navigation-routes-v3/candidate/{route}-{start}';r=read(ROOT/chain/'result.json');rows=[json.loads(l) for l in (ROOT/chain/'trajectory.jsonl').read_text().splitlines()]
  health=rows[r['sword_step']-1]['health'];harm=next(a['step'] for a in rows[r['sword_step']:] if a['health']<health)
  i=rows[harm]['goal_index'];begin=r['progress']['completed'][i-1]['step']
  positions=sorted({begin,begin+4,*[max(begin,harm-d) for d in (16,8,4,3,2,1)]})
  diagnosis.append(dict(name=route,start=start,goal_index=i,handoff=begin,first_damage_action=harm,collection_positions=positions))
  for pos in positions:
   add(dict(segment_id=f'{"west" if route=="west_return" else "beach"}-repair-{start}-{pos}',chain=chain,start=start,goal=r['route']['goals'][i],replay_extra=r['actions'][r['sword_step']:pos],attempt_cap=64,success_cap=3))
 old=ROOT/'runs/navigation-routes-v3';curriculum=read(old/'curriculum.json')
 plan=dict(parent=str(PARENT),parent_sha256=sha256(PARENT),curriculum=curriculum,epochs=8,learning_rate=1e-5,retention_weight=8,retention_route_data=str(old/'data'),
  balanced_path_groups=['damage-','fresh-','beach-','west-'],group_batch_sizes=[32,32,64,128],recovery_entry_rows=4,recovery_entry_weight=8,recovery_entry_group='west-',preservation_summary=str(ROOT/'runs/navigation-routes-v1/candidate/summary.json'),
  preservation_summaries=[str(ROOT/f'runs/navigation-routes-{v}/candidate/summary.json') for v in ['v1','v2','v3']],retired_cohorts=sorted(retired),diagnosis=diagnosis,jobs=[j[0] for j in jobs],
  selection='One fixed final epoch. Preserve all v4 local successes and all successful v1/v2 routes, with zero damage/deaths; preserve original continuous chains.',reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(old/'curriculum.json',OUT/'curriculum.json');shutil.copy2(__file__,OUT/'collector_source.py')
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for result in pool.map(rec.collect_job,jobs):results.append(result);print(json.dumps(result),flush=True)
 for mpth in data.glob('*/manifest.json'):
  m=read(mpth);dest=OUT/'data'/mpth.parent.name;dest.mkdir();paths=[]
  if '-anchor-' in mpth.parent.name:assert m['successes'],str(mpth)
  for i,a in enumerate(m['successes']):
   source=mpth.parent/f'success-{i}.npz';attempt=next(t for t in m['attempts'] if t['attempt']==a['attempt']);assert attempt['success'] and attempt['damage']==0
   shutil.copy2(source,dest/source.name);paths.append(dict(file=source.name,sha256=sha256(source),actions=a['actions'],replay_verified=True))
  (dest/'manifest.json').write_text(json.dumps(dict(paths=paths,replay_verified=True,policy_sha256=sha256(PARENT),source_manifest=str(mpth),source_sha256=sha256(mpth)),indent=2))
 (OUT/'collection.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()

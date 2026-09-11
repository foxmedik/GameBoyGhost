"""Broad successful live-trace supervision plus focused timeout recovery."""
import json,sys,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import navigation_recovery as rec
from gameboy_agent.dataset import sha256
OUT=ROOT/'runs/navigation-routes-v6';OLD=ROOT/'runs/navigation-routes-v5';PARENT=OLD/'model/epoch-008.pt'
def read(p):return json.loads(Path(p).read_text())
def main():
 OUT.mkdir(exist_ok=False);raw=OUT/'raw-data';raw.mkdir();(OUT/'data').mkdir();jobs=[]
 def add(c):jobs.append(({**c,'rollout_policy':str(PARENT)},0,str(raw)))
 key='f49bda234a90275504d0a788f3ed896810299bca814d35a880e2da18d8b37087';case=next(c for c in read(ROOT/'runs/navigation-live-correction-v3/fresh-panel/live-dev-cases.json') if c['segment_id']==key)
 good=read(ROOT/f'runs/navigation-routes-v4/eval-fresh/{key}-learned.json');bad=read(OLD/f'eval-fresh/{key}-learned.json');assert good['success'] and good['damage']==0
 first=next(i for i,(a,b) in enumerate(zip(good['actions'],bad['actions'])) if a!=b)
 add({**case,'segment_id':'repair-anchor','fixed_actions':good['actions'],'attempt_cap':1,'success_cap':1})
 for pos in sorted({0,max(0,first-2),first,first+2}):add({**case,'segment_id':f'repair-origin-{pos}','replay_extra':bad['actions'][:pos],'attempt_cap':48,'success_cap':3})
 retired=set([case['cohort_id']]);anchor_sources=[]
 for panel,cache in [('original','runs/navigation-cache-v2'),('additional','runs/navigation-recovery-dev-v1'),('fresh','runs/navigation-live-correction-v3/fresh-panel')]:
  for c in read(ROOT/cache/'live-dev-cases.json'):
   choices=[]
   for version in ['v5','v4','v3']:
    source=ROOT/f'runs/navigation-routes-{version}/eval-{panel}/{c["segment_id"]}-learned.json';r=read(source)
    if r['success'] and r['damage']==0:choices.append((source,r))
   source=ROOT/f'runs/navigation-focused-v4/eval-{panel}/{c["segment_id"]}-learned.json';r=read(source)
   if r['success'] and r['damage']==0:choices.append((source,r))
   if not choices:continue
   source,r=choices[0]
   if c.get('cohort_id'):retired.add(c['cohort_id'])
   anchor_sources.append(dict(case_id=c['segment_id'],panel=panel,source=str(source),source_sha256=sha256(source),episode_id=c['episode_id']))
   add({**c,'segment_id':f'local-anchor-{panel}-{c["segment_id"]}','fixed_actions':r['actions'],'attempt_cap':1,'success_cap':1})
 # Actual failing house return: prior waypoint ends a few pixels off its old path.
 chain='runs/navigation-routes-v5/candidate/beach_return-house';r=read(ROOT/chain/'result.json');begin=r['progress']['leg_start']
 for pos in [begin,begin+4,begin+16,begin+64]:
  add(dict(segment_id=f'repair-house-{pos}',chain=chain,start='house',goal=r['route']['goals'][3],replay_extra=r['actions'][r['sword_step']:pos],attempt_cap=64,success_cap=3))
 for route in ['beach_return','west_return']:
  for start in ['house','beach','approach']:
   chain=f'runs/navigation-routes-v4/candidate/{route}-{start}';r=read(ROOT/chain/'result.json');assert r['navigation_damage']==0;begin=r['sword_step']
   for completion in r['progress']['completed']:
    end=completion['step'];i=completion['index'];assert end-begin<=128
    add(dict(segment_id=f'{"west" if route=="west_return" else "beach"}-anchor-{start}-{i}',chain=chain,start=start,goal=r['route']['goals'][i],replay_extra=r['actions'][r['sword_step']:begin],fixed_actions=r['actions'][begin:end],attempt_cap=1,success_cap=1));begin=end
 plan=dict(parent=str(PARENT),parent_sha256=sha256(PARENT),curriculum=read(OLD/'curriculum.json'),epochs=8,learning_rate=5e-6,retention_weight=8,retention_route_data=str(OLD/'data'),balanced_path_groups=['repair-','local-','beach-','west-'],group_batch_sizes=[64,96,48,48],action_margin=0.25,action_margin_weight=2,retired_cohorts=sorted(retired),live_anchor_sources=anchor_sources,target_case=case,first_divergence=first,jobs=[j[0] for j in jobs],local_preservation_roots=[str(ROOT/f'runs/navigation-routes-v{i}') for i in range(1,6)],preservation_summaries=[str(ROOT/f'runs/navigation-routes-{v}/candidate/summary.json') for v in ['v1','v2','v3','v4','v5']],selection='One fixed final epoch; preserve all v4 local successes and all earlier complete routes; zero damage/deaths on all local panels and routes.',reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(OLD/'curriculum.json',OUT/'curriculum.json');shutil.copy2(__file__,OUT/'collector_source.py')
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for result in pool.map(rec.collect_job,jobs):results.append(result);print(json.dumps(result),flush=True)
 for p in raw.glob('*/manifest.json'):
  m=read(p);dest=OUT/'data'/p.parent.name;dest.mkdir();paths=[]
  if '-anchor-' in p.parent.name:assert m['successes'],str(p)
  for i,a in enumerate(m['successes']):
   source=p.parent/f'success-{i}.npz';attempt=next(t for t in m['attempts'] if t['attempt']==a['attempt']);assert attempt['success'] and attempt['damage']==0
   shutil.copy2(source,dest/source.name);paths.append(dict(file=source.name,sha256=sha256(source),actions=a['actions'],replay_verified=True))
  (dest/'manifest.json').write_text(json.dumps(dict(paths=paths,replay_verified=True,policy_sha256=sha256(PARENT),source_manifest=str(p),source_sha256=sha256(p)),indent=2))
 (OUT/'collection.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()

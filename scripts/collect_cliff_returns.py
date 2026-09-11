"""Verify full-budget western return detours after successful cliff approaches."""
import sys,json,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from collect_cliff_detour import collect_job
if __name__=='__main__':
 out=ROOT/'runs/navigation-cliff-returns-v3';out.mkdir(exist_ok=False);shutil.copy2(ROOT/'scripts/collect_cliff_detour.py',out/'collector_source.py');jobs=[]
 for start in ['house','beach','approach']:
  m=json.loads((ROOT/f'runs/navigation-cliff-probe-v1/cliff-west_neighbor-{start}/manifest.json').read_text())
  for i,a in enumerate(m['paths']):jobs.append((start,'return_west',str(out),dict(a,id=i,waypoint_tolerance=3)))
 with ProcessPoolExecutor(max_workers=5,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for r in pool.map(collect_job,jobs):results.append(r);print(json.dumps(r),flush=True)
 (out/'collection.json').write_text(json.dumps(results,indent=2))

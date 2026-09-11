"""Attach verified continuous cliff-return demonstrations before training."""
import argparse,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256

def finalize(out,returns):
 out=Path(out).resolve();returns=Path(returns).resolve();assert not (out/'model').exists()
 plan=json.loads((out/'plan.json').read_text());added=[];links=[]
 for manifest in sorted(returns.glob('*/manifest.json')):
  m=json.loads(manifest.read_text());assert m['replay_verified'];start=Path(m['source_run']).name.removeprefix('room_loop-');index=int(manifest.parent.name.rsplit('-',1)[-1])
  approach=json.loads((ROOT/f'runs/navigation-cliff-probe-v1/cliff-west_neighbor-{start}/manifest.json').read_text())['paths'][index]
  for a in m['paths']:
   assert a['prefix']==approach['prefix']+approach['actions']
   assert a['initial']==approach['final'],'Fourth goal must begin at exact third-goal endpoint'
   assert sha256(manifest.parent/a['file'])==a['sha256']
  if m['paths']:
   links.append((out/'data'/manifest.parent.name,manifest.parent.resolve()))
  added.append(dict(id=manifest.parent.name,successes=len(m['paths']),source_manifest_sha256=sha256(manifest)))
 assert len(added)==5 and all(a['successes'] for a in added),'Need a verified return for every retained approach path'
 for dest,source in links:dest.symlink_to(source,target_is_directory=True)
 existing=json.loads((out/'collection.json').read_text());(out/'collection.json').write_text(json.dumps(existing+added,indent=2))
 plan.update(return_collector=str(returns),return_collection=added,continuous_cliff_handoffs_verified=True)
 (out/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(added))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--returns',required=True);a=p.parse_args();finalize(a.out,a.returns)

"""Read-only audit of verified cliff labels and selected/rejected navigators."""
import json,sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import torch
from gameboy_agent.navigation import NavigationNet
from gameboy_agent.dataset import sha256

def main():
 torch.set_num_threads(1);models={};saved={}
 for name in ['v7','v8']:
  p=ROOT/f'runs/navigation-routes-{name}/model/epoch-008.pt';assert sha256(p)==json.loads(p.with_suffix('.json').read_text())['sha256']
  s=torch.load(p,map_location='cpu');m=NavigationNet(s['inputs']);m.load_state_dict(s['model']);m.eval();models[name]=m;saved[name]=s
 paths=[];labels=defaultdict(set);sources={}
 for manifest in sorted((ROOT/'runs/navigation-routes-v8/data').glob('cliff*/manifest.json')):
  meta=json.loads(manifest.read_text());assert meta['replay_verified'];sources[str(manifest.relative_to(ROOT))]=sha256(manifest)
  for spec in meta['paths']:
   p=manifest.parent/spec['file'];assert spec['replay_verified'] and sha256(p)==spec['sha256'];d=np.load(p);x,y=d['x'],d['y'];assert np.array_equal(y,spec['actions'])
   goal=spec.get('goal');assert goal is not None
   assert np.allclose(x[:,-7],goal['x']/160) and np.allclose(x[:,-6],goal['y']/144)
   mask=saved['v7']['input_mask']
   for xx,yy in zip(x,y):labels[(xx*mask).tobytes()].add(int(yy[0]))
   stats={}
   for name,m in models.items():
    s=saved[name]
    with torch.no_grad():z=m(torch.from_numpy((x-s['mean'])/s['scale']*s['input_mask'])).numpy()
    movement=z[:,:5].argmax(1);buttons=z[:,5:].argmax(1);bad=np.flatnonzero(movement!=y[:,0]);stats[name]=dict(movement_correct=int((movement==y[:,0]).sum()),button_correct=int((buttons==y[:,1]).sum()),first_movement_disagreement=int(bad[0]) if len(bad) else None,first_action=[int(movement[0]),int(buttons[0])],first_four_movement_matches=(movement[:4]==y[:4,0]).tolist())
   paths.append(dict(path=str(p.relative_to(ROOT)),sha256=sha256(p),kind='return' if 'return' in p.parent.name else 'approach',rows=len(y),goal=goal,first_teacher_action=y[0].tolist(),stats=stats))
 assert len(paths)==20
 summary={}
 for kind in ['approach','return']:
  subset=[p for p in paths if p['kind']==kind];rows=sum(p['rows'] for p in subset)
  summary[kind]=dict(paths=len(subset),rows=rows,models={n:dict(movement_accuracy=sum(p['stats'][n]['movement_correct'] for p in subset)/rows,button_accuracy=sum(p['stats'][n]['button_correct'] for p in subset)/rows,matching_first_movements=sum(p['stats'][n]['first_movement_disagreement']!=0 for p in subset)) for n in models})
 result=dict(summary=summary,paths=paths,exact_masked_states=len(labels),states_with_conflicting_movement_labels=sum(len(v)>1 for v in labels.values()),original_goals_verified=True,source_manifest_hashes=sources,source_sha256=sha256(__file__),offline_training_row_diagnostic=True,interpretation='Training-row agreement does not establish live navigation success. Existing physical verification is checked through immutable manifests; this audit runs no emulator or training.')
 out=ROOT/'reports/cliff-navigation-audit-v1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ('summary','exact_masked_states','states_with_conflicting_movement_labels')},indent=2))
 print('APPROACH ENTRIES',json.dumps([dict(path=p['path'],teacher=p['first_teacher_action'],v7=p['stats']['v7'],v8=p['stats']['v8']) for p in paths if p['kind']=='approach'],indent=2))
if __name__=='__main__':main()

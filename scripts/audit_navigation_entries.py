"""Training-state diagnostics for the first decisions of verified recoveries."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from gameboy_agent.dataset import sha256

def audit(out):
 import torch
 from gameboy_agent.navigation import NavigationNet
 torch.set_num_threads(1);out=Path(out).resolve();plan=json.loads((out/'plan.json').read_text());result={}
 for label,checkpoint in [('parent',Path(plan['parent'])),('candidate',out/'model/epoch-008.pt')]:
  assert sha256(checkpoint)==json.loads(checkpoint.with_suffix('.json').read_text())['sha256']
  s=torch.load(checkpoint,map_location='cpu');model=NavigationNet(s['inputs']);model.load_state_dict(s['model']);model.eval();rows=[]
  for manifest in sorted((out/'data').glob('west-*/manifest.json')):
   m=json.loads(manifest.read_text());assert m['replay_verified']
   for a in m['paths']:
    p=manifest.parent/a['file'];assert sha256(p)==a['sha256'];d=np.load(p)
    x=torch.from_numpy((d['x']-s['mean'])/s['scale']*s['input_mask'])
    with torch.no_grad():z=model(x)
    pred=torch.stack([z[:,:5].argmax(1),z[:,5:].argmax(1)],1).numpy();wrong=np.where(np.any(pred!=d['y'],axis=1))[0]
    rows.append(dict(path=str(p.relative_to(ROOT)),teacher_first=d['y'][0].tolist(),predicted_first=pred[0].tolist(),first_action_matches=bool(np.array_equal(pred[0],d['y'][0])),disagreements=wrong.tolist(),length=len(pred)))
  result[label]=dict(first_movements_matched=sum(r['teacher_first'][0]==r['predicted_first'][0] for r in rows),first_actions_matched=sum(r['first_action_matches'] for r in rows),paths=len(rows),details=rows)
 result['interpretation']='Training-path label agreement, including alternative teacher actions. Not a live success metric or a held-out evaluation.'
 (out/'entry-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:{n:r[n] for n in ['first_actions_matched','paths']} for k,r in result.items() if isinstance(r,dict)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);audit(p.parse_args().out)

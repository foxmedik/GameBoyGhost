"""Fixed goal specialists: v7 fallback immutable, final-goal routing from data."""
import json,sys,shutil,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import torch
from gameboy_agent.navigation import NavigationNet
from gameboy_agent.dataset import sha256
READ=lambda p:json.loads(Path(p).read_text())
OUT=ROOT/'runs/navigation-cliff-specialists-v1'

def goal_key(x):
 room=(x[219:243].reshape(3,8)@(2**np.arange(8))).astype(int).tolist()
 return tuple(room)+tuple(np.rint(x[-7:-5]*[160,144]).astype(int))

def main():
 torch.set_num_threads(4);torch.manual_seed(2027);OUT.mkdir(exist_ok=False)
 parent=ROOT/'runs/navigation-routes-v7/model/epoch-008.pt';s=torch.load(parent,map_location='cpu');reference=copy.deepcopy(s['model']);data=ROOT/'runs/navigation-routes-v9/data';goals=set();selected={};artifacts={}
 for manifest in sorted(data.glob('*/manifest.json')):
  m=READ(manifest);assert m['replay_verified'];artifacts[str(manifest.relative_to(ROOT))]=sha256(manifest)
  for a in m['paths']:
   p=manifest.parent/a['file'];assert a['replay_verified'] and sha256(p)==a['sha256'];artifacts[str(p.relative_to(ROOT))]=sha256(p);d=np.load(p);assert np.array_equal(d['y'],a['actions'])
   if manifest.parent.name.startswith('cliff-'):goals.update(goal_key(x) for x in d['x'])
   for i,(x,y) in enumerate(zip(d['x'],d['y'])):
    k=(x*s['input_mask']).tobytes();cost=len(d['y'])-i
    if k not in selected or cost<selected[k]['cost']:selected[k]=dict(x=x,y=y,cost=cost,path=str(p.relative_to(ROOT)),row=i)
 goals=sorted(goals);prior=READ(ROOT/'runs/navigation-routes-v9/plan.json');plan=dict(experiment='Two feed-forward specialists routed by exact original final goals derived from cliff demonstrations. V7 fallback and normalization are byte-preserved. No intermediate goals, runtime teacher, route index or action replay.',parent=str(parent),parent_sha256=sha256(parent),goals=[dict(room=list(k[:3]),x=int(k[3]),y=int(k[4])) for k in goals],epochs=256,learning_rate=1e-4,seed=2027,batch_size=128,button_weight=.25,cliff_sampling_fraction=.5,selection=prior['selection'],additional_sword_evaluation=prior['additional_sword_evaluation'],curriculum=prior['curriculum'],baseline_hashes=prior['baseline_hashes'],trainer_sha256=sha256(__file__),training_artifacts=artifacts,reserved_evaluation_used=False,scope_caveat='Known-goal specialization, not a general detour planner. Shared return goal can still regress and is fully evaluated. Only final checkpoint eligible; no live checkpoint shopping.')
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'trainer_source.py');shutil.copy2(ROOT/'runs/navigation-routes-v9/curriculum.json',OUT/'curriculum.json');(OUT/'model').mkdir();experts=[];fits=[]
 for g in plan['goals']:
  key=tuple(g['room'])+(g['x'],g['y']);rows=[r for r in selected.values() if goal_key(r['x'])==key];assert rows
  x=torch.from_numpy((np.stack([r['x'] for r in rows])-s['mean'])/s['scale']*s['input_mask']);y=torch.from_numpy(np.stack([r['y'] for r in rows]));groups=[torch.tensor([i for i,r in enumerate(rows) if ('/cliff-' in r['path'])==cliff]) for cliff in [True,False]];assert all(len(a) for a in groups)
  model=NavigationNet(s['inputs']);model.load_state_dict(reference);opt=torch.optim.Adam(model.parameters(),lr=plan['learning_rate']);rng=torch.Generator().manual_seed(plan['seed']);history=[]
  for epoch in range(1,plan['epochs']+1):
   losses=[]
   for _ in range(max(4,(len(rows)+127)//128)):
    idx=torch.cat([group[torch.randint(len(group),(64,),generator=rng)] for group in groups]);z=model(x[idx]);loss=torch.nn.functional.cross_entropy(z[:,:5],y[idx,0])+.25*torch.nn.functional.cross_entropy(z[:,5:],y[idx,1]);opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();losses.append(float(loss.detach()))
   history.append(dict(epoch=epoch,loss=float(np.mean(losses))))
   if epoch%64==0:print(json.dumps(dict(goal=g,**history[-1])),flush=True)
  model.eval()
  with torch.no_grad():z=model(x);fit=dict(goal=g,rows=len(rows),movement_accuracy=float((z[:,:5].argmax(1)==y[:,0]).float().mean()),button_accuracy=float((z[:,5:].argmax(1)==y[:,1]).float().mean()))
  print('FIT',json.dumps(fit),flush=True);fits.append(fit);experts.append(dict(goal=g,model=model.state_dict(),optimizer=opt.state_dict(),shuffle_rng=rng.get_state(),history=history,provenance=[{k:v for k,v in r.items() if k not in ('x','y')} for r in rows]))
 assert all(torch.equal(s['model'][k],reference[k]) for k in reference)
 path=OUT/'model/epoch-256.pt';torch.save({**s,'goal_experts':experts,'specialist_plan_sha256':sha256(OUT/'plan.json')},path);path.with_suffix('.json').write_text(json.dumps(dict(sha256=sha256(path),plan_sha256=sha256(OUT/'plan.json')),indent=2));(OUT/'training-fit.json').write_text(json.dumps(fits,indent=2))
 print('COMPLETE',sha256(path),flush=True)
if __name__=='__main__':main()

"""Update only the cliff expert from fully verified continuous corrections."""
import json,sys,shutil,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from gameboy_agent.navigation import NavigationNet
from gameboy_agent.dataset import sha256
from train_cliff_specialists import goal_key
READ=lambda p:json.loads(Path(p).read_text());OUT=ROOT/'runs/navigation-cliff-specialists-v2'

def main():
 torch.set_num_threads(4);torch.manual_seed(2027);OUT.mkdir(exist_ok=False);data=OUT/'data';data.mkdir();base=ROOT/'runs/navigation-cliff-specialists-v1';s=torch.load(base/'model/epoch-256.pt',map_location='cpu');original=copy.deepcopy(s);target=(0,0,226,64,64);sources=[]
 for start in ['house','beach','approach']:
  choices=[]
  for p in (ROOT/'runs/cliff-live-corrections-v1').glob(f'{start}-*/approach.json'):
   a=READ(p);b=READ(p.parent/'return.json')
   if a['accepted'] and b['accepted']:
    assert a['final_fingerprint']==b['initial_fingerprint'] and b['prefix']==a['prefix']+a['actions'];choices.append((a['steps'],str(p),p))
  source=min(choices)[2];m=READ(source);asset=source.parent/m['asset'];assert m['features_replay_verified'] and sha256(asset)==m['asset_sha256'];dest=data/f'cliff-{start}';dest.mkdir();shutil.copy2(asset,dest/'success.npz');meta=dict(file='success.npz',sha256=sha256(asset),teacher_switch_step=m['teacher_switch_step'],source=str(source),source_sha256=sha256(source),return_source_sha256=sha256(source.parent/'return.json'),replay_verified=True);(dest/'manifest.json').write_text(json.dumps(meta,indent=2));sources.append(meta)
 for manifest in sorted((ROOT/'runs/navigation-routes-v9/data').glob('local-*/manifest.json')):
  for a in READ(manifest)['paths']:
   asset=manifest.parent/a['file'];d=np.load(asset)
   if goal_key(d['x'][0])==target:
    assert sha256(asset)==a['sha256'];dest=data/manifest.parent.name;dest.mkdir(exist_ok=True);shutil.copy2(asset,dest/a['file']);meta=dict(file=a['file'],sha256=sha256(asset),teacher_switch_step=None,source=str(manifest),source_sha256=sha256(manifest),replay_verified=True);(dest/'manifest.json').write_text(json.dumps(meta,indent=2))
 prior=READ(base/'plan.json');plan={**prior,'experiment':'Update only the E2 (64,64) expert from three canonical safe corrected cliff paths; keep v7 fallback and v1 return specialist unchanged. Fresh features include actual v1 prefixes and original final goals; all three learned continuous returns verified before training.','epochs':256,'learning_rate':1e-4,'initial_candidate':str(base/'model/epoch-256.pt'),'initial_candidate_sha256':sha256(base/'model/epoch-256.pt'),'trainer_sha256':sha256(__file__),'correction_sources':sources,'entry_weight':8,'entry_rows':8,'training_artifacts':{str(p.relative_to(ROOT)):sha256(p) for p in data.glob('*/*')},'selection':prior['selection']+' Additionally preserve all seven specialist-v1 routes and increase complete routes beyond seven.','specialist_v1_result_sha256':sha256(ROOT/'reports/navigation-cliff-specialists-v1.json')}
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'trainer_source.py');shutil.copy2(base/'curriculum.json',OUT/'curriculum.json');(OUT/'model').mkdir();selected={};labels={}
 for manifest in sorted(data.glob('*/manifest.json')):
  m=READ(manifest);p=manifest.parent/m['file'];d=np.load(p);assert sha256(p)==m['sha256']
  for i,(x,y) in enumerate(zip(d['x'],d['y'])):
   assert goal_key(x)==target;k=(x*s['input_mask']).tobytes();cost=len(d['y'])-i;labels.setdefault(k,set()).add(tuple(y));switch=m['teacher_switch_step'];entry=switch is not None and switch<=i<switch+plan['entry_rows']
   if k not in selected or cost<selected[k]['cost']:selected[k]=dict(x=x,y=y,cost=cost,path=str(p.relative_to(ROOT)),row=i,entry=entry)
 rows=list(selected.values());x=torch.from_numpy((np.stack([r['x'] for r in rows])-s['mean'])/s['scale']*s['input_mask']);y=torch.from_numpy(np.stack([r['y'] for r in rows]));groups=[torch.tensor([i for i,r in enumerate(rows) if ('/cliff-' in r['path'])==cliff]) for cliff in [True,False]];assert all(len(g) for g in groups)
 expert=next(e for e in s['goal_experts'] if tuple(e['goal']['room'])+(e['goal']['x'],e['goal']['y'])==target);model=NavigationNet(s['inputs']);model.load_state_dict(expert['model']);opt=torch.optim.Adam(model.parameters(),lr=plan['learning_rate']);rng=torch.Generator().manual_seed(2027);history=[]
 for epoch in range(1,257):
  losses=[]
  for _ in range(max(4,(len(rows)+127)//128)):
   chunks=[]
   for group in groups:
    weights=torch.tensor([8.0 if rows[i]['entry'] else 1.0 for i in group]);chunks.append(group[torch.multinomial(weights,64,replacement=True,generator=rng)])
   idx=torch.cat(chunks);z=model(x[idx]);loss=torch.nn.functional.cross_entropy(z[:,:5],y[idx,0])+.25*torch.nn.functional.cross_entropy(z[:,5:],y[idx,1]);opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();losses.append(float(loss.detach()))
  history.append(dict(epoch=epoch,loss=float(np.mean(losses))))
  if epoch%64==0:print(json.dumps(history[-1]),flush=True)
 expert.update(model=model.state_dict(),optimizer=opt.state_dict(),shuffle_rng=rng.get_state(),history=history,provenance=[{k:v for k,v in r.items() if k not in ('x','y')} for r in rows]);model.eval()
 with torch.no_grad():z=model(x);fit=dict(rows=len(rows),conflicting_states=sum(len(v)>1 for v in labels.values()),movement_accuracy=float((z[:,:5].argmax(1)==y[:,0]).float().mean()),button_accuracy=float((z[:,5:].argmax(1)==y[:,1]).float().mean()))
 assert all(torch.equal(s['model'][k],original['model'][k]) for k in s['model'])
 for e,o in zip(s['goal_experts'],original['goal_experts']):
  if e is not expert:assert all(torch.equal(e['model'][k],o['model'][k]) for k in e['model'])
 for key in ['mean','scale','input_mask']:assert np.array_equal(s[key],original[key])
 path=OUT/'model/epoch-256.pt';torch.save({**s,'specialist_plan_sha256':sha256(OUT/'plan.json')},path);path.with_suffix('.json').write_text(json.dumps(dict(sha256=sha256(path),plan_sha256=sha256(OUT/'plan.json')),indent=2));(OUT/'training-fit.json').write_text(json.dumps(fit,indent=2));print('FIT',json.dumps(fit));print('COMPLETE',sha256(path))
if __name__=='__main__':main()

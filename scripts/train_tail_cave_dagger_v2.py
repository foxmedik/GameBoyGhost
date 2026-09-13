"""Train the frozen first-divergence Tail Cave DAgger experiment."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from torch import nn
from gameboy_agent.world_memory import file_hash
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_dagger_v2_experiment.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text());cfg=plan['model']
 if file_hash(Path(__file__))!=plan['trainer_sha256']:raise ValueError('Frozen trainer changed')
 base_dir=ROOT/plan['base_data'];base_manifest=json.loads((base_dir/'manifest.json').read_text())
 if file_hash(base_dir/'train.npz')!=plan['base_data_sha256'] or base_manifest['validation_loaded']:raise ValueError('Base data changed')
 correction_dir=ROOT/plan['correction_run'];summary=json.loads((correction_dir/'summary.json').read_text())
 if file_hash(correction_dir/'summary.json')!=plan['correction_summary_sha256'] or summary['successes']<summary['required_successes'] or summary['validation_loaded']:raise ValueError('Correction gate failed')
 correction=[]
 for result in summary['results']:
  if not result['success']:continue
  folder=correction_dir/result['spec']['id'];manifest=json.loads((folder/'manifest.json').read_text())
  if file_hash(folder/'corrections.npz')!=manifest['artifacts']['corrections.npz']:raise ValueError(f'Correction data changed: {folder}')
  correction.append(np.load(folder/'corrections.npz'))
 base=np.load(base_dir/'train.npz');bx=base['x'].copy();by=torch.from_numpy(base['y']);cx=np.concatenate([d['x'] for d in correction]);cy=torch.from_numpy(np.concatenate([d['y'] for d in correction]))
 parent=ROOT/plan['parent'];
 if file_hash(parent)!=plan['parent_sha256']:raise ValueError('Parent changed')
 saved=torch.load(parent,map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);n=saved['base_inputs']
 for x in (bx,cx):x[:,:n]=(x[:,:n]-saved['mean'])/saved['scale']*saved['input_mask']
 bx=torch.from_numpy(bx);cx=torch.from_numpy(cx);torch.set_num_threads(8);torch.manual_seed(cfg['seed']);gen=torch.Generator().manual_seed(cfg['seed']+1);opt=torch.optim.Adam(model.parameters(),lr=cfg['learning_rate']);ce=nn.CrossEntropyLoss();history=[]
 def loss(z,t):return ce(z[:,:5],t[:,0])+ce(z[:,5:8],t[:,1])+ce(z[:,8:],t[:,2])
 def metrics(x,y):
  z=model(x);return {'loss':float(loss(z,y)),'movement_accuracy':float((z[:,:5].argmax(1)==y[:,0]).float().mean()),'button_accuracy':float((z[:,5:8].argmax(1)==y[:,1]).float().mean()),'duration_accuracy':float((z[:,8:].argmax(1)==y[:,2]).float().mean())}
 half=cfg['batch_rows']//2
 for epoch in range(1,cfg['epochs']+1):
  model.train();total=0
  for _ in range(cfg['batches_per_epoch']):
   bi=torch.randint(len(bx),(half,),generator=gen);ci=torch.randint(len(cx),(cfg['batch_rows']-half,),generator=gen);x=torch.cat((bx[bi],cx[ci]));y=torch.cat((by[bi],cy[ci]));opt.zero_grad();value=loss(model(x),y);value.backward();nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();total+=float(value.detach())
  model.eval()
  with torch.no_grad():row={'epoch':epoch,'objective':total/cfg['batches_per_epoch'],'base':metrics(bx,by),'correction':metrics(cx,cy)}
  history.append(row);print(json.dumps(row),flush=True)
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');checkpoint=out/'candidate.pt';torch.save({**saved,'model':model.state_dict(),'history':history,'parent_sha256':plan['parent_sha256']},checkpoint)
 result={'status':'trained_autonomous_live_pending','checkpoint':str(checkpoint),'checkpoint_sha256':file_hash(checkpoint),'base_rows':len(bx),'correction_rows':len(cx),'selection':cfg['selection'],'final':history[-1],'validation_loaded':False};write(out/'result.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

"""Train the frozen compact Tail Cave specialist."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from torch import nn
from gameboy_agent.world_memory import file_hash
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_specialist_v3.json';DATA=ROOT/'runs/tail-cave-specialist-v3-data'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text());cfg=plan['model']
 if file_hash(Path(__file__))!=plan['trainer_sha256']:raise ValueError('Frozen trainer changed')
 manifest=json.loads((DATA/'manifest.json').read_text())
 if manifest['experiment_sha256']!=file_hash(PLAN) or file_hash(DATA/'train.npz')!=manifest['train_sha256'] or manifest['validation_loaded']:raise ValueError('Frozen data changed')
 data=np.load(DATA/'train.npz');raw=data['x'].astype(np.float32);y=torch.from_numpy(data['y']);mean=raw.mean(0);scale=raw.std(0);scale[scale<1e-4]=1;x=torch.from_numpy((raw-mean)/scale);model=DaggerNet(x.shape[1]);torch.set_num_threads(8);torch.manual_seed(cfg['seed']);gen=torch.Generator().manual_seed(cfg['seed']+1);opt=torch.optim.Adam(model.parameters(),lr=cfg['learning_rate']);ce=nn.CrossEntropyLoss();history=[]
 def loss(z,t):return ce(z[:,:5],t[:,0])+ce(z[:,5:8],t[:,1])+ce(z[:,8:],t[:,2])
 for epoch in range(1,cfg['epochs']+1):
  model.train();total=0
  for _ in range(cfg['batches_per_epoch']):
   i=torch.randint(len(x),(cfg['batch_rows'],),generator=gen);opt.zero_grad();v=loss(model(x[i]),y[i]);v.backward();nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();total+=float(v.detach())
  model.eval()
  with torch.no_grad():z=model(x);row={'epoch':epoch,'objective':total/cfg['batches_per_epoch'],'loss':float(loss(z,y)),'movement_accuracy':float((z[:,:5].argmax(1)==y[:,0]).float().mean()),'button_accuracy':float((z[:,5:8].argmax(1)==y[:,1]).float().mean()),'duration_accuracy':float((z[:,8:].argmax(1)==y[:,2]).float().mean())}
  history.append(row);print(json.dumps(row),flush=True)
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');checkpoint=out/'candidate.pt';torch.save({'model':model.state_dict(),'inputs':x.shape[1],'base_inputs':x.shape[1],'mean':mean,'scale':scale,'input_mask':np.ones(x.shape[1],dtype=np.float32),'history':history},checkpoint);result={'status':'trained_autonomous_live_pending','checkpoint':str(checkpoint),'checkpoint_sha256':file_hash(checkpoint),'rows':len(x),'final':history[-1],'validation_loaded':False};write(out/'result.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

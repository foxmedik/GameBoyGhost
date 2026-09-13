"""Train the frozen Tail Cave first-key history controller."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from torch import nn
from gameboy_agent.world_memory import file_hash
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_first_key_model_v1.json';DATA=ROOT/'runs/tail-cave-first-key-data-v1'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text());cfg=plan['model']
 if file_hash(Path(__file__))!=plan['trainer_sha256']:raise ValueError('Frozen trainer changed')
 manifest=json.loads((DATA/'manifest.json').read_text())
 if manifest['experiment_sha256']!=file_hash(PLAN) or file_hash(DATA/'train.npz')!=manifest['train_sha256'] or manifest['validation_loaded']:raise ValueError('Frozen training data changed')
 parent_path=ROOT/plan['parent']
 if file_hash(parent_path)!=plan['parent_sha256']:raise ValueError('Parent changed')
 saved=torch.load(parent_path,map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model'])
 data=np.load(DATA/'train.npz');x=data['x'].copy();y=torch.from_numpy(data['y']);n=saved['base_inputs'];x[:,:n]=(x[:,:n]-saved['mean'])/saved['scale']*saved['input_mask'];x=torch.from_numpy(x)
 torch.set_num_threads(8);torch.manual_seed(cfg['seed']);gen=torch.Generator().manual_seed(cfg['seed']+1);opt=torch.optim.Adam(model.parameters(),lr=cfg['learning_rate']);ce=nn.CrossEntropyLoss();history=[]
 def loss(z,t):return ce(z[:,:5],t[:,0])+ce(z[:,5:8],t[:,1])+ce(z[:,8:],t[:,2])
 for epoch in range(1,cfg['epochs']+1):
  model.train();total=0
  for _ in range(cfg['batches_per_epoch']):
   i=torch.randint(len(x),(cfg['batch_rows'],),generator=gen);opt.zero_grad();value=loss(model(x[i]),y[i]);value.backward();nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();total+=float(value.detach())
  model.eval()
  with torch.no_grad():z=model(x);metrics={'loss':float(loss(z,y)),'movement_accuracy':float((z[:,:5].argmax(1)==y[:,0]).float().mean()),'button_accuracy':float((z[:,5:8].argmax(1)==y[:,1]).float().mean()),'duration_accuracy':float((z[:,8:].argmax(1)==y[:,2]).float().mean())}
  history.append({'epoch':epoch,'objective':total/cfg['batches_per_epoch'],**metrics});print(json.dumps(history[-1]),flush=True)
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');checkpoint=out/'candidate.pt';torch.save({**saved,'model':model.state_dict(),'history':history,'parent_sha256':plan['parent_sha256']},checkpoint)
 result={'status':'trained_live_development_pending','checkpoint':str(checkpoint),'checkpoint_sha256':file_hash(checkpoint),'rows':len(x),'selection':cfg['selection'],'final':history[-1],'validation_loaded':False};write(out/'result.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

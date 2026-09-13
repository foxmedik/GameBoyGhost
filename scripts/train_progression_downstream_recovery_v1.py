"""Fine-tune the frozen history controller on downstream recovery evidence."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
from gameboy_agent.world_memory import file_hash
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/progression_downstream_recovery_v1_training.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def load_collection(path,summary):
 xs=[];ys=[]
 for result in summary['results']:
  if not result['success'] or not result['exact_replay']:continue
  folder=path/result['spec']['id'];manifest=json.loads((folder/'manifest.json').read_text())
  for name,expected in manifest['artifacts'].items():
   if file_hash(folder/name)!=expected:raise ValueError(f'Collection artifact changed: {folder/name}')
  data=np.load(folder/'corrections.npz');xs.append(data['x']);ys.append(data['y'])
 return np.concatenate(xs),np.concatenate(ys)
def normalize(x,saved):
 x=x.copy();n=saved['base_inputs'];x[:,:n]=(x[:,:n]-saved['mean'])/saved['scale']*saved['input_mask'];return torch.from_numpy(x)
def run(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(Path(__file__))!=plan['trainer_sha256']:raise ValueError('Frozen trainer changed')
 collection=ROOT/plan['collection'];summary=json.loads((collection/'summary.json').read_text())
 if file_hash(collection/'summary.json')!=plan['collection_summary_sha256'] or summary['successes']<summary['required_successes'] or summary['validation_loaded']:raise ValueError('Teacher gate or collection identity failed')
 x,y=load_collection(collection,summary)
 if len(x)!=plan['correction_rows']:raise ValueError('Correction row count changed')
 parent_path=ROOT/plan['parent']
 if file_hash(parent_path)!=plan['parent_sha256']:raise ValueError('Parent changed')
 saved=torch.load(parent_path,map_location='cpu');parent=DaggerNet(saved['inputs']);parent.load_state_dict(saved['model']);parent.eval()
 model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model'])
 old_summary=json.loads((ROOT/plan['retention_collection']/'summary.json').read_text());rx,_=load_collection(ROOT/plan['retention_collection'],old_summary)
 tx=normalize(x,saved);ty=torch.from_numpy(y);rtx=normalize(rx,saved)
 with torch.no_grad():retention_logits=parent(rtx)
 torch.set_num_threads(8);torch.manual_seed(plan['seed']);gen=torch.Generator().manual_seed(plan['seed']+1)
 opt=torch.optim.Adam(model.parameters(),lr=plan['learning_rate']);ce=nn.CrossEntropyLoss();history=[]
 def supervised(z,target):return ce(z[:,:5],target[:,0])+ce(z[:,5:8],target[:,1])+ce(z[:,8:],target[:,2])
 def distill(z,p):return F.kl_div(F.log_softmax(z[:,:5],1),F.softmax(p[:,:5],1),reduction='batchmean')+.25*F.kl_div(F.log_softmax(z[:,5:8],1),F.softmax(p[:,5:8],1),reduction='batchmean')+.25*F.kl_div(F.log_softmax(z[:,8:],1),F.softmax(p[:,8:],1),reduction='batchmean')
 for epoch in range(1,plan['epochs']+1):
  model.train();total=0
  for _ in range(plan['batches_per_epoch']):
   i=torch.randint(len(tx),(plan['batch_rows'],),generator=gen);r=torch.randint(len(rtx),(plan['retention_batch_rows'],),generator=gen)
   opt.zero_grad();value=supervised(model(tx[i]),ty[i])+plan['retention_weight']*distill(model(rtx[r]),retention_logits[r]);value.backward();nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();total+=float(value.detach())
  model.eval()
  with torch.no_grad():z=model(tx);metrics={'loss':float(supervised(z,ty)),'movement_accuracy':float((z[:,:5].argmax(1)==ty[:,0]).float().mean()),'button_accuracy':float((z[:,5:8].argmax(1)==ty[:,1]).float().mean()),'duration_accuracy':float((z[:,8:].argmax(1)==ty[:,2]).float().mean())}
  history.append({'epoch':epoch,'objective':total/plan['batches_per_epoch'],**metrics});print(json.dumps(history[-1]),flush=True)
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');shutil.copy2(Path(__file__),out/'trainer-source.py')
 checkpoint=out/'candidate.pt';torch.save({**saved,'model':model.state_dict(),'history':history,'parent_sha256':plan['parent_sha256']},checkpoint)
 result={'status':'trained_live_development_pending','checkpoint':str(checkpoint),'checkpoint_sha256':file_hash(checkpoint),'correction_rows':len(x),'retention_rows':len(rx),'teacher_successes':summary['successes'],'teacher_cases':summary['cases'],'validation_loaded':False,'selection':plan['selection'],'final':history[-1]};write(out/'result.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)

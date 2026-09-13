"""Fine-tune the Tail Cave specialist on both frozen integration batches."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from torch import nn
from gameboy_agent.world_memory import file_hash
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_integration_dagger_v5_training.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text());cfg=plan['model']
 for path,key in ((Path(__file__),'trainer_sha256'),(ROOT/plan['parent'],'parent_sha256'),(ROOT/plan['base_data'],'base_data_sha256')):
  if file_hash(path)!=plan[key]:raise ValueError(f'Frozen input changed: {path}')
 parts=[];collection_rows=[]
 for item in plan['collections']:
  root=ROOT/item['run'];summary=json.loads((root/'summary.json').read_text())
  if file_hash(root/'summary.json')!=item['summary_sha256'] or summary['successes']<summary['required_successes'] or summary['validation_loaded']:raise ValueError(f'Collection gate failed: {root}')
  loaded=[np.load(root/r['id']/'corrections.npz') for r in summary['results'] if r['success']];parts.extend(loaded);collection_rows.append(sum(len(p['x']) for p in loaded))
 base=np.load(ROOT/plan['base_data']);base_raw=base['x'].astype(np.float32);base_y=torch.from_numpy(base['y']);correction_raw=np.concatenate([p['x'] for p in parts]).astype(np.float32);correction_y=torch.from_numpy(np.concatenate([p['y'] for p in parts]))
 if collection_rows!=[item['rows'] for item in plan['collections']]:raise ValueError('Correction row count changed')
 saved=torch.load(ROOT/plan['parent'],map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);mean=saved['mean'];scale=saved['scale'];base_x=torch.from_numpy((base_raw-mean)/scale);correction_x=torch.from_numpy((correction_raw-mean)/scale)
 torch.set_num_threads(8);torch.manual_seed(cfg['seed']);gen=torch.Generator().manual_seed(cfg['seed']+1);opt=torch.optim.Adam(model.parameters(),lr=cfg['learning_rate']);ce=nn.CrossEntropyLoss();history=[]
 def loss(z,t):return ce(z[:,:5],t[:,0])+ce(z[:,5:8],t[:,1])+ce(z[:,8:],t[:,2])
 def accuracy(z,t):return [float((z[:,:5].argmax(1)==t[:,0]).float().mean()),float((z[:,5:8].argmax(1)==t[:,1]).float().mean()),float((z[:,8:].argmax(1)==t[:,2]).float().mean())]
 for epoch in range(1,cfg['epochs']+1):
  model.train();total=0
  for _ in range(cfg['batches_per_epoch']):
   bi=torch.randint(len(base_x),(cfg['base_rows_per_batch'],),generator=gen);ci=torch.randint(len(correction_x),(cfg['correction_rows_per_batch'],),generator=gen);x=torch.cat((base_x[bi],correction_x[ci]));y=torch.cat((base_y[bi],correction_y[ci]));opt.zero_grad();v=loss(model(x),y);v.backward();nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();total+=float(v.detach())
  model.eval()
  with torch.no_grad():
   bidx=torch.arange(min(len(base_x),cfg['report_rows']));cidx=torch.arange(min(len(correction_x),cfg['report_rows']));row={'epoch':epoch,'objective':total/cfg['batches_per_epoch'],'base_accuracy':accuracy(model(base_x[bidx]),base_y[bidx]),'correction_accuracy':accuracy(model(correction_x[cidx]),correction_y[cidx])}
  history.append(row);print(json.dumps(row),flush=True)
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');checkpoint=out/'candidate.pt';torch.save({**saved,'model':model.state_dict(),'history':history,'parent_sha256':plan['parent_sha256']},checkpoint);result={'status':'trained_autonomous_evaluation_pending','checkpoint':str(checkpoint),'checkpoint_sha256':file_hash(checkpoint),'base_rows':len(base_x),'correction_rows':len(correction_x),'total_rows':len(base_x)+len(correction_x),'final':history[-1],'validation_loaded':False};write(out/'result.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)

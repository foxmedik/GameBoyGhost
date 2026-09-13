"""Train the standalone first-trigger recovery skill only."""
import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import torch
from torch import nn

class RecoveryNet(nn.Module):
    def __init__(self, inputs, outputs=10):
        super().__init__();self.net=nn.Sequential(nn.Linear(inputs,128),nn.ReLU(),nn.Linear(128,128),nn.ReLU(),nn.Linear(128,outputs))
    def forward(self,x):return self.net(x)

def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=np.load(a.data/'skill.npz');raw,y=d['x'].astype(np.float32),d['y'];mean,scale=raw.mean(0),raw.std(0);scale[scale<1e-4]=1
 x=torch.from_numpy((raw-mean)/scale);target=torch.from_numpy(y);counts=np.bincount(y,minlength=10);weights=torch.tensor(len(y)/np.maximum(counts,1)/10,dtype=torch.float32)
 torch.manual_seed(5117);m=RecoveryNet(x.shape[1]);opt=torch.optim.Adam(m.parameters(),lr=3e-4);loss=nn.CrossEntropyLoss(weight=weights)
 history=[]
 for epoch in range(80):
  opt.zero_grad();v=loss(m(x),target);v.backward();opt.step()
  with torch.no_grad():history.append({'epoch':epoch+1,'loss':float(v),'fit_accuracy':float((m(x).argmax(1)==target).float().mean())})
 a.out.mkdir(parents=True,exist_ok=False);torch.save({'model':m.state_dict(),'inputs':x.shape[1],'mean':mean,'scale':scale,'history':history},a.out/'candidate.pt');(a.out/'result.json').write_text(json.dumps({'status':'standalone_gate_pending','rows':len(y),'final':history[-1]},indent=2)+'\n');print(json.dumps(history[-1]))
if __name__=='__main__':main()

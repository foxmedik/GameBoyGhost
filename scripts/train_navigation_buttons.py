"""Button-only ablation of the frozen selective-sword training method."""
import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256
import navigation_recovery as rec
from button_only_training import freeze_movement,assert_movement_unchanged



def action_margin_loss(z, targets, margin):
    """Require demonstrated movement/button logits to beat alternatives."""
    import torch
    penalties=[]
    for logits,labels,weight in [(z[:,:5],targets[:,0],1.0),(z[:,5:],targets[:,1],0.25)]:
        chosen=logits.gather(1,labels[:,None]).squeeze(1)
        competitors=logits.masked_fill(torch.nn.functional.one_hot(labels,logits.shape[1]).bool(),float('-inf')).max(1).values
        penalties.append(weight*torch.relu(margin+competitors-chosen).mean())
    return sum(penalties)


def train(out):
    import torch
    from gameboy_agent.navigation import NavigationNet
    out=Path(out);plan=json.loads((out/'plan.json').read_text());parent=Path(plan['parent'])
    assert sha256(parent)==plan['parent_sha256']
    assert sha256(ROOT/'scripts/button_only_training.py')==plan['button_helper_sha256']
    torch.set_num_threads(8);torch.manual_seed(2027)
    s=torch.load(parent,map_location='cpu');model=NavigationNet(s['inputs']);model.load_state_dict(s['model']);model.eval()
    frozen_movement=freeze_movement(model)
    normalize=lambda x:torch.from_numpy((x-s['mean'])/s['scale']*s['input_mask'])
    selected={};labels={};entry_keys=set();raw=0;path_count=0
    for manifest in sorted((out/'data').glob('*/manifest.json')):
        m=json.loads(manifest.read_text());assert m['replay_verified'] and m['policy_sha256'] in plan.get('allowed_collection_policies',[plan['parent_sha256']])
        for a in m['paths']:
            p=manifest.parent/a['file'];assert a['replay_verified'] and sha256(p)==a['sha256']
            d=np.load(p);assert np.array_equal(d['y'],a['actions']);raw+=len(d['y']);path_count+=1
            for i,(x,y) in enumerate(zip(d['x'],d['y'])):
                key=(x*s['input_mask']).tobytes();cost=len(d['y'])-i
                labels.setdefault(key,set()).add(tuple(y))
                if plan.get('recovery_entry_group') and p.parent.name.startswith(plan['recovery_entry_group']) and i<plan['recovery_entry_rows']:entry_keys.add(key)
                if key not in selected or cost<selected[key]['cost']:
                    selected[key]=dict(x=x,y=y,cost=cost,path=str(p.resolve()),row=i,source_sha256=a['sha256'])
    for key,value in selected.items():value['recovery_entry']=key in entry_keys
    values=list(selected.values());assert values
    focus_indices=[i for i,v in enumerate(values) if plan.get('focus_path_fragment') and plan['focus_path_fragment'] in v['path']]
    groups=[[i for i,v in enumerate(values) if Path(v['path']).parent.name.startswith(prefix)] for prefix in plan.get('balanced_path_groups',[])]
    if groups:assert all(groups),'Every correction group must have verified examples'
    fx=normalize(np.stack([v['x'] for v in values]));fy=torch.from_numpy(np.stack([v['y'] for v in values]))
    bm=json.loads((rec.BASE_CACHE/'manifest.json').read_text());assert sha256(rec.BASE_CACHE/'train-x.npy')==bm['artifacts']['train-x.npy']
    base=normalize(np.load(rec.BASE_CACHE/'train-x.npy'))
    other=[];artifacts={}
    for folder in ('navigation-live-correction-v3','navigation-focused-v4'):
        for p in sorted((ROOT/'runs'/folder/'data').glob('*/success-*.npz')):
            m=json.loads((p.parent/'manifest.json').read_text());assert m['replay_verified'] and sha256(p)==m['artifacts'][p.name]
            other.append(np.load(p)['x']);artifacts[str(p)]=sha256(p)
    if plan.get('retention_route_data'):
        for manifest in sorted(Path(plan['retention_route_data']).glob('*/manifest.json')):
            m=json.loads(manifest.read_text());assert m['replay_verified']
            for a in m['paths']:
                p=manifest.parent/a['file'];assert a['replay_verified'] and sha256(p)==a['sha256']
                other.append(np.load(p)['x']);artifacts[str(p)]=sha256(p)
    rx=normalize(np.concatenate(other))
    with torch.no_grad():bl=torch.cat([model(c) for c in base.split(4096)]);rl=torch.cat([model(c) for c in rx.split(4096)])
    dest=out/'model';dest.mkdir(exist_ok=False)
    metadata=dict(plan=plan,verified_paths=path_count,raw_route_rows=raw,target_unique_states=len(fx),conflicting_states=sum(len(v)>1 for v in labels.values()),
        target_provenance=[{k:v for k,v in a.items() if k not in ('x','y')} for a in values],
        retention_rows=len(base),retention_demonstration_rows=len(rx),retention_artifacts=artifacts,
        source_sha256=sha256(__file__),torch_version=torch.__version__,numpy_version=np.__version__)
    (out/'training-plan.json').write_text(json.dumps(metadata,indent=2));shutil.copy2(__file__,dest/'train_navigation_buttons.py')
    optimizer=torch.optim.Adam(model.parameters(),lr=plan['learning_rate']);g=torch.Generator().manual_seed(2027);ce=torch.nn.CrossEntropyLoss();history=[]
    for epoch in range(1,plan['epochs']+1):
        model.train();total=0;count=0
        for idx in torch.randperm(len(base),generator=g).split(1536):
            ri=torch.randint(len(rx),(512,),generator=g);ti=torch.randint(len(fx),(256,),generator=g)
            if groups:
                chunks=[]
                for group_index,group in enumerate(groups):
                    gi=torch.tensor(group);size=plan.get('group_batch_sizes',[256//len(groups)]*len(groups))[group_index]
                    weights=torch.ones(len(group))
                    if plan['balanced_path_groups'][group_index]==plan.get('recovery_entry_group'):
                        weights=torch.tensor([float(plan['recovery_entry_weight']) if values[i]['recovery_entry'] else 1.0 for i in group])
                    chunks.append(gi[torch.multinomial(weights,size,replacement=True,generator=g)])
                ti=torch.cat(chunks)
            if focus_indices:
                fi=torch.tensor(focus_indices);ti[:128]=fi[torch.randint(len(fi),(128,),generator=g)]
            optimizer.zero_grad();retain=rec.parent_divergence(model(base[idx]),bl[idx])+rec.parent_divergence(model(rx[ri]),rl[ri])
            z=model(fx[ti]);loss=ce(z[:,:5],fy[ti,0])+.25*ce(z[:,5:],fy[ti,1])+plan['retention_weight']*retain
            if plan.get('action_margin_weight'):
                loss=loss+plan['action_margin_weight']*action_margin_loss(z,fy[ti],plan['action_margin'])
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step();assert_movement_unchanged(model,frozen_movement);total+=float(loss.detach());count+=1
        history.append(dict(epoch=epoch,loss=total/count,movement_weights_exactly_preserved=True));print(json.dumps(history[-1]),flush=True)
        p=dest/f'epoch-{epoch:03}.pt';torch.save({**s,'model':model.state_dict(),'optimizer':optimizer.state_dict(),'epoch':epoch,'history':history,'shuffle_rng':g.get_state(),'torch_rng':torch.get_rng_state(),'route_plan':metadata},p)
        p.with_suffix('.json').write_text(json.dumps(dict(sha256=sha256(p),identity=metadata),indent=2))
    (dest/'history.json').write_text(json.dumps(history,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);train(p.parse_args().out)

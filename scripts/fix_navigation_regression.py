"""Focused regression correction using shortest verified continuations."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import navigation_recovery as rec
from gameboy_agent.dataset import sha256
PARENT=ROOT/'runs/navigation-live-correction-v3/model/epoch-012.pt'
TARGET='7ca8327a89569c1600002a6c5953fd39b8e34a98039d425d862eceb99db53944'


def collect(out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True);data=out/'data';data.mkdir()
    item=json.loads((ROOT/'runs/navigation-live-correction-v3/remaining-regressions.json').read_text())[0]
    case=item['case'];trace=json.loads((ROOT/item['candidate_trace']).read_text())
    original=json.loads((ROOT/f'runs/navigation-live-no-history-v1/{TARGET}-learned.json').read_text())
    first=next(i for i,(a,b) in enumerate(zip(trace['actions'],original['actions'])) if a!=b)
    jobs=[]
    for position in sorted({0,first,first+8,96}):
        c={**case,'segment_id':f'focused-{TARGET}-{position}','replay_extra':trace['actions'][:position],
           'parent_teacher':True,'success_cap':4,'rollout_policy':str(PARENT)}
        jobs.append((c,0,str(data)))
    plan=dict(target=case,first_divergence=first,positions=[len(j[0]['replay_extra']) for j in jobs],
        parent_sha256=sha256(PARENT),collector_sha256=sha256(ROOT/'scripts/navigation_recovery.py'),source_sha256=sha256(__file__),
        epochs=8,learning_rate=1e-5,retention_KL_weight=8,
        selection='Fixed final epoch; no new development examples added to training beyond the already retired target cohort.',
        gate='No original parent or v3 successes lost across all three known panels; zero damage/deaths; 3/3 continuous success without damage.',reserved_evaluation_used=False)
    (out/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,out/'fix_navigation_regression.py');shutil.copy2(ROOT/'scripts/navigation_recovery.py',out/'navigation_recovery.py')
    with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('spawn')) as pool:
        results=list(pool.map(rec.collect_job,jobs))
    assert all(r['successes'] for r in results)
    (out/'collection.json').write_text(json.dumps(results,indent=2));print(json.dumps(results),flush=True)


def shortest_labels(paths,mask):
    """For repeated model-visible states, prefer the shortest observed suffix.

    No optimality claim: costs are observed actions-to-go in verified paths.
    Deterministic path/row ordering breaks ties. Every label retains provenance.
    """
    selected={};conflicts=set();labels={}
    for p in sorted(paths):
        m=json.loads((p.parent/'manifest.json').read_text());assert m['replay_verified'] and sha256(p)==m['artifacts'][p.name]
        d=np.load(p);index=int(p.stem.split('-')[-1]);accepted=m['successes'][index]
        attempt=next(a for a in m['attempts'] if a['attempt']==accepted['attempt'])
        assert attempt['success'] and attempt['damage']==0
        assert np.array_equal(d['y'],accepted['actions'])
        for i,(x,y) in enumerate(zip(d['x'],d['y'])):
            key=(x*mask).tobytes();cost=len(d['y'])-i
            labels.setdefault(key,set()).add(tuple(y))
            if len(labels[key])>1:conflicts.add(key)
            if key not in selected or cost<selected[key]['cost']:
                selected[key]=dict(x=x,y=y,cost=cost,path=str(p.resolve()),row=i,source_sha256=sha256(p))
    values=list(selected.values())
    return np.stack([v['x'] for v in values]),np.stack([v['y'] for v in values]),[{k:v for k,v in item.items() if k not in ['x','y']} for item in values],len(conflicts)


def train(out):
    import torch
    from gameboy_agent.navigation import NavigationNet
    out=Path(out);plan=json.loads((out/'plan.json').read_text());assert sha256(PARENT)==plan['parent_sha256']
    torch.set_num_threads(8);torch.manual_seed(2027)
    s=torch.load(PARENT,map_location='cpu');model=NavigationNet(s['inputs']);model.load_state_dict(s['model']);model.eval()
    normalize=lambda x:torch.from_numpy((x-s['mean'])/s['scale']*s['input_mask'])
    old=ROOT/'runs/navigation-live-correction-v3/data'
    target_paths=list(old.glob('*'+TARGET+'*/success-*.npz'))+list((out/'data').glob('*/success-*.npz'))
    tx,ty,provenance,conflicts=shortest_labels(target_paths,s['input_mask']);fx=normalize(tx);fy=torch.from_numpy(ty)
    bm=json.loads((rec.BASE_CACHE/'manifest.json').read_text());assert sha256(rec.BASE_CACHE/'train-x.npy')==bm['artifacts']['train-x.npy']
    base=normalize(np.load(rec.BASE_CACHE/'train-x.npy'))
    other=[];artifacts={}
    for p in sorted(old.glob('*/success-*.npz')):
        if TARGET in str(p):continue
        m=json.loads((p.parent/'manifest.json').read_text());assert sha256(p)==m['artifacts'][p.name]
        other.append(np.load(p)['x']);artifacts[str(p)]=sha256(p)
    rx=normalize(np.concatenate(other))
    with torch.no_grad():bl=torch.cat([model(c) for c in base.split(4096)]);rl=model(rx)
    dest=out/'model';dest.mkdir(exist_ok=False)
    metadata=dict(plan=plan,target_unique_states=len(fx),conflicting_states=conflicts,target_provenance=provenance,
        retention_rows=len(base),retention_demonstration_rows=len(rx),retention_artifacts=artifacts,
        source_sha256=sha256(__file__),torch_version=torch.__version__,numpy_version=np.__version__)
    (out/'training-plan.json').write_text(json.dumps(metadata,indent=2));shutil.copy2(__file__,dest/'fix_navigation_regression.py')
    optimizer=torch.optim.Adam(model.parameters(),lr=plan['learning_rate']);g=torch.Generator().manual_seed(2027);ce=torch.nn.CrossEntropyLoss();history=[]
    for epoch in range(1,plan['epochs']+1):
        model.train();total=0;count=0
        for idx in torch.randperm(len(base),generator=g).split(1536):
            ri=torch.randint(len(rx),(512,),generator=g);ti=torch.randint(len(fx),(256,),generator=g)
            optimizer.zero_grad();retain=rec.parent_divergence(model(base[idx]),bl[idx])+rec.parent_divergence(model(rx[ri]),rl[ri])
            z=model(fx[ti]);loss=ce(z[:,:5],fy[ti,0])+.25*ce(z[:,5:],fy[ti,1])+plan['retention_KL_weight']*retain
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step();total+=float(loss.detach());count+=1
        history.append(dict(epoch=epoch,loss=total/count));print(json.dumps(history[-1]),flush=True)
        p=dest/f'epoch-{epoch:03}.pt';torch.save({**s,'model':model.state_dict(),'optimizer':optimizer.state_dict(),'epoch':epoch,'history':history,'shuffle_rng':g.get_state(),'torch_rng':torch.get_rng_state(),'focused_plan':metadata},p)
        p.with_suffix('.json').write_text(json.dumps(dict(sha256=sha256(p),identity=metadata),indent=2))
    (dest/'history.json').write_text(json.dumps(history,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['collect','train']);p.add_argument('--out',type=Path,required=True);a=p.parse_args();(collect if a.mode=='collect' else train)(a.out)

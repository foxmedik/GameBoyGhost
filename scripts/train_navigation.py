"""Balanced hindsight data cache and deterministic resumable behavior cloning."""
import argparse
from collections import defaultdict,Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import pyarrow.parquet as pq
import torch
from gameboy_agent.dataset import sha256,unpack_observation
from gameboy_agent.curation import stable_hash
from gameboy_agent.navigation import encode,NavigationNet


def sampled_steps(segment):
    a,b=segment['step_start'],segment['step_end']
    return [begin+int(stable_hash([segment['segment_id'],begin])[:8],16)%min(4,b-begin)
            for begin in range(a,b,4)]


def build_cache(curated,out):
    curated=Path(curated).resolve();out=Path(out).resolve()
    manifest=json.loads((curated/'manifest.json').read_text());batch=Path(manifest['source_batch'])
    out.mkdir(parents=True,exist_ok=False)
    selections={};sources=defaultdict(list);counts={}
    for split,cap in [('train',1536),('dev',192)]:
        path=curated/split/'hindsight_navigation.parquet'
        if sha256(path)!=manifest['artifacts'][str(path.relative_to(curated))]:raise ValueError('Curated index mismatch')
        groups=defaultdict(list)
        for row in pq.read_table(path).to_pylist():groups[(row['start'],tuple(row['target_room']))].append(row)
        selected=[]
        for key,items in sorted(groups.items()):
            selected.extend(sorted(items,key=lambda r:stable_hash(r['segment_id']))[:cap])
        selections[split]=selected;counts[split]={'segments':len(selected),'strata':{str(k):min(len(v),cap) for k,v in groups.items()}}
        for row in selected:sources[row['source_path']].append((split,row))
    data={s:dict(x=[],y=[]) for s in selections};case_candidates=[]
    def process(item):
        path,segments=item;source=batch/path
        if sha256(source)!=segments[0][1]['source_sha256']:raise ValueError('Raw source mismatch')
        meta=json.loads((source.parent/'manifest.json').read_text())
        t=pq.read_table(source,columns=['observation','room','x','y','action']).to_pydict()
        result={s:dict(x=[],y=[]) for s in selections};cases=[]
        for split,row in segments:
            a,b=row['step_start'],row['step_end'];goal=dict(room=row['target_room'],x=row['target_x'],y=row['target_y'])
            for step in sampled_steps(row):
                obs=unpack_observation(t['observation'][step],meta['observation_layout'])
                result[split]['x'].append(encode(obs,t['room'][step],goal['room'],goal['x'],goal['y']))
                result[split]['y'].append(t['action'][step])
            if split=='dev':
                cases.append(dict(segment_id=row['segment_id'],episode_id=meta['episode_id'],source_path=path,
                    source_sha256=row['source_sha256'],start=meta['start'],seed=meta['seed'],step=a,
                    goal=goal,initial_room=t['room'][a],initial_x=t['x'][a],initial_y=t['y'][a],
                    kind='same_room' if t['room'][a]==goal['room'] else 'cross_room'))
        return result,cases
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,(result,cases) in enumerate(pool.map(process,sorted(sources.items()))):
            for split in data:
                data[split]['x'].extend(result[split]['x']);data[split]['y'].extend(result[split]['y'])
            case_candidates.extend(cases)
            if (i+1)%500==0:print('CACHE',i+1,len(sources),flush=True)
    for split in data:
        np.save(out/f'{split}-x.npy',np.stack(data[split]['x']))
        np.save(out/f'{split}-y.npy',np.asarray(data[split]['y'],dtype=np.int64))
        counts[split]['rows']=len(data[split]['x'])
    # Freeze live-development cases before any optimizer update. One case per
    # source episode, balanced over starts and same/cross-room goals.
    used=set();cases=[]
    for start in ('house','beach','approach'):
        for kind in ('same_room','cross_room'):
            options=sorted((c for c in case_candidates if c['start']==start and c['kind']==kind),key=lambda c:stable_hash(c['segment_id']))
            accepted=0
            for case in options:
                if case['episode_id'] in used:continue
                if case['initial_room']==case['goal']['room'] and abs(case['initial_x']-case['goal']['x'])+abs(case['initial_y']-case['goal']['y'])<=8:continue
                used.add(case['episode_id']);cases.append(case);accepted+=1
                if accepted==8:break
    (out/'live-dev-cases.json').write_text(json.dumps(cases,indent=2))
    info=dict(schema='navigation-cache-v1',curated=str(curated),source_batch=str(batch),counts=counts,
              sampling='up to 1536 train / 192 dev segments per (base start,target room); one deterministic hashed offset in each four-action stratum',
              live_dev_cases=len(cases),frozen_evaluation_used=False,
              curated_manifest_sha256=sha256(curated/'manifest.json'),
              sources={str(p.relative_to(ROOT)):sha256(p) for p in (Path(__file__),ROOT/'src/gameboy_agent/navigation.py')},
              artifacts={p.name:sha256(p) for p in out.iterdir()})
    (out/'manifest.json').write_text(json.dumps(info,indent=2));print(json.dumps(info),flush=True)


def fit(cache,out,*,epochs=12,seed=0,stop_after=None,resume=None,no_movement_history=False):
    cache=Path(cache);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(8);torch.manual_seed(seed)
    import shutil
    (out/'sources').mkdir(exist_ok=True)
    for source in (Path(__file__),ROOT/'src/gameboy_agent/navigation.py'):
        target=out/'sources'/source.name
        if not target.exists():shutil.copy2(source,target)
    metadata=json.loads((cache/'manifest.json').read_text())
    for name,h in metadata['artifacts'].items():
        if sha256(cache/name)!=h:raise ValueError('Feature cache mismatch')
    x=np.load(cache/'train-x.npy');y=torch.from_numpy(np.load(cache/'train-y.npy'))
    dx=np.load(cache/'dev-x.npy');dy=torch.from_numpy(np.load(cache/'dev-y.npy'))
    mean=x.mean(axis=0);scale=np.maximum(x.std(axis=0),.05)
    mask=np.ones(x.shape[1],dtype=np.float32)
    if no_movement_history:mask[3]=0
    tx=torch.from_numpy((x-mean)/scale*mask);vx=torch.from_numpy((dx-mean)/scale*mask)
    model=NavigationNet(x.shape[1]);optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
    generator=torch.Generator().manual_seed(seed+1234);history=[];start=0
    identity=dict(cache_manifest=sha256(cache/'manifest.json'),epochs=epochs,seed=seed,no_movement_history=no_movement_history,
                  torch_version=torch.__version__,numpy_version=np.__version__,
                  model_source=sha256(ROOT/'src/gameboy_agent/navigation.py'),trainer_source=sha256(Path(__file__)))
    if resume:
        resume=Path(resume);check=json.loads(resume.with_suffix('.json').read_text())
        if check['sha256']!=sha256(resume) or check['identity']!=identity:raise ValueError('Checkpoint identity/integrity mismatch')
        state=torch.load(resume,map_location='cpu');model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer'])
        generator.set_state(state['shuffle_rng']);torch.set_rng_state(state['torch_rng']);history=state['history'];start=state['epoch']
    loss_fn=torch.nn.CrossEntropyLoss()
    def loss(logits,labels):return loss_fn(logits[:,:5],labels[:,0])+.25*loss_fn(logits[:,5:],labels[:,1])
    def evaluate():
        model.eval();total=correct=buttons=0
        with torch.no_grad():
            for a in range(0,len(vx),4096):
                logits=model(vx[a:a+4096]);labels=dy[a:a+4096]
                total+=float(loss(logits,labels))*len(labels)
                correct+=int((logits[:,:5].argmax(1)==labels[:,0]).sum())
                buttons+=int((logits[:,5:].argmax(1)==labels[:,1]).sum())
        return dict(dev_loss=total/len(vx),movement_accuracy=correct/len(vx),button_accuracy=buttons/len(vx))
    for epoch in range(start,min(epochs,stop_after or epochs)):
        began=time.monotonic();model.train();total=0
        for idx in torch.randperm(len(tx),generator=generator).split(2048):
            optimizer.zero_grad();value=loss(model(tx[idx]),y[idx]);value.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step();total+=float(value.detach())*len(idx)
        history.append(dict(epoch=epoch+1,train_loss=total/len(tx),seconds=time.monotonic()-began,**evaluate()))
        destination=out/f'epoch-{epoch+1:03}.pt'
        if destination.exists():raise FileExistsError(destination)
        torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),inputs=x.shape[1],mean=mean,scale=scale,input_mask=mask,
                        shuffle_rng=generator.get_state(),torch_rng=torch.get_rng_state(),epoch=epoch+1,history=history),destination)
        destination.with_suffix('.json').write_text(json.dumps(dict(sha256=sha256(destination),identity=identity),indent=2))
        (out/'history.json').write_text(json.dumps(history,indent=2));print(json.dumps(history[-1]),flush=True)
    best=min(history,key=lambda r:r['dev_loss'])
    (out/'selection.json').write_text(json.dumps(dict(epoch=best['epoch'],criterion='minimum grouped-development action loss; live evaluation still required',
                    checkpoint=str((out/f'epoch-{best["epoch"]:03}.pt').resolve()),history=history),indent=2))
    return model,optimizer,history


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['cache','train']);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--curated',type=Path,default=ROOT/'data/curated/ladx-navigation-v1');p.add_argument('--out',type=Path)
    p.add_argument('--epochs',type=int,default=12);p.add_argument('--seed',type=int,default=0);p.add_argument('--stop-after',type=int);p.add_argument('--resume',type=Path)
    p.add_argument('--no-movement-history',action='store_true')
    a=p.parse_args()
    if a.mode=='cache':build_cache(a.curated,a.cache)
    else:
        if a.out is None:p.error('--out required for training')
        fit(a.cache,a.out,epochs=a.epochs,seed=a.seed,stop_after=a.stop_after,resume=a.resume,no_movement_history=a.no_movement_history)

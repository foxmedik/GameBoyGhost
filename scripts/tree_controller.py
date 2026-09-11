"""Interpretable imitation-learning comparator on existing structured inputs."""
import json
from pathlib import Path
import sys
import numpy as np
from stable_baselines3 import PPO
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from control_context import ControlContext
from gameboy_agent.checkpoint import digest

def features(obs):
    control=obs['control'];shape=control.shape[:-1]
    return np.concatenate((control,obs['vector'][...,3:7],
                           obs['entity_type'],obs['entity_info'].reshape(*shape,64)),axis=-1)

def fit_tree(x,y,depth=0):
    counts=np.bincount(y,minlength=20);winner=int(counts.argmax())
    if depth>=48 or len(y)<2 or counts[winner]==len(y):return {'action':winner,'n':len(y)}
    best=None
    for feature in range(x.shape[1]):
        order=np.argsort(x[:,feature],kind='stable');v=x[order,feature];labels=y[order]
        cumulative=np.cumsum(np.eye(20,dtype=np.int32)[labels],axis=0)[:-1]
        left=np.arange(1,len(y));right=len(y)-left
        score=(cumulative*cumulative).sum(axis=1)/left+((counts-cumulative)**2).sum(axis=1)/right
        valid=(v[:-1]<v[1:]) & (left>=1) & (right>=1)
        if not valid.any():continue
        score[~valid]=-np.inf;index=int(score.argmax())
        if best is None or score[index]>best[0]:best=(float(score[index]),feature,float((v[index]+v[index+1])/2))
    if best is None:return {'action':winner,'n':len(y)}
    _,f,t=best;mask=x[:,f]<=t
    return {'feature':f,'threshold':t,'left':fit_tree(x[mask],y[mask],depth+1),'right':fit_tree(x[~mask],y[~mask],depth+1)}

def predict(tree,x):
    while 'action' not in tree:tree=tree['left'] if x[tree['feature']]<=tree['threshold'] else tree['right']
    return np.array([tree['action']//4,tree['action']%4])

def evaluate(tree,out):
    rows=[]
    for i,(start,setup) in enumerate([('house',[]),('house',[[3,0]]),('house',[[3,0]]*2),('beach',[]),('approach',[])]):
        env=ControlContext(environment(out/f'eval-{i}',start));trace=[]
        try:
            obs,_=env.reset(seed=20000+i)
            for action in setup:obs,_,_,_,_=env.step(np.asarray(action))
            for step in range(1600):
                action=predict(tree,features(obs));m=env.unwrapped.pyboy.memory
                trace.append({'action':action.tolist(),'x':int(m[0xFF98]),'y':int(m[0xFF99]),'room':[int(m[a]) for a in (0xDBA5,0xFFF7,0xFFF6)]})
                obs,_,done,truncated,info=env.step(action)
                if done or truncated:break
            rows.append({'start':start,'setup_actions':setup,'success':info['sword_acquired'],'steps':step+1})
        finally:env.close()
        write(out/f'eval-{i}-trace.json',trace)
    write(out/'evaluation.json',{'teacher_active':False,'episodes':rows});print(rows,flush=True)

if __name__=='__main__':
    source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
    d=np.load(source);x=features(d);y=d['actions'][:,0]*4+d['actions'][:,1]
    tree=fit_tree(x,y);write(out/'policy.json',tree)
    write(out/'provenance.json',{'supervision':'decision_tree_behavior_cloning','source':str(source),'sha256':digest(source),
          'features':['pixel_x','pixel_y','dialog_state','previous_movement','previous_button','map_x','map_y','map_z','health'],
          'feature_contract':'control_world_entity_v2','feature_count':int(x.shape[1]),
          'harness_privilege':'D','teacher_active_at_evaluation':False})
    evaluate(tree,out)

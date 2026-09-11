"""Frozen final-epoch learned sword and preservation evaluation against v7."""
import json,sys,shutil,tempfile,subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256,pack_observation
from terrain_sword import inputs,reachable_terrain
from proximity_sword import THREATS
OUT=ROOT/'runs/navigation-routes-v9'
READ=lambda p:json.loads(Path(p).read_text())
def trial(args):
 import torch,pyarrow.parquet as pq
 import gameboy_agent.training_env as training
 from gameboy_agent.navigation import reached,NavigationController
 from gameboy_agent.checkpoint import fingerprint
 from control_context import ControlContext
 from run_skill_chain import senses
 torch.set_num_threads(1)
 case,variant,batch,dest,checkpoint=args;policy=NavigationController(checkpoint);source=Path(batch)/case['source_path'];meta=json.loads((source.parent/'manifest.json').read_text());assert sha256(source)==case['source_sha256']
 trace=pq.read_table(source,columns=['action','observation']).to_pydict();prefix=trace['action'][:case['step']]
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(Path(batch)/'assets/game.gbc',rom)
  def restore(actions):
   base=training.TrainingEnv(rom,Path(batch)/'assets'/f'{meta["start"]}.state',max_steps=meta['max_steps'],sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=meta['seed'])
   for a in prefix:obs,_,_,_,_=env.step(np.asarray(a))
   assert pack_observation(obs,meta['observation_layout'])==trace['observation'][case['step']]
   base.config['max_steps']=base.total_steps+129
   for a in actions:obs,_,_,_,_=env.step(np.asarray(a))
   return base,env,obs
  base,env,obs=restore([]);initial=fingerprint(base);actions=[];events=[];frame_events=[];damage=0;status='timeout';swings=0;frames=0;presses=0;types=set()
  original=training.advance
  class Tap:
   def __init__(self,boy):self.boy=boy
   def __getattr__(self,n):return getattr(self.boy,n)
   def tick(self,*a,**kw):
    nonlocal swings,frames
    before=int(self.boy.memory[0xC137]);health=int(self.boy.memory[0xDB5A]);value=self.boy.tick(*a,**kw);after=int(self.boy.memory[0xC137]);frames+=1
    started=before not in (1,2,3,4) and after in (1,2,3,4);swings+=int(started)
    if started or health!=int(self.boy.memory[0xDB5A]):frame_events.append(dict(frame=frames,step=len(actions),swing_start=started,health_before=health,health_after=int(self.boy.memory[0xDB5A]),x=int(self.boy.memory[0xFF98]),y=int(self.boy.memory[0xFF99]),facing=int(self.boy.memory[0xFF9E])))
    return value
  def tapped(boy,tracker,pressed,**kw):return original(Tap(boy),tracker,pressed,**kw)
  training.advance=tapped
  try:
   for step in range(128):
    s=senses(base);proposed=policy.action(obs,s.room,case['goal']);info=inputs(base);types.update(e['type'] for e in info['entities']);button=1 if s.a_item==1 else 2 if s.b_item==1 else 0
    action,reason=proposed,'learned'
    presses+=int(bool(button) and action[1]==button and not s.dialogue)
    obs,_,done,truncated,_=env.step(np.asarray(action));after=senses(base);loss=max(0,s.health-after.health);damage+=loss;actions.append(action)
    terrain=reachable_terrain(**{k:info[k] for k in ('x','y','facing','indoor','objects','physics','cutting_blocked')},movement=proposed[0])
    events.append(dict(state=s.__dict__,after_state=after.__dict__,inputs=info,terrain_target=terrain,frames=base.last_timing,step=step,proposed=proposed,action=action,reason=reason,damage=loss,sword_state=info['sword_state'],near_threats=sum(e['type'] in THREATS and (e['x']-s.x)**2+(e['y']-s.y)**2<=32**2 for e in info['entities'])))
    if after.health==0:status='death';break
    if reached(after.room,after.x,after.y,case['goal']):status='success';break
    if done or truncated:status='environment_end';break
   final=fingerprint(base);final_state=senses(base).__dict__
  finally:training.advance=original;env.close()
  base,env,obs=restore(actions)
  try:assert fingerprint(base)==final
  finally:env.close()
  result=dict(case_id=case['segment_id'],variant=variant,start=case['start'],kind=case['kind'],status=status,success=status=='success',steps=len(actions),damage=damage,actual_swing_starts=swings,sword_press_actions=presses,frames=frames,
   start_fingerprint=initial,final_fingerprint=final,final_state=final_state,observed_entity_types=sorted(types),replay_verified=True,actions=actions,events=events,frame_events=frame_events)
  (Path(dest)/f'{case["segment_id"]}-{variant}.json').write_text(json.dumps(result,indent=2))
  return {k:v for k,v in result.items() if k not in ('actions','events','frame_events','final_state')}


def command(args,log):
 with Path(log).open('x') as f:subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)

def replay_run(folder):
 from gameboy_agent.training_env import TrainingEnv
 from gameboy_agent.checkpoint import fingerprint
 from control_context import ControlContext
 import torch
 torch.set_num_threads(1);folder=Path(folder);r=READ(folder/'result.json');m=READ(folder/'manifest.json')
 for name,h in m['artifacts'].items():assert sha256(folder/name)==h
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom)
  base=TrainingEnv(rom,folder/'initial.state',max_steps=1600+r['budget']*(len(r['route']['goals']) if 'route' in r else 1)+1,sword_curriculum=False);env=ControlContext(base)
  try:
   env.reset(seed=0)
   for a in r['actions']:env.step(np.asarray(a))
   assert fingerprint(base)==r['fingerprint']
  finally:env.close()
 return dict(run=str(folder.relative_to(ROOT)),fingerprint=r['fingerprint'],replay_verified=True)

def main():
 plan=READ(OUT/'plan.json');model=OUT/'model/epoch-008.pt';parent=Path(plan['parent'])
 assert sha256(model)==READ(model.with_suffix('.json'))['sha256']
 assert sha256(parent)==plan['parent_sha256']
 for p,h in plan['baseline_hashes'].items():assert sha256(ROOT/p)==h
 assert sha256(ROOT/'scripts/train_navigation_routes.py')==plan['trainer_sha256']
 panels={'original':ROOT/'runs/navigation-cache-v2','additional':ROOT/'runs/navigation-recovery-dev-v1','fresh':ROOT/'runs/navigation-live-correction-v3/fresh-panel'}
 jobs=[];case_panels={};baseline_local={}
 for name,cache in panels.items():
  meta=READ(cache/'manifest.json');assert sha256(cache/'live-dev-cases.json')==meta['artifacts']['live-dev-cases.json']
  cases=READ(cache/'live-dev-cases.json');assert len(cases)==48;case_panels[name]=cases
  dest=OUT/f'eval-{name}';dest.mkdir(exist_ok=False)
  baseline_local[name]=READ(ROOT/f'runs/navigation-routes-v7/eval-{name}/result.json')
  for c in cases:
   for variant in (['v7','candidate'] if name=='original' else ['candidate']):
    jobs.append((c,variant,meta['source_batch'],str(dest),str(parent if variant=='v7' else model)))
 ep=dict(training_plan_sha256=sha256(OUT/'plan.json'),candidate_sha256=sha256(model),parent_sha256=sha256(parent),panels=case_panels,
  local_rollouts=192,original_paired_sword_rollouts=96,local_budget=128,route_budget=256,
  gates=plan['selection'],sword_gate=plan['additional_sword_evaluation'],reserved_evaluation_used=False,
  source_sha256=sha256(__file__),diagnostic_only_terrain_inputs=True,
  evaluation_sources={str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'scripts/run_navigation_route.py',ROOT/'scripts/run_navigation_chain.py',ROOT/'scripts/route_progress.py',ROOT/'scripts/terrain_sword.py',ROOT/'scripts/proximity_sword.py']},
  baseline_reports={str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/f'runs/navigation-routes-v7/eval-{n}/result.json' for n in panels]})
 (OUT/'evaluation-plan.json').write_text(json.dumps(ep,indent=2));shutil.copy2(__file__,OUT/'evaluation_source.py')
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for r in pool.map(trial,jobs):
   results.append(r)
   if len(results)%12==0:print('LOCAL_VERIFIED',len(results),len(jobs),flush=True)
 local={}
 for name,cases in case_panels.items():
  ids={c['segment_id'] for c in cases};now=[r for r in results if r['variant']=='candidate' and r['case_id'] in ids]
  old={r['case_id']:r for r in baseline_local[name]['episodes'] if r['agent']=='learned'}
  for r in now:assert r['start_fingerprint']==old[r['case_id']]['start_fingerprint']
  local[name]=dict(cases=48,successes=sum(r['success'] for r in now),baseline_successes=sum(r['success'] for r in old.values()),damage=sum(r['damage'] for r in now),deaths=sum(r['status']=='death' for r in now),lost=[r['case_id'] for r in now if old[r['case_id']]['success'] and not r['success']],gained=[r['case_id'] for r in now if not old[r['case_id']]['success'] and r['success']],episodes=now)
  (OUT/f'eval-{name}/result.json').write_text(json.dumps(local[name],indent=2))
 before=[r for r in results if r['variant']=='v7'];ids={r['case_id'] for r in before};after=[r for r in results if r['variant']=='candidate' and r['case_id'] in ids]
 pairs=[]
 for a in before:
  b=next(r for r in after if r['case_id']==a['case_id']);historical=next(r for r in baseline_local['original']['episodes'] if r['agent']=='learned' and r['case_id']==a['case_id'])
  assert a['final_fingerprint']==historical['final_fingerprint'] and a['start_fingerprint']==b['start_fingerprint']
  pairs.append(dict(case_id=a['case_id'],lost=a['success'] and not b['success'],damage_delta=b['damage']-a['damage'],new_death=b['status']=='death' and a['status']!='death',swings_delta=b['actual_swing_starts']-a['actual_swing_starts']))
 sword={v:{k:sum(r[k] for r in rr) for k in ['success','steps','damage','actual_swing_starts','sword_press_actions','frames']} for v,rr in [('v7',before),('candidate',after)]}
 (OUT/'sword-result.json').write_text(json.dumps(dict(summary=sword,pairs=pairs),indent=2));print('LOCAL_RESULTS',json.dumps({n:{k:v for k,v in r.items() if k!='episodes'} for n,r in local.items()}),flush=True);print('SWORD_RESULTS',json.dumps(sword),flush=True)
 route_specs=[(r,s) for r in plan['curriculum']['routes'] for s in plan['curriculum']['starts']]
 (OUT/'candidate').mkdir(exist_ok=False)
 def route_job(spec):
  r,start=spec;dest=OUT/'candidate'/f"{r['id']}-{start}"
  command(['scripts/run_navigation_route.py','--checkpoint',model,'--route-id',r['id'],'--curriculum',OUT/'curriculum.json','--start',start,'--out',dest],dest.with_suffix('.log'))
  return dest
 with ThreadPoolExecutor(max_workers=8) as pool:folders=list(pool.map(route_job,route_specs))
 def chain_job(start):
  dest=OUT/f'chain-{start}';command(['scripts/run_navigation_chain.py','--checkpoint',model,'--goal','0','0','226','36','121','--start',start,'--out',dest],dest.with_suffix('.log'));return dest
 with ThreadPoolExecutor(max_workers=3) as pool:chains=list(pool.map(chain_job,['house','beach','approach']))
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:replays=list(pool.map(replay_run,folders+chains))
 routes=[]
 for (route,start),folder in zip(route_specs,folders):
  a=READ(ROOT/f"runs/navigation-routes-v7/candidate/{route['id']}-{start}/result.json");b=READ(folder/'result.json')
  assert a['route']==b['route'] and a['budget']==b['budget'] and a['sword_step']==b['sword_step'] and a['actions'][:a['sword_step']]==b['actions'][:b['sword_step']]
  routes.append(dict(route=route['id'],start=start,status=b['status'],baseline_status=a['status'],waypoints=b['progress']['cursor'],baseline_waypoints=a['progress']['cursor'],lost=a['status']=='success' and b['status']!='success',waypoints_lost=b['progress']['cursor']<a['progress']['cursor'],damage=b['navigation_damage'],steps=b['navigation_steps']))
 continuous=[]
 for folder in chains:
  b=READ(folder/'result.json');a=READ(ROOT/f"runs/navigation-routes-v7/chain-{b['start']}/result.json")
  assert a['goal']==b['goal'] and a['sword_step']==b['sword_step'] and a['actions'][:a['sword_step']]==b['actions'][:b['sword_step']]
  continuous.append({k:b[k] for k in ('start','status','navigation_damage','navigation_steps')})
 resumed=[]
 for label,script,folder,args in [('route','scripts/run_navigation_route.py',OUT/'candidate/beach_return-house',['--route-id','beach_return','--curriculum',OUT/'curriculum.json']),('chain','scripts/run_navigation_chain.py',OUT/'chain-house',['--goal','0','0','226','36','121'])]:
  full=READ(folder/'result.json')
  stop=min(full['steps']-1,(full['progress']['completed'][0]['step']+2 if label=='route' and full['progress']['completed'] else full['sword_step']+2))
  paused=OUT/f'{label}-paused';dest=OUT/f'{label}-resumed'
  command([script,'--checkpoint',model,'--start','house',*args,'--stop-after',stop,'--out',paused],paused.with_suffix('.log'))
  command([script,'--resume',paused,'--out',dest],dest.with_suffix('.log'))
  r=READ(dest/'result.json');fields=['actions','fingerprint','steps','sword_step','navigation_steps','damage','navigation_damage','status','final_state']+(['progress'] if label=='route' else [])
  assert all(full[k]==r[k] for k in fields)
  resumed.append(dict(kind=label,exact_fields=fields,paused_step=stop,completed_goals_at_pause=READ(paused/'result.json').get('progress',{}).get('cursor'),verified=True))
 gates=dict(local_success_preservation=all(not r['lost'] for r in local.values()),zero_local_damage_deaths=all(not r['damage'] and not r['deaths'] for r in local.values()),route_preservation=all(not r['lost'] and not r['waypoints_lost'] for r in routes),zero_route_damage_deaths=all(not r['damage'] and r['status']!='death' for r in routes),continuous_chains=all(r['status']=='success' and not r['navigation_damage'] for r in continuous),exact_replays_and_resumes=True,more_complete_routes=sum(r['status']=='success' for r in routes)>6)
 report=dict(candidate_path=str(model.relative_to(ROOT)),candidate_sha256=sha256(model),parent_sha256=sha256(parent),training_plan_sha256=sha256(OUT/'plan.json'),evaluation_plan_sha256=sha256(OUT/'evaluation-plan.json'),local_panels=local,sword=dict(summary=sword,pairs=pairs),routes=routes,continuous=continuous,replays=replays,resumes=resumed,gates=gates,eligible=all(gates.values()),training_performed=True,reserved_evaluation_used=False,harness_privilege='D',completion_evaluated=False)
 for p,h in plan['baseline_hashes'].items():assert sha256(ROOT/p)==h
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/navigation-routes-v9.json').write_text(json.dumps(report,indent=2));print('FINAL_GATES',json.dumps(gates),flush=True)
if __name__=='__main__':main()

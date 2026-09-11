"""Frozen physical-start perturbations for the selected cliff specialists."""
import json,sys,shutil,tempfile,hashlib
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import torch
from gameboy_agent.navigation import NavigationController,encode
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.dataset import sha256
from control_context import ControlContext
from run_skill_chain import senses
from route_progress import advance
READ=lambda p:json.loads(Path(p).read_text());OUT=ROOT/'runs/navigation-cliff-stress-v1'
CONDITIONS={'control':0,'up':1,'down':2,'left':3,'right':4}

def supervision_keys(checkpoint):
 saved=torch.load(checkpoint,map_location='cpu');keys={};assets={}
 hashes={**READ(ROOT/'runs/navigation-cliff-specialists-v1/plan.json')['training_artifacts'],**READ(ROOT/'runs/navigation-cliff-specialists-v2/plan.json')['training_artifacts']}
 for expert in saved['goal_experts']:
  g=expert['goal'];key=tuple(g['room'])+(g['x'],g['y']);keys[key]=set()
  for row in expert['provenance']:
   p=ROOT/row['path']
   if str(p) not in assets:
    assert sha256(p)==hashes[str(p.relative_to(ROOT))];assets[str(p)]=np.load(p)['x']
   keys[key].add((assets[str(p)][row['row']]*saved['input_mask']).tobytes())
 return keys

def trial(job):
 torch.set_num_threads(1);plan=READ(OUT/'plan.json');checkpoint=ROOT/plan['policy_path'];assert sha256(checkpoint)==plan['policy_sha256'];policy=NavigationController(checkpoint);known=supervision_keys(checkpoint);folder=ROOT/job['source_run'];run=READ(folder/'result.json');assert sha256(folder/'result.json')==job['source_result_sha256'];prefix=run['actions'][:job['anchor_step']];goals=run['route']['goals'][job['goal_index']:];dest=OUT/job['id'];dest.mkdir()
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(folder/'game.gbc',rom);assert sha256(rom)==job['rom_sha256']
  def restore():
   base=TrainingEnv(rom,folder/'initial.state',max_steps=3500,sword_curriculum=False);env=ControlContext(base);obs,_=env.reset(seed=0)
   for a in prefix:obs,*_=env.step(np.asarray(a))
   return base,env,obs
  base,env,obs=restore();anchor=senses(base).__dict__;assert [*anchor['room'],anchor['x'],anchor['y'],anchor['health']]==job['anchor_pose'];anchor_fp=fingerprint(base);nudges=[];setup_damage=0;setup_invalid=None;actions=[];events=[];xs=[];damage=0;progress=dict(cursor=0,leg_steps=0,leg_start=0,completed=[])
  try:
   if job['condition']!='control':
    for _ in range(plan['perturbation_actions']):
     s=senses(base);button=1 if s.a_item==1 else 2 if s.b_item==1 else 0;a=[CONDITIONS[job['condition']],button if base.last_action[1]!=button else 0];nudges.append(a);obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);setup_damage+=max(0,s.health-after.health)
     if setup_damage or after.health==0 or done or truncated:setup_invalid='setup_damage' if setup_damage else 'setup_environment_end';break
   initial=senses(base).__dict__;initial_fp=fingerprint(base);initial_x=encode(obs,initial['room'],goals[0]['room'],goals[0]['x'],goals[0]['y']);g=goals[0];matched=(initial_x*policy.mask).tobytes() in known[tuple(g['room'])+(g['x'],g['y'])];status=setup_invalid or 'running'
   if setup_invalid is None:
    while True:
     s=senses(base);status=advance(s,goals,progress,len(actions),plan['budget_per_goal'])
     if status!='running':break
     g=goals[progress['cursor']];x=encode(obs,s.room,g['room'],g['x'],g['y']);a=policy.action(obs,s.room,g);xs.append(x);progress['leg_steps']+=1;actions.append(a);obs,_,done,truncated,_=env.step(np.asarray(a));after=senses(base);loss=max(0,s.health-after.health);damage+=loss;events.append(dict(step=len(actions)-1,goal_index=job['goal_index']+progress['cursor'],goal=g,state=s.__dict__,action=a,after=after.__dict__,damage=loss))
     if done or truncated:status='death' if after.health==0 else 'environment_end';break
   final=fingerprint(base);final_state=senses(base).__dict__;base.pyboy.screen.image.save(dest/'final.png')
   if job['condition']=='control':assert actions==run['actions'][job['anchor_step']:] and final==run['fingerprint'] and status=='success'
  finally:env.close()
  base,env,obs=restore()
  try:
   assert fingerprint(base)==anchor_fp
   for a in nudges:obs,*_=env.step(np.asarray(a))
   assert fingerprint(base)==initial_fp
   for x,e in zip(xs,events):
    s=senses(base);g=e['goal'];assert np.array_equal(x,encode(obs,s.room,g['room'],g['x'],g['y']));obs,*_=env.step(np.asarray(e['action']))
   assert fingerprint(base)==final
  finally:env.close()
  if xs:np.savez_compressed(dest/'observed-rollout.npz',x=np.stack(xs),y=np.asarray(actions,dtype=np.int64))
 result=dict(case_id=job['id'],start=job['start'],anchor=job['anchor'],condition=job['condition'],status=status,valid_setup=setup_invalid is None,setup_damage=setup_damage,damage=damage,success=status=='success',safe_success=status=='success' and damage==0,steps=len(actions),goals_completed=progress['cursor'],goals_total=len(goals),progress=progress,anchor_state=anchor,initial_state=initial,final_state=final_state,anchor_fingerprint=anchor_fp,initial_fingerprint=initial_fp,final_fingerprint=final,position_changed=(anchor['room'],anchor['x'],anchor['y'])!=(initial['room'],initial['x'],initial['y']),room_changed=anchor['room']!=initial['room'],matches_latest_expert_supervision=matched,setup_actions=nudges,actions=actions,events=events,independent_replay_verified=True,feature_replay_verified=True,control_matches_historical=job['condition']=='control',training_performed=False)
 (dest/'result.json').write_text(json.dumps(result,indent=2));return {k:v for k,v in result.items() if k not in ('actions','events','setup_actions','progress')}

def summarize(rows):
 valid=[r for r in rows if r['valid_setup']]
 return dict(cases=len(rows),valid_setups=len(valid),setup_damage_cases=sum(r['setup_damage']>0 for r in rows),setup_damage=sum(r['setup_damage'] for r in rows),completed=sum(r['success'] for r in valid),safe_completed=sum(r['safe_success'] for r in valid),navigation_damage_cases=sum(r['damage']>0 for r in valid),navigation_damage=sum(r['damage'] for r in valid),navigation_deaths=sum(r['status']=='death' for r in valid),position_changed=sum(r['position_changed'] for r in valid),unique_valid_initial_fingerprints=len({r['initial_fingerprint'] for r in valid}),latest_expert_supervision_matches=sum(r['matches_latest_expert_supervision'] for r in valid))

def main():
 OUT.mkdir(exist_ok=False);selection=READ(ROOT/'configs/navigation_experiment.json');jobs=[]
 for start in ['house','beach','approach']:
  folder=ROOT/f'runs/navigation-cliff-specialists-v2/candidate/room_loop-{start}';r=READ(folder/'result.json');m=READ(folder/'manifest.json')
  for name,h in m['artifacts'].items():assert sha256(folder/name)==h
  t=[json.loads(line) for line in (folder/'trajectory.jsonl').read_text().splitlines()];cliff=[x for x in t if x['goal_index']==2];west=next(x for x in cliff if x['room']==[0,0,225]);upper=next(x for x in cliff if x['step']>west['step'] and x['room']==[0,0,226] and x['y']<=64)
  anchors=[('cliff_entry',r['progress']['completed'][1]['step'],2),('west_corridor',west['step']+1,2),('upper_entry',upper['step']+1,2),('return_entry',r['progress']['completed'][2]['step'],3)]
  for name,index,goal_index in anchors:
   pose=t[index-1];assert pose['step']==index-1
   for condition in CONDITIONS:jobs.append(dict(id=f'{start}-{name}-{condition}',start=start,anchor=name,anchor_step=index,goal_index=goal_index,anchor_pose=[*pose['room'],pose['x'],pose['y'],pose['health']],condition=condition,source_run=str(folder.relative_to(ROOT)),source_result_sha256=sha256(folder/'result.json'),rom_sha256=sha256(folder/'game.gbc')))
 plan=dict(jobs=jobs,policy_path=selection['policy_path'],policy_sha256=selection['policy_sha256'],perturbation_actions=4,budget_per_goal=256,protocol='60 frozen cases: 3 historical starts x 4 deterministic route anchors x unchanged control or four fixed directional setup actions. Setup alternates the equipped sword from prior button state. No teleports, memory writes or adaptive retries. Evaluate original remaining final goals in the same episode, 256 learned actions per remaining goal. Budget resets at the stress handoff; setup and historical prefix are not charged to learned budget.',setup_rule='Stop setup and do not evaluate learned navigation if setup causes damage/death/environment termination. Report every such case separately; do not remove it from the frozen 48-perturbation denominator. Other cases, including wall-blocked/no-position-change setups and room transitions, remain in the panel.',acceptance='All 12 controls must exactly match historical actions and final fingerprint. Broad stress pass requires all 48 perturbations to have valid setup and safe learned completion. Also report valid-setup completion separately, without attributing setup damage to the learned policy.',independent_replay='Replay every physical prefix, setup and recorded learned sequence independently; compare each learned input feature row and final fingerprint.',scope='New development perturbations of known training/development routes; unchanged final goals, not held-out maps or reserved evaluation. Input-match diagnostic covers latest expert supervision only, not all inherited pretraining.',reserved_evaluation_used=False,training_performed=False,source_sha256=sha256(__file__),baseline_hashes={str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'configs/navigation_experiment.json',ROOT/'configs/sword_controller.json',ROOT/'configs/navigation_retired_cohorts.json']},runtime_sources={str(p.relative_to(ROOT)):sha256(p) for p in list((ROOT/'src/gameboy_agent').glob('*.py'))+[ROOT/'scripts/control_context.py',ROOT/'scripts/route_progress.py',ROOT/'scripts/run_skill_chain.py']})
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'source.py');print('FROZEN',len(jobs),sha256(OUT/'plan.json'),flush=True)
 with ProcessPoolExecutor(max_workers=6,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for r in pool.map(trial,jobs):
   results.append(r)
   if len(results)%5==0:print('VERIFIED',len(results),json.dumps(summarize(results)),flush=True)
 control=[r for r in results if r['condition']=='control'];perturbed=[r for r in results if r['condition']!='control'];assert len(control)==12 and len(perturbed)==48;groups={}
 for field in ['anchor','condition','start']:groups[field]={value:summarize([r for r in perturbed if r[field]==value]) for value in sorted({r[field] for r in perturbed})}
 report=dict(plan_sha256=sha256(OUT/'plan.json'),policy_path=plan['policy_path'],policy_sha256=plan['policy_sha256'],controls=summarize(control),perturbed=summarize(perturbed),by_group=groups,cases=results,all_independent_replays_verified=all(r['independent_replay_verified'] for r in results),controls_match_historical=all(r['control_matches_historical'] for r in control),passes_frozen_stress_gate=all(r['safe_success'] and r['valid_setup'] for r in results),training_performed=False,selection_changed=False,reserved_evaluation_used=False,scope=plan['scope'])
 for p,h in {**plan['baseline_hashes'],**plan['runtime_sources']}.items():assert sha256(ROOT/p)==h
 assert sha256(ROOT/plan['policy_path'])==plan['policy_sha256'];(OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/navigation-cliff-stress-v1.json').write_text(json.dumps(report,indent=2));print('FINAL',json.dumps({k:v for k,v in report.items() if k not in ('cases','by_group')}),flush=True)
if __name__=='__main__':main()

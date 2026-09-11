"""48 paired physical sessions comparing cadence and proximity-gated teachers."""
import json,sys,shutil,tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256,pack_observation
from proximity_sword import gate,inputs,THREATS
OUT=ROOT/'runs/proximity-sword-48-v1';CACHE=ROOT/'runs/navigation-cache-v2'

def trial(args):
 import torch,pyarrow.parquet as pq
 import gameboy_agent.training_env as training
 from gameboy_agent.navigation import reached
 from gameboy_agent.checkpoint import fingerprint
 from control_context import ControlContext
 from run_skill_chain import senses
 from navigation_recovery import teacher
 torch.set_num_threads(1)
 case,variant,batch=args;source=Path(batch)/case['source_path'];meta=json.loads((source.parent/'manifest.json').read_text());assert sha256(source)==case['source_sha256']
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
  base,env,obs=restore([]);initial=fingerprint(base);actions=[];events=[];damage=0;status='timeout';swings=0;frames=0;presses=0;types=set()
  original=training.advance
  class Tap:
   def __init__(self,boy):self.boy=boy
   def __getattr__(self,n):return getattr(self.boy,n)
   def tick(self,*a,**kw):
    nonlocal swings,frames
    before=int(self.boy.memory[0xC137]);value=self.boy.tick(*a,**kw);after=int(self.boy.memory[0xC137]);frames+=1
    swings+=int(before not in (1,2,3,4) and after in (1,2,3,4));return value
  def tapped(boy,tracker,pressed,**kw):return original(Tap(boy),tracker,pressed,**kw)
  training.advance=tapped
  try:
   for step in range(128):
    s=senses(base);proposed=teacher(s,case['goal'],None,step,0,{});info=inputs(base);types.update(e['type'] for e in info['entities']);button=1 if s.a_item==1 else 2 if s.b_item==1 else 0
    action,reason=gate(proposed,dialogue=s.dialogue,sword_button=button,**info) if variant=='proximity' else (proposed,'cadence')
    presses+=int(bool(button) and action[1]==button and not s.dialogue)
    obs,_,done,truncated,_=env.step(np.asarray(action));after=senses(base);loss=max(0,s.health-after.health);damage+=loss;actions.append(action)
    events.append(dict(step=step,proposed=proposed,action=action,reason=reason,damage=loss,sword_state=info['sword_state'],near_threats=sum(e['type'] in THREATS and (e['x']-s.x)**2+(e['y']-s.y)**2<=32**2 for e in info['entities'])))
    if after.health==0:status='death';break
    if reached(after.room,after.x,after.y,case['goal']):status='success';break
    if done or truncated:status='environment_end';break
   final=fingerprint(base);final_state=senses(base).__dict__
  finally:training.advance=original;env.close()
  base,env,obs=restore(actions)
  try:assert fingerprint(base)==final
  finally:env.close()
  result=dict(case_id=case['segment_id'],variant=variant,start=case['start'],kind=case['kind'],status=status,success=status=='success',steps=len(actions),damage=damage,actual_swing_starts=swings,sword_press_actions=presses,frames=frames,
   start_fingerprint=initial,final_fingerprint=final,final_state=final_state,observed_entity_types=sorted(types),replay_verified=True,actions=actions,events=events)
  (OUT/f'{case["segment_id"]}-{variant}.json').write_text(json.dumps(result,indent=2))
  return {k:v for k,v in result.items() if k not in ('actions','events','final_state')}

def main():
 OUT.mkdir(exist_ok=False);metadata=json.loads((CACHE/'manifest.json').read_text());assert sha256(CACHE/'live-dev-cases.json')==metadata['artifacts']['live-dev-cases.json'];cases=json.loads((CACHE/'live-dev-cases.json').read_text());assert len(cases)==48
 plan=dict(cases=cases,matched_sessions=48,rollouts=96,budget=128,radius_pixels=32,variants=['cadence','proximity'],movement_teacher='navigation_recovery.teacher attempt 0; same movement rule in both arms',active_swing_states=[1,2,3,4],threat_types=sorted(THREATS),
  source_hashes={p.name:sha256(p) for p in [Path(__file__),ROOT/'scripts/proximity_sword.py',ROOT/'scripts/navigation_recovery.py']},harness_privilege='D',reserved_evaluation_used=False,training_performed=False,
  gate='Fewer actual swings; no baseline success lost, no increased per-case damage or deaths. Diagnostic only; selected learned navigator unchanged.')
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copy2(__file__,OUT/'experiment_source.py');shutil.copy2(ROOT/'scripts/proximity_sword.py',OUT/'gate_source.py')
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for r in pool.map(trial,[(c,v,metadata['source_batch']) for c in cases for v in plan['variants']]):results.append(r);print(json.dumps({k:r[k] for k in ['case_id','variant','status','damage','actual_swing_starts']}),flush=True)
 pairs=[]
 for c in cases:
  a=next(r for r in results if r['case_id']==c['segment_id'] and r['variant']=='cadence');b=next(r for r in results if r['case_id']==c['segment_id'] and r['variant']=='proximity');assert a['start_fingerprint']==b['start_fingerprint']
  pairs.append(dict(case_id=c['segment_id'],lost=a['success'] and not b['success'],gained=b['success'] and not a['success'],damage_delta=b['damage']-a['damage'],swings_delta=b['actual_swing_starts']-a['actual_swing_starts']))
 summary={v:{k:sum(r[k] for r in results if r['variant']==v) for k in ['success','steps','damage','actual_swing_starts','sword_press_actions','frames']} for v in plan['variants']}
 for v in summary:summary[v]['deaths']=sum(r['status']=='death' for r in results if r['variant']==v)
 passed=summary['proximity']['actual_swing_starts']<summary['cadence']['actual_swing_starts'] and not any(p['lost'] or p['damage_delta']>0 for p in pairs) and summary['proximity']['deaths']<=summary['cadence']['deaths']
 report=dict(summary=summary,pairs=pairs,episodes=results,gate_passed=passed,paired_start_fingerprints_match=True,all_replays_verified=True,matched_sessions=48,rollouts=96,reserved_evaluation_used=False,training_performed=False)
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/proximity-sword-48-v1.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(summary=summary,gate_passed=passed)),flush=True)
if __name__=='__main__':main()

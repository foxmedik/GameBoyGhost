"""Matched v7 movement with and without the frozen terrain-motion sword teacher."""
import json,sys,shutil,tempfile,subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256,pack_observation
from terrain_sword import inputs,reachable_terrain,gate
from proximity_sword import THREATS
OUT=ROOT/'runs/v7-sword-teacher-v1'
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
    action,reason=gate(proposed,dialogue=s.dialogue,sword_button=button,motion=True,**info) if variant=='v7_gated' else (proposed,'v7_unchanged')
    assert action[0]==proposed[0]
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


def main():
 cache=ROOT/'runs/navigation-cache-v2';meta=READ(cache/'manifest.json');cases=READ(cache/'live-dev-cases.json')
 assert len(cases)==48 and sha256(cache/'live-dev-cases.json')==meta['artifacts']['live-dev-cases.json']
 selection=READ(ROOT/'configs/navigation_experiment.json');model=ROOT/selection['policy_path']
 assert sha256(model)==selection['policy_sha256']=='6d26dcd6a2d7b22c0681d7e7a0c9b9d3f27c9d8caccbeca94426be0da97fc062'
 OUT.mkdir(exist_ok=False)
 paths=[Path(__file__),ROOT/'scripts/terrain_sword.py',ROOT/'scripts/proximity_sword.py',ROOT/'scripts/control_context.py',ROOT/'scripts/run_skill_chain.py',ROOT/'src/gameboy_agent/navigation.py',ROOT/'src/gameboy_agent/training_env.py',ROOT/'src/gameboy_agent/transitions.py',ROOT/'src/gameboy_agent/checkpoint.py',ROOT/'docs/V7_SWORD_TEACHER_V1_PROTOCOL.md']
 plan=dict(cases=cases,matched_sessions=48,rollouts=96,variants=['v7','v7_gated'],budget=128,tolerance_manhattan_pixels=8,
  policy_path=str(model),policy_sha256=sha256(model),gate='Existing terrain_sword.gate(motion=True), unchanged parameters; suppress only v7-proposed sword presses; movement always v7 on the current observation.',
  movement_interpretation='Same movement function in both arms, not a fixed movement sequence. Suppression changes observations, timing, terrain and subsequent v7 decisions.',
  motion_horizon=20,motion_limitation='Inherited 20-frame heuristic was chosen for an alternating teacher; learned v7 may propose sword on a different schedule. No guarantee of next sword opportunity.',
  adoption='At least 25% fewer actual swing starts, no lost v7 successes, no per-case damage increases, no new deaths. Full exact final replay for both arms. Collect safe successful demonstrations only if this gate passes.',
  selected_config_sha256=sha256(ROOT/'configs/navigation_experiment.json'),source_hashes={str(p.relative_to(ROOT)):sha256(p) for p in paths},
  assets={p.name:sha256(p) for p in (Path(meta['source_batch'])/'assets').iterdir() if p.suffix in ('.gbc','.state')},
  source_batch=meta['source_batch'],harness_privilege='D',training_performed=False,reserved_evaluation_used=False)
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2))
 for p in paths:
  dest=OUT/'sources'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for r in pool.map(trial,[(c,v,meta['source_batch'],str(OUT),str(model)) for c in cases for v in plan['variants']]):
   results.append(r)
   if len(results)%12==0:print('VERIFIED',len(results),96,flush=True)
 pairs=[]
 for c in cases:
  a=next(r for r in results if r['case_id']==c['segment_id'] and r['variant']=='v7');b=next(r for r in results if r['case_id']==c['segment_id'] and r['variant']=='v7_gated')
  old=READ(ROOT/f"runs/navigation-routes-v7/eval-original/{c['segment_id']}-learned.json")
  assert a['start_fingerprint']==b['start_fingerprint']==old['start_fingerprint'] and a['final_fingerprint']==old['final_fingerprint']
  pairs.append(dict(case_id=c['segment_id'],lost=a['success'] and not b['success'],gained=b['success'] and not a['success'],damage_delta=b['damage']-a['damage'],new_death=b['status']=='death' and a['status']!='death',swings_delta=b['actual_swing_starts']-a['actual_swing_starts']))
 summary={v:{k:sum(r[k] for r in results if r['variant']==v) for k in ['success','steps','damage','actual_swing_starts','sword_press_actions','frames']} for v in plan['variants']}
 for v in summary:summary[v]['deaths']=sum(r['status']=='death' for r in results if r['variant']==v)
 passed=summary['v7_gated']['actual_swing_starts']<=.75*summary['v7']['actual_swing_starts'] and not any(p['lost'] or p['damage_delta']>0 or p['new_death'] for p in pairs)
 from collections import Counter
 reasons={v:dict(Counter(e['reason'] for c in cases for e in READ(OUT/f"{c['segment_id']}-{v}.json")['events'])) for v in plan['variants']}
 report=dict(summary=summary,pairs=pairs,episodes=results,reasons=reasons,gate_passed=passed,matched_sessions=48,rollouts=96,all_replays_verified=True,paired_starts_match=True,historical_v7_matches=True,plan_sha256=sha256(OUT/'plan.json'),training_performed=False,reserved_evaluation_used=False)
 assert sha256(ROOT/'configs/navigation_experiment.json')==plan['selected_config_sha256']
 for p in paths:assert sha256(p)==plan['source_hashes'][str(p.relative_to(ROOT))]
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/v7-sword-teacher-v1.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(summary=summary,gate_passed=passed)),flush=True)
if __name__=='__main__':main()

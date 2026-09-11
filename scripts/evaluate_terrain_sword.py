"""48 matched cases: cadence, terrain+exit guard, and terrain+exit+motion."""
import json,sys,shutil,tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from gameboy_agent.dataset import sha256,pack_observation
from terrain_sword import gate,inputs,reachable_terrain
from proximity_sword import THREATS
OUT=ROOT/'runs/proximity-sword-48-v2';CACHE=ROOT/'runs/navigation-cache-v2'

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
    s=senses(base);proposed=teacher(s,case['goal'],None,step,0,{});info=inputs(base);types.update(e['type'] for e in info['entities']);button=1 if s.a_item==1 else 2 if s.b_item==1 else 0
    action,reason=gate(proposed,dialogue=s.dialogue,sword_button=button,motion=variant=='terrain_motion',**info) if variant!='cadence' else (proposed,'cadence')
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
  (OUT/f'{case["segment_id"]}-{variant}.json').write_text(json.dumps(result,indent=2))
  return {k:v for k,v in result.items() if k not in ('actions','events','frame_events','final_state')}

def main():
 OUT.mkdir(exist_ok=False)
 metadata=json.loads((CACHE/'manifest.json').read_text())
 assert sha256(CACHE/'live-dev-cases.json')==metadata['artifacts']['live-dev-cases.json']
 cases=json.loads((CACHE/'live-dev-cases.json').read_text());assert len(cases)==48
 old_plan=json.loads((ROOT/'runs/proximity-sword-48-v1/plan.json').read_text())
 assert cases==old_plan['cases']
 paths=[Path(__file__),ROOT/'scripts/terrain_sword.py',ROOT/'scripts/proximity_sword.py',ROOT/'scripts/navigation_recovery.py',ROOT/'scripts/control_context.py',ROOT/'scripts/run_skill_chain.py',ROOT/'src/gameboy_agent/training_env.py',ROOT/'src/gameboy_agent/transitions.py',ROOT/'src/gameboy_agent/checkpoint.py',ROOT/'src/gameboy_agent/ladx_baseline.py',ROOT/'docs/PROXIMITY_SWORD_48_V2.md',ROOT/'tests/test_terrain_sword.py']
 references=[ROOT/'references/LADX-Disassembly/azle-r1.sym',ROOT/'references/LADX-Disassembly/src/code/bank0.asm',ROOT/'references/LADX-Disassembly/src/data/objects/physics.asm',ROOT/'references/LADX-Disassembly/src/constants/memory/wram.asm',ROOT/'references/LADXExperiments/experiments/gym_env/link_awake_env.py']
 assets=Path(metadata['source_batch'])/'assets'
 assert sha256(assets/'game.gbc')==sha256(ROOT/'references/LADX-Disassembly/azle-r1.gbc')=='6285ba6201f17bc8595c600ebc2477d52561f0aff29b11f7fc3343bacb2e230b'
 rom_bytes=(assets/'game.gbc').read_bytes()
 assert rom_bytes[0x158E:0x1592]==bytes([22,250,8,8])
 assert rom_bytes[0x159A:0x159E]==bytes([8,8,250,22])
 plan=dict(cases=cases,matched_sessions=48,rollouts=144,budget=128,radius_pixels=32,motion_horizon_ready_frames=20,
  variants=['cadence','terrain','terrain_motion'],movement_teacher='navigation_recovery.teacher attempt 0; unchanged movement rule',
  source_hashes={str(p.relative_to(ROOT)):sha256(p) for p in paths+references},
  asset_hashes={p.name:sha256(p) for p in assets.iterdir() if p.suffix in ('.gbc','.state')},
  baseline_plan_sha256=sha256(ROOT/'runs/proximity-sword-48-v1/plan.json'),
  selected_navigation_sha256=sha256(ROOT/'configs/navigation_experiment.json'),
  harness_privilege='D',reserved_evaluation_used=False,training_performed=False,
  gate='At least 25% fewer actual swings; no lost cadence successes, no per-case damage increases, no new per-case deaths. No automatic adoption or training.')
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2))
 for p in paths+references:
  dest=OUT/'sources'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:
  results=[]
  for r in pool.map(trial,[(c,v,metadata['source_batch']) for c in cases for v in plan['variants']]):
   results.append(r);print(json.dumps({k:r[k] for k in ['case_id','variant','status','damage','actual_swing_starts']}),flush=True)
 pairs=[]
 for c in cases:
  a=next(r for r in results if r['case_id']==c['segment_id'] and r['variant']=='cadence')
  historical=json.loads((ROOT/f"runs/proximity-sword-48-v1/{c['segment_id']}-cadence.json").read_text())
  assert a['start_fingerprint']==historical['start_fingerprint']
  assert a['final_fingerprint']==historical['final_fingerprint']
  for v in plan['variants'][1:]:
   b=next(r for r in results if r['case_id']==c['segment_id'] and r['variant']==v)
   assert a['start_fingerprint']==b['start_fingerprint']
   pairs.append(dict(case_id=c['segment_id'],variant=v,lost=a['success'] and not b['success'],gained=b['success'] and not a['success'],damage_delta=b['damage']-a['damage'],new_death=b['status']=='death' and a['status']!='death',swings_delta=b['actual_swing_starts']-a['actual_swing_starts']))
 summary={v:{k:sum(r[k] for r in results if r['variant']==v) for k in ['success','steps','damage','actual_swing_starts','sword_press_actions','frames']} for v in plan['variants']}
 for v in summary:summary[v]['deaths']=sum(r['status']=='death' for r in results if r['variant']==v)
 passed={v:summary[v]['actual_swing_starts']<=0.75*summary['cadence']['actual_swing_starts'] and not any(p['lost'] or p['damage_delta']>0 or p['new_death'] for p in pairs if p['variant']==v) for v in plan['variants'][1:]}
 from collections import Counter
 reasons={v:dict(Counter(e['reason'] for c in cases for e in json.loads((OUT/f"{c['segment_id']}-{v}.json").read_text())['events'])) for v in plan['variants']}
 assert sha256(ROOT/'configs/navigation_experiment.json')==plan['selected_navigation_sha256']
 for p in paths+references:assert sha256(p)==plan['source_hashes'][str(p.relative_to(ROOT))]
 report=dict(summary=summary,pairs=pairs,episodes=results,gate_passed=passed,reasons=reasons,paired_start_fingerprints_match=True,historical_cadence_fingerprints_match=True,all_replays_verified=True,matched_sessions=48,rollouts=144,reserved_evaluation_used=False,training_performed=False,plan_sha256=sha256(OUT/'plan.json'))
 (OUT/'result.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/proximity-sword-48-v2.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(summary=summary,gate_passed=passed)),flush=True)
if __name__=='__main__':main()

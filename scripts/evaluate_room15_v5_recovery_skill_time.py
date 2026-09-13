"""Physical standalone gate for the V5 recovery-only policy."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.room15_model_v4 import action_index,action_command,temporal_feature,update
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix,senses
from run_toadstool_progression import Trace,apply
from train_room15_v5_recovery_skill import RecoveryNet

def run(plan,out):
 source=ROOT/'runs/state-driven-tail-cave-disengage-guarded-v1';guided=ROOT/'runs/room15-v5-guided-30m';teacher=ROOT/plan['source'];saved=torch.load(ROOT/plan['candidate'],map_location='cpu');m=RecoveryNet(saved['inputs']);m.load_state_dict(saved['model']);m.eval();results=[]
 for item in json.loads((teacher/'summary.json').read_text())['results']:
  spec=item['spec'];case=spec['id'];gid='guided-v5-'+case.split('-')[1];d=out/case;d.mkdir();rows=[];history=[];events=json.loads((guided/gid/'evidence.json').read_text());hit=next(x for x in events if x['kind']=='guided_early_y80_recovery');old=[json.loads(x) for x in (guided/gid/'trajectory.jsonl').read_text().splitlines()];old=[r for r in old if r['frame']<hit['frame']]
  env=ProgressionEnv(source/f"development-house-{spec['base']:02d}"/'game.gbc',source/f"development-house-{spec['base']:02d}"/'initial.state',max_steps=16000,max_frames=300000,completion_milestone=None);failure=None
  try:
   env.reset(seed=0);prefix(env,source/f"development-house-{spec['base']:02d}");env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
   for r in old:
    before=snapshot(env.pyboy);a=action_index(r['command']);apply(env,r['command']);after=snapshot(env.pyboy)
    if a is not None:history=update(history,a,before,after)
   start=senses(env);tr=Trace(env,(d/'trajectory.jsonl').open('x'),rows);escaped=None
   for n in range(128):
    st=snapshot(env.pyboy)
    features=temporal_feature(senses(env),history)
    features=__import__('numpy').concatenate((features,[n/128])).astype('float32')
    x=torch.from_numpy((features-saved['mean'])/saved['scale']);a=int(m(x).argmax());buttons,frames=action_command(a)
    (tr.step_input_events(buttons,release=('up','down','left','right','a','b','start','select'),frames=frames) if a==9 else tr.step_buttons(buttons,action_frames=frames));history=update(history,a,st,snapshot(env.pyboy))
    if escaped is None and abs(st['x']-start['state']['x'])+abs(st['y']-start['state']['y'])>=16:escaped=n+1
   final=senses(env);ok=escaped is not None and final['state']['health'] and not (80<=final['state']['y']<=84 and final['state']['x']==start['state']['x']);failure=None if ok else 'escape contract failed'
  except Exception as e: final=senses(env);escaped=None;failure=f'{type(e).__name__}: {e}'
  finally: env.close()
  results.append({'case':case,'success':failure is None,'failure':failure,'escaped_at':escaped,'final':final})
  (d/'result.json').write_text(json.dumps(results[-1],indent=2)+'\n')
 report={'status':'complete','cases':len(results),'successes':sum(r['success'] for r in results),'results':results,'validation_loaded':False};(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=ROOT/'configs/room15_student_v5_recovery_skill.json';o=ROOT/'runs/room15-v5-recovery-skill-time-probe-v3';o.mkdir();run(json.loads(p.read_text())|{'candidate':'runs/room15-v5-recovery-skill-time-candidate/candidate.pt'},o)

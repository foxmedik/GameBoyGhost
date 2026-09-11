"""Scripted diagnostic: validate E1 -> E0 -> D0, with zero-loss stop rule."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.world_memory import WorldMemory,file_hash


def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


def run():
    source=ROOT/'runs/progression-attempt-v2';out=ROOT/'runs/progression-west-passage-v1'
    out.mkdir(exist_ok=False)
    for name in ('initial.state','game.gbc'):shutil.copy2(source/name,out/name)
    prefix=[json.loads(line) for line in (source/'trajectory.jsonl').read_text().splitlines()]
    write(out/'plan.json',dict(source_trace_hash=file_hash(source/'trajectory.jsonl'),
        max_diagnostic_decisions=40,stop_on_any_health_loss=True,stationary_limit=3,
        phases=['Cross west to E0','Align x=24 in E0','Cross north to D0'],
        supervision='scripted_physical_diagnostic_not_learned_completion'))
    expected=None
    for replay in (False,True):
        env=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1100)
        try:
            env.reset(seed=0)
            for row in prefix:
                c=row['command'];env.step_buttons(c['buttons'],action_frames=c['action_frames'],legacy_action=c['legacy_action'])
            assert fingerprint(env)==prefix[-1]['fingerprint']
            initial=snapshot(env.pyboy);trace=[];stationary=0;status='budget';phase=0
            for _ in range(40):
                s=snapshot(env.pyboy)
                if phase==0 and s['room']==[0,0,224]:phase=1
                if phase==1 and abs(s['x']-24)<=3:phase=2
                if phase==2 and s['room']==[0,0,208]:status='western_crossing_verified';break
                movement=3 if phase==0 or (phase==1 and s['x']>24) else 4 if phase==1 else 1
                _,_,done,truncated,info=env.step([movement,0]);after=snapshot(env.pyboy)
                trace.append(dict(decision=env.total_steps-1,command=deepcopy(env.episode_actions[-1]),
                    before=s,after=after,frame=env.frames,events=info['events'],fingerprint=fingerprint(env),
                    diagnostic_phase=phase))
                if after['health']<initial['health']:status='damage_stop';break
                if after['room'] not in ([0,0,225],[0,0,224],[0,0,208]):status='unexpected_room';break
                stationary=stationary+1 if (s['room'],s['x'],s['y'])==(after['room'],after['x'],after['y']) else 0
                if stationary>=3:status='stationary_stop';break
                if done or truncated:status='episode_end';break
            value=dict(status=status,trace=trace,final=snapshot(env.pyboy),journal=env.journal.state())
            if replay:assert value==expected,'Western diagnostic replay mismatch'
            else:
                expected=deepcopy(value)
                env.pyboy.screen.image.save(out/'final.png')
                with (out/'final.state').open('wb') as f:env.pyboy.save_state(f)
        finally:env.close()
    (out/'trajectory.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in prefix+expected['trace']))
    write(out/'journal.json',expected['journal'])
    result=dict(status=expected['status'],steps=len(prefix)+len(expected['trace']),
        diagnostic_steps=len(expected['trace']),diagnostic_damage_raw=initial['health']-expected['final']['health'],
        final=expected['final'],exact_action_replay=True,
        assistance='source_map_assisted_scripted_physical_diagnostic',quest_success=False)
    write(out/'result.json',result)
    write(out/'manifest.json',dict(artifacts={p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}))
    memory=WorldMemory.load(ROOT/'runs/progression-integration-v1/memory-generation-2.json').next_generation()
    memory.import_verified_fixture(out);memory.verify_evidence();memory.save(out/'memory-generation-3.json')
    write(ROOT/'reports/progression-west-passage-v1.json',dict(result=result,output=str(out.relative_to(ROOT)),
        memory_version=memory.version,source_hash=file_hash(Path(__file__))))
    print(json.dumps(result,indent=2))


if __name__=='__main__':run()

"""One bounded guided progression attempt, trace/replay and evidence promotion."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import torch
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_planner import ProgressionPlanner
from gameboy_agent.navigation import NavigationController
from gameboy_agent.world_memory import WorldMemory,file_hash
from gameboy_agent.checkpoint import fingerprint
from control_context import ControlContext
from run_skill_chain import SwordController,senses
from sword_imitation import STARTS


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def run(out, guidance_path):
    began=time.monotonic();torch.set_num_threads(1)
    out.mkdir(parents=True,exist_ok=False)
    guidance=json.loads(guidance_path.read_text())
    memory=WorldMemory.load(ROOT/guidance.get('memory_path','runs/world-memory-v1/generation-1.json'));memory.verify_evidence()
    for config,name in [('sword_controller','sword.json'),('navigation_experiment','navigation.pt')]:
        selection=json.loads((ROOT/f'configs/{config}.json').read_text())
        path=ROOT/selection['policy_path']
        if file_hash(path)!=selection['policy_sha256']:raise ValueError('Selected policy hash mismatch')
        shutil.copy2(path,out/name)
    shutil.copy2(next(ROOT.glob('*.gbc')),out/'game.gbc')
    # Re-obtain the sword continuously from the supplied house start. There is
    # no loading of a mid-episode sword state and no synthetic inventory setup.
    shutil.copy2(STARTS['house'],out/'initial.state')
    memory.save(out/'inherited-memory.json');write(out/'guidance.json',guidance)
    write(out/'plan.json',dict(status='frozen_before_run',max_post_sword_decisions=8192,
        max_frames=200000,guidance=guidance,source_map_hash=file_hash(ROOT/guidance['map_manifest']),
        inherited_memory=memory.version,attempt=1,max_unchanged_attempts=3))
    rows=[];planner=None;sword_step=None
    def play(replay=False):
        nonlocal planner,sword_step
        base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=1600+8192,max_frames=200000)
        env=ControlContext(base)
        manager=ProgressionPlanner(memory,guidance['goals'],goal_budget=guidance['goal_budget'],
                                   recovery_limit=guidance['recovery_limit'])
        nav=NavigationController(out/'navigation.pt')
        sword=SwordController(env,json.loads((out/'sword.json').read_text()))
        try:
            obs,_=env.reset(seed=0)
            while True:
                state=senses(base)
                if not state.sword:
                    if base.total_steps>=1600:manager.status='sword_timeout';break
                    action=sword.action(state);decision={'kind':'selected_sword_controller'}
                else:
                    if sword_step is None:sword_step=base.total_steps
                    if base.total_steps-sword_step>=8192:manager.status='post_sword_budget';break
                    action=manager.action(obs,state,nav);decision=deepcopy(manager.last_decision)
                    if action is None:break
                before=snapshot(base.pyboy)
                obs,_,done,truncated,info=env.step(action)
                row=dict(decision=base.total_steps-1,command=deepcopy(base.episode_actions[-1]),
                    before=before,after=snapshot(base.pyboy),frame=base.frames,
                    events=info['events'],fingerprint=fingerprint(base),planner_decision=decision)
                if replay:
                    expected=rows[base.total_steps-1]
                    if json.dumps(row,sort_keys=True)!=json.dumps(expected,sort_keys=True):
                        raise AssertionError(f'Planner/action replay diverged at {base.total_steps-1}')
                    if base.total_steps==sword_step+5:
                        manager.restore(json.loads(json.dumps(manager.state())))
                else:rows.append(row)
                if done or truncated:
                    manager.status='tail_key_and_entry' if info['task_success'] else 'death' if info['death'] else 'environment_budget'
                    break
            if replay:
                if base.total_steps!=len(rows) or manager.state()!=planner:raise AssertionError('Planner final state mismatch')
                return
            planner=manager.state()
            base.pyboy.screen.image.save(out/'final.png')
            with (out/'final.state').open('wb') as stream:base.pyboy.save_state(stream)
            write(out/'journal.json',json.loads(json.dumps(base.journal.state())))
            result=dict(status=manager.status,steps=base.total_steps,sword_actions=sword_step,
                post_sword_actions=base.total_steps-sword_step if sword_step is not None else 0,
                frames=base.frames,damage_raw=base.journal.damage_raw,healing_raw=base.journal.healing_raw,
                final_state=snapshot(base.pyboy),planner=planner,milestones=base.journal.milestones,
                exact_action_replay=False,assistance='provided_map_guidance_and_structured_read_only_state',
                human_interventions=0,optimizer_updates=0,reserved_evaluation_used=False)
            return result
        finally:env.close()
    result=play()
    (out/'trajectory.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write(out/'result.json',result)
    play(replay=True)
    result.update(exact_action_replay=True,planner_roundtrip_exact=True,wall_seconds=round(time.monotonic()-began,3))
    write(out/'result.json',result)
    write(out/'manifest.json',dict(artifacts={p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}))
    child=memory.next_generation();child.import_verified_fixture(out);child.verify_evidence();child.save(out/'discovered-memory.json')
    report=dict(result=result,output=str(out.relative_to(ROOT)),parent_memory=memory.version,
        next_memory=child.version,new_observations=len(child.observations)-len(memory.observations),
        new_connection_observations=len(child.connections())-len(memory.connections()),
        code_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in [Path(__file__),ROOT/'src/gameboy_agent/progression_planner.py']})
    write(ROOT/'reports'/f'{out.name}.json',report)
    print(json.dumps({k:result[k] for k in ('status','steps','sword_actions','post_sword_actions','damage_raw','milestones')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'runs/progression-attempt-v1');p.add_argument('--guidance',type=Path,default=ROOT/'configs/progression_guidance_v1.json');args=p.parse_args();run(args.out.resolve(),args.guidance.resolve())

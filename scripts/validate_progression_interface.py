"""Single-worker interface proof, physical fixture capture and exact action replay.

This validates the first implementation stage, not Tail Key progression. Test
RAM fixtures are kept separate from the physically recorded trajectories.
"""
import argparse
from copy import deepcopy
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot, ProgressJournal
from gameboy_agent.progression_skills import equip_item
from gameboy_agent.checkpoint import digest, fingerprint
from control_context import ControlContext
from run_skill_chain import SwordController, senses
from sword_imitation import STARTS


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def fixture(out,start,policy):
    out.mkdir()
    shutil.copy2(STARTS[start],out/'initial.state')
    rom=out.parent/'game.gbc'
    env=ProgressionEnv(rom,out/'initial.state',max_steps=2000)
    wrapped=ControlContext(env)
    rows=[]
    original=env.step_buttons
    def recorded(buttons,*,action_frames=10,legacy_action=None):
        before=snapshot(env.pyboy)
        result=original(buttons,action_frames=action_frames,legacy_action=legacy_action)
        rows.append(dict(decision=env.total_steps-1,command=deepcopy(env.episode_actions[-1]),
                         before=before,after=snapshot(env.pyboy),fingerprint=fingerprint(env),
                         frame=env.frames,events=result[4]['events']))
        return result
    env.step_buttons=recorded
    try:
        wrapped.reset(seed=0)
        controller=SwordController(wrapped,policy)
        while not senses(env).sword and env.total_steps<1600:
            _,_,done,truncated,_=wrapped.step(controller.action(senses(env)))
            if done or truncated:break
        if not senses(env).sword or senses(env).health==0:
            raise AssertionError(f'Sword handoff failed from {start}')
        sword_steps=env.total_steps
        # Finish the physical item dialogue before opening the inventory.
        for i in range(128):
            if not senses(env).dialogue:break
            env.step_buttons(['a'] if i%2==0 else [],action_frames=10)
        if senses(env).dialogue:raise AssertionError('Sword dialogue did not close')
        equipped=[]
        if start=='house':
            equipped=[equip_item(env,1,button='b'),equip_item(env,1,button='a')]
        commands=deepcopy(env.episode_actions)
        expected=fingerprint(env)
        journal=json.loads(json.dumps(env.journal.state()))
        frames=env.frames
        env.pyboy.screen.image.save(out/'final.png')
        with (out/'final.state').open('wb') as stream:env.pyboy.save_state(stream)
    finally:wrapped.close()
    (out/'trajectory.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    write(out/'journal.json',journal)
    replay=ProgressionEnv(rom,out/'initial.state',max_steps=2000)
    try:
        replay.reset(seed=0)
        midpoint=len(commands)//2
        for i,command in enumerate(commands):
            replay.step_buttons(command['buttons'], action_frames=command['action_frames'],
                                legacy_action=command['legacy_action'])
            if fingerprint(replay)!=rows[i]['fingerprint']:
                raise AssertionError(f'Action replay diverged at {start}:{i}')
            if replay.frames!=rows[i]['frame']:
                raise AssertionError('Frame count diverged')
            if i==midpoint:
                # Journal serialization boundary while the physical prefix is replayed.
                replay.journal=ProgressJournal.restore(json.loads(json.dumps(replay.journal.state())))
        if fingerprint(replay)!=expected or json.loads(json.dumps(replay.journal.state()))!=journal:
            raise AssertionError('Final gameplay/journal replay mismatch')
        summary=dict(start=start,sword_actions=sword_steps,steps=len(commands),frames=frames,
                     damage_raw=journal['damage_raw'],healing_raw=journal['healing_raw'],
                     physical_equip_results=equipped,exact_action_replay=True,
                     journal_roundtrip_exact=True,final_fingerprint=expected,
                     room_transitions=sum(e['kind']=='room_transition' for e in journal['events']),
                     dialogue_events=sum(e['kind']=='dialogue_observed' for e in journal['events']),
                     terminal_quest_evaluated=False,assistance='structured_read_only_game_state',
                     supervision='selected_sword_controller_then_scripted_physical_menu_skill')
    finally:replay.close()
    write(out/'result.json',summary)
    write(out/'manifest.json',{'artifacts':{p.name:digest(p) for p in out.iterdir() if p.is_file()}})
    return summary


def run(out):
    begin=time.monotonic()
    out.mkdir(parents=True,exist_ok=False)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_progression.py')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful() or result.skipped:
        raise AssertionError('All interface tests must pass without skips')
    source_profile=json.loads((ROOT/'configs/ladx-rom-verification.json').read_text())
    if digest(ROOT/'references/LADX-Disassembly/azle-r1.sym')!=source_profile['symbols_sha256']:
        raise AssertionError('Matched source symbols changed')
    selection=json.loads((ROOT/'configs/sword_controller.json').read_text())
    policy_path=ROOT/selection['policy_path']
    if digest(policy_path)!=selection['policy_sha256']:raise AssertionError('Policy integrity mismatch')
    shutil.copy2(policy_path,out/'sword-policy.json')
    shutil.copy2(next(ROOT.glob('*.gbc')),out/'game.gbc')
    policy=json.loads(policy_path.read_text())
    fixtures=[fixture(out/start,start,policy) for start in ('house','beach','approach')]
    report=dict(schema='progression-interface-validation-v1',status='passed',
                acceptance_scope='stage_1_interface_and_event_foundation',
                tests_run=result.testsRun,synthetic_tests_separate_from_trajectories=True,
                observation_purity_reads=100,fixtures=fixtures,
                live_verified=['sword_acquisition','room_transition','dialogue_id_observation',
                               'inventory_open_close','physical_sword_equip_between_buttons'],
                source_grounded_pending_live=['toadstool','witch_exchange','raccoon_cure',
                                             'tail_key_acquisition','tail_cave_unlock','tail_cave_entry'],
                wall_seconds=round(time.monotonic()-begin,3),workers=1,optimizer_updates=0,
                reserved_evaluation_used=False,run_directory=str(out.relative_to(ROOT)),
                sources={str(p.relative_to(ROOT)):digest(p) for p in
                         [ROOT/'scripts/validate_progression_interface.py',ROOT/'tests/test_progression.py',
                          *sorted((ROOT/'src/gameboy_agent').glob('*.py'))]},
                versions={p:importlib.metadata.version(p) for p in ('pyboy','torch','gymnasium','numpy')},
                sword_policy_sha256=digest(policy_path),rom_sha256=digest(out/'game.gbc'))
    write(out/'report.json',report)
    write(ROOT/'reports/progression-interface-v1.json',report)
    print(json.dumps({k:report[k] for k in ('status','tests_run','fixtures','wall_seconds')},indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'runs/progression-interface-v1')
    run(parser.parse_args().out.resolve())

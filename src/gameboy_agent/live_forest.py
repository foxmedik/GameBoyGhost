"""Live state-driven sword-to-forest handoff; never plays a saved input prefix."""
import json
from pathlib import Path

from gameboy_agent.progression import snapshot
from gameboy_agent.world_memory import file_hash


def execute(env,evidence):
    # Controllers and terrain helper imports are shared with their original drivers.
    root=Path(__file__).resolve().parents[2]
    s=snapshot(env.pyboy)
    if not s['sword'] or s['room']!=[0,0,0xF2]:
        raise RuntimeError(f'Forest handoff requires sword on beach F2, got {s["room"]}')
    # Demonstrated spatial route is guidance, not a saved controller input tape.
    from gameboy_agent.observed_route import follow
    source=root/'runs/progression-attempt-v4'
    expected=json.loads((source/'manifest.json').read_text())['artifacts']['trajectory.jsonl']
    if file_hash(source/'trajectory.jsonl')!=expected:raise ValueError('Observed route evidence changed')
    rows=[json.loads(line) for line in (source/'trajectory.jsonl').read_text().splitlines()]
    start=next(i for i,r in enumerate(rows) if r['before']['sword'])
    follow(env,rows[start:],evidence)
    if snapshot(env.pyboy)['room']!=[0,0,0xD0]:raise RuntimeError('Missing live D0 handoff')
    evidence.append(dict(kind='live_D0_handoff',frame=env.frames))
    source=root/'runs/progression-forest-terrain-v5'
    expected=json.loads((source/'manifest.json').read_text())['artifacts']['trajectory.jsonl']
    if file_hash(source/'trajectory.jsonl')!=expected:raise ValueError('Forest route evidence changed')
    rows=[json.loads(line) for line in (source/'trajectory.jsonl').read_text().splitlines()]
    follow(env,rows[749:],evidence)
    state=snapshot(env.pyboy)
    if state['room']!=[0,0,0x52]:raise RuntimeError(f'Forest handoff expected52, got {state["room"]}')
    evidence.append(dict(kind='live_forest_handoff',frame=env.frames,state=state))

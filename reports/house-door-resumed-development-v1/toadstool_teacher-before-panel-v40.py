"""Known physical toadstool teacher route; not a learned planner result."""
from gameboy_agent.terrain_navigation import cell, paths, steer, terrain
from gameboy_agent.cave_navigation import block_changed
from gameboy_agent.progression_contracts import settle_and_require_stage
from gameboy_agent.local_approach import approach,cross
from gameboy_agent.transitions import BUTTONS
from gameboy_agent.terrain_navigation import exits


def execute(env, evidence, *, forest_crossing=None):
    settle_and_require_stage(env,"toadstool")
    def state():
        return tuple(int(env.pyboy.memory[a]) for a in
                     (0xDBA5, 0xFFF7, 0xFFF6, 0xFF98, 0xFF99, 0xDB4B))

    def raw(buttons, duration):
        env.step_input_events(buttons, release=[b for b in BUTTONS if b not in buttons], frames=duration, release_after=buttons)

    # Release inherited controls before planning from the actual arrival pose.
    env.step_input_events(release=BUTTONS,frames=1)
    if forest_crossing is None:
        x,y=state()[3:5]
        candidates=[e for e in exits(terrain(env.pyboy),cell(x,y),0x52) if e['direction']==2]
        if not candidates:raise RuntimeError('No reachable southern exit from forest52')
        target=min(candidates,key=lambda e:len(e['path']))
        approach(env,target['cell'],terrain,expected=[0,0,0x62])
        cross(env,'down',[0,0,0x62])
    else:
        forest_crossing(env,evidence)
        if state()[:3] != (0,0,0x62):
            raise RuntimeError(f'Injected forest crossing did not reach room62: {state()}')
    approach(env,(7,4),terrain)
    cross(env,'up',[1,10,0xBD])
    evidence.append(dict(kind='state_checked_cave_entry',frame=env.frames,pose=state()))

    # User-traced crumbling-floor path, then the two verified stone pushes.
    raw(("left", "up"), 18); raw(("left",), 42); raw(("up",), 70); raw(("right", "up", "b"), 92)
    if state()[:3] != (1, 10, 172):
        raise RuntimeError(f"Crumbling-floor route failed: {state()}")
    raw(("up",), 70)
    for _ in range(100):
        raw(("left", "up"), 1)
        if state()[2] == 171:
            break
    raw((), 180)
    if state()[:3] != (1, 10, 171):
        raise RuntimeError(f"Stone room failed: {state()}")
    raw(("down",), 18)
    for direction, index in (("left", 0x37), ("down", 0x57)):
        before = list(env.pyboy.memory[0xD711:0xD791])
        raw((direction,), 64)
        after = list(env.pyboy.memory[0xD711:0xD791])
        if not block_changed(before, after, {"index": index}):
            raise RuntimeError(f"Push {direction} did not change block {index:02X}: {state()}")
        evidence.append(dict(kind="verified_block_push", index=index,
                             before=before[index], after=after[index], frame=env.frames))
    raw(("left",), 70); raw(("right",), 12); raw(("down",), 160)
    if state()[:3] != (0, 0, 80):
        raise RuntimeError(f"Overworld mushroom screen failed: {state()}")

    # Navigate to the live entity's local clearing, then walk through its
    # physical collision band.  The fourth one-frame down input starts its
    # 0x68-frame pickup animation at (36, 49); no inventory RAM is written.
    for _ in range(120):
        _, _, _, x, y, has_toadstool = state()
        if has_toadstool:
            break
        route = paths(terrain(env.pyboy), cell(x, y)).get((2, 3), [])
        if not route:
            raise RuntimeError(f"No local Toadstool route from {state()}")
        direction = steer(x, y, route[min(1, len(route) - 1)])
        if direction is not None:
            env.step_buttons(({1: "up", 2: "down", 3: "left", 4: "right"}[direction],),
                             action_frames=6, legacy_action=(direction, 0))
    raw(("up",), 32); raw(("left",), 48); raw(("down",), 22)
    pickup_started=False
    for _ in range(48):
        if int(env.pyboy.memory[0xC2E0]) == 0x68:
            pickup_started=True;break
        if state()[5]:pickup_started=True;break
        raw(("down",),1)
    if not pickup_started:
        raise RuntimeError(f'Toadstool collision did not trigger within 48 observed steps: {state()}')

    # Dialog00F is marked unskippable.  Let each text segment render before
    # one deliberate physical A pulse; only the game's final handler writes
    # wHasToadstool (DB4B).
    for _ in range(220):
        raw((), 1)
    for _ in range(5):
        if not int(env.pyboy.memory[0xC19F]):
            break
        raw((), 120); raw(("a",), 1); raw((), 24)
    for _ in range(80):
        if state()[5]:
            break
        raw((), 1)
    if state()[5] != 1:
        raise RuntimeError(f"Toadstool acquisition did not settle: {state()}")

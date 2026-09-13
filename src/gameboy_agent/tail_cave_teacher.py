"""State-checked physical teacher for Tail Cave's first Small Key."""
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_skills import dismiss_dialogue
from gameboy_agent.transitions import BUTTONS

HARDHAT_BEETLE = 0x20
KEY_DROP_POINT = 0x30
SMALL_KEYS = 0xDBD0


def entities(env, entity_type):
    memory = env.pyboy.memory
    return [dict(slot=index, type=int(memory[0xC3A0 + index]),
                 status=int(memory[0xC280 + index]), state=int(memory[0xC290 + index]),
                 x=int(memory[0xC200 + index]),
                 y=int(memory[0xC210 + index]))
            for index in range(16)
            if memory[0xC280 + index] and int(memory[0xC3A0 + index]) == entity_type]


def move_until(env, direction, predicate, *, budget=96, frames=3):
    for _ in range(budget):
        state = snapshot(env.pyboy)
        if predicate(state):
            return
        if not state['health']:
            raise RuntimeError(f'Tail Cave movement died in {state["room"]}')
        env.step_buttons([direction, 'b'], action_frames=frames)
    state = snapshot(env.pyboy)
    raise RuntimeError(f'Tail Cave movement stalled in {state["room"]} at {(state["x"],state["y"])}')


def enter_beetle_room(env, evidence):
    state = snapshot(env.pyboy)
    if state['room'] != [1, 0, 0x17] or not state['health']:
        raise RuntimeError(f'First-key stage requires living Tail Cave room 17, got {state["room"]}')
    env.step_input_events(release=BUTTONS, frames=1)
    # Depending on the preceding transition timing, the title can begin before
    # movement or several steps into this corridor.  Stop on either condition
    # so no movement command is repeated into an open dialogue.
    move_until(env, 'up', lambda s: s['dialog_state'] or s['y'] <= 92, budget=24)
    if snapshot(env.pyboy)['dialog_state']:
        result = dismiss_dialogue(env)
        if result['dialog_id'] != 0x56:
            raise RuntimeError(f'Unexpected Tail Cave entrance dialogue {result["dialog_id"]:03X}')
        evidence.append(dict(kind='tail_cave_title_dismissed', frame=env.frames, **result))
    # Room 17's entrance macro has directional threshold physics. These live
    # coordinate checks traverse its verified open corridor without treating
    # the threshold flags as general dungeon floor.
    move_until(env, 'up', lambda s: s['y'] <= 92, budget=16)
    move_until(env, 'left', lambda s: s['x'] <= 20, budget=32)
    move_until(env, 'right', lambda s: s['x'] >= 26, budget=8)
    move_until(env, 'up', lambda s: s['y'] <= 68, budget=16)
    move_until(env, 'left', lambda s: s['room'] != [1, 0, 0x17], budget=32)
    state = snapshot(env.pyboy)
    if state['room'] != [1, 0, 0x16]:
        raise RuntimeError(f'Unexpected Tail Cave entrance transition to {state["room"]}')
    env.step_input_events(release=BUTTONS, frames=60)
    active = entities(env, HARDHAT_BEETLE)
    if len(active) != 2:
        raise RuntimeError(f'Expected two active Hardhat Beetles, observed {len(active)}')
    evidence.append(dict(kind='tail_cave_beetle_room_entered', frame=env.frames,
                         health=state['health'], entities=active))


class BeetleTeacher:
    """One-command-at-a-time version of the verified pit-push policy."""

    def __init__(self):
        self.phase = None

    def action(self, state, targets):
        if self.phase == 'swing':
            self.phase = 'settle'
            return ['a'], 10
        if self.phase == 'settle':
            self.phase = None
            return [], 3
        target = min(targets, key=lambda e: abs(e['x']-state['x'])+abs(e['y']-state['y']))
        dx, dy = target['x']-state['x'], target['y']-state['y']
        push = 'up' if target['y'] <= 72 else 'down'
        stance_x = target['x']; stance_y = target['y'] + 24 if push == 'up' else target['y'] - 24
        if abs(dx)+abs(dy) <= 28:
            facing = (('right' if dx > 0 else 'left') if abs(dx) > abs(dy)
                      else ('down' if dy > 0 else 'up'))
            self.phase = 'swing'
            return [facing], 1
        if abs(stance_y-state['y']) > 5:
            return [('down' if stance_y > state['y'] else 'up'), 'b'], 1
        if abs(stance_x-state['x']) > 5:
            return [('right' if stance_x > state['x'] else 'left'), 'b'], 1
        self.phase = 'swing'
        return [push], 1


def defeat_beetles(env, evidence, *, budget=512):
    start_health = snapshot(env.pyboy)['health']
    teacher = BeetleTeacher()
    for decision in range(budget):
        state = snapshot(env.pyboy)
        if state['room'] != [1, 0, 0x16] or not state['health']:
            raise RuntimeError(f'Beetle teacher left living room-16 contract: {state["room"]}')
        targets = entities(env, HARDHAT_BEETLE)
        if not targets:
            evidence.append(dict(kind='tail_cave_beetles_defeated', frame=env.frames,
                                 decisions=decision, damage_raw=start_health-state['health']))
            return
        action, frames = teacher.action(state, targets)
        env.step_buttons(action, action_frames=frames)
    raise RuntimeError('Hardhat Beetle teacher exhausted 512-decision budget')


def collect_key(env, evidence, *, budget=256):
    initial = int(env.pyboy.memory[SMALL_KEYS])
    for decision in range(budget):
        state = snapshot(env.pyboy)
        if int(env.pyboy.memory[SMALL_KEYS]) > initial:
            if state['dialog_state']:
                dismiss_dialogue(env)
            evidence.append(dict(kind='tail_cave_first_key_collected', frame=env.frames,
                                 decisions=decision, small_keys=int(env.pyboy.memory[SMALL_KEYS])))
            return
        if state['room'] != [1, 0, 0x16] or not state['health']:
            raise RuntimeError(f'Key collection left living room-16 contract: {state["room"]}')
        drops = entities(env, KEY_DROP_POINT)
        if not drops:
            env.step_buttons([], action_frames=3)
            continue
        target = drops[0]; dx, dy = target['x']-state['x'], target['y']-state['y']
        direction = (('right' if dx > 0 else 'left') if abs(dx) > abs(dy)
                     else ('down' if dy > 0 else 'up'))
        env.step_buttons([direction, 'b'], action_frames=1)
    raise RuntimeError('Spawned first Small Key was not collected within 256 decisions')


def execute(env, evidence):
    if int(env.pyboy.memory[SMALL_KEYS]):
        raise RuntimeError('First-key teacher requires zero initial dungeon keys')
    enter_beetle_room(env, evidence)
    defeat_beetles(env, evidence)
    collect_key(env, evidence)
    state = snapshot(env.pyboy)
    if state['room'] != [1, 0, 0x16] or not state['health'] or int(env.pyboy.memory[SMALL_KEYS]) != 1:
        raise RuntimeError('First Small Key completion contract failed')

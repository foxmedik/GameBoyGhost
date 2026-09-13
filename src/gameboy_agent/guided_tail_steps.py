"""Bounded physical development steps; these are not a qualified teacher."""
from gameboy_agent.progression import snapshot


def walk(env, room, direction, predicate, budget=180):
    stagnant = 0
    for _ in range(budget):
        state = snapshot(env.pyboy)
        if state['room'] != [1, 0, room] or not state['health'] or state['dialog_state']:
            raise RuntimeError(f'Movement requires living room {room:02X} with closed dialogue: {state}')
        if predicate(state):
            return
        old = (state['x'], state['y'])
        env.step_buttons([direction], action_frames=1)
        new = snapshot(env.pyboy)
        stagnant = stagnant + 1 if old == (new['x'], new['y']) else 0
        if stagnant >= 12:
            raise RuntimeError(f'Blocked {direction} at {old} in room {room:02X}')
    raise RuntimeError('Movement budget exhausted')


def travel(env, room, direction, dest, budget=180):
    for _ in range(budget):
        state = snapshot(env.pyboy)
        if not state['health'] or state['dialog_state']:
            raise RuntimeError(f'Transition interrupted: {state}')
        if state['room'] == [1, 0, dest]:
            return
        if state['room'] != [1, 0, room]:
            raise RuntimeError(f'Transition expected {room:02X} -> {dest:02X}; got {state["room"]}')
        env.step_buttons([direction], action_frames=1)
    raise RuntimeError(f'Transition {room:02X} -> {dest:02X} budget exhausted')

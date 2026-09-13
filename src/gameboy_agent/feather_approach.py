"""Unqualified development controller for the room-1D spike-trap crossing.

Privileged observations are read-only. All movement goes through the supplied
trace wrapper. This controller is not approved for generating training labels.
"""
from gameboy_agent.progression import snapshot
from gameboy_agent.tail_cave_teacher import entities


def cross_feather_traps(env, evidence):
    initial = snapshot(env.pyboy)
    if (initial['room'] != [1, 0, 0x1D] or initial['health'] <= 0
            or initial['dialog_state'] or not 68 <= initial['x'] <= 76
            or not 114 <= initial['y'] <= 128):
        raise RuntimeError(f'Feather trap entry requires living room1D, x68..76, '
                           f'y114..128 and closed dialogue; got {initial}')
    health = initial['health']

    def observe():
        state = snapshot(env.pyboy)
        traps = sorted(entities(env, 0x27), key=lambda t: t['x'])
        if (state['room'] != [1, 0, 0x1D] or state['health'] != health
                or state['dialog_state'] or len(traps) != 2):
            raise RuntimeError(f'Feather trap contract interrupted: {state}; {traps}')
        return state, traps

    def phase(name, buttons, terminal, budget):
        for _ in range(budget):
            state, traps = observe()
            if terminal(state, traps):
                evidence.append(dict(kind=name, frame=env.frames,
                                     x=state['x'], y=state['y'], traps=traps))
                return
            env.step_buttons(buttons, action_frames=1)
        raise RuntimeError(f'Feather trap phase {name} exhausted {budget} commands')

    observe()
    phase('trap_bait', ['up'], lambda s, t: all(e['state'] == 2 for e in t), 24)
    phase('trap_retreat', ['down'], lambda s, t: s['y'] >= 122, 20)
    phase('traps_returning_outward', [],
          lambda s, t: all(e['state'] == 3 for e in t)
          and t[0]['x'] <= 48 and t[1]['x'] >= 112, 220)
    phase('trap_lane_crossed', ['up'], lambda s, t: s['y'] <= 68, 60)
    observe()

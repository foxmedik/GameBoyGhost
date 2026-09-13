"""State-checked Nightmare Key route development, not a qualified teacher.

The upper west entrance of 0F is required: its lower entrance is separated
from the north exit by solid blocks. No recorded action prefix is used here.
"""
from gameboy_agent.progression import snapshot, mode


class RouteBlocker(RuntimeError):
    pass


class RouteSteps:
    def __init__(self, env):
        self.env = env
        self.health = snapshot(env.pyboy)['health']

    def check(self, room):
        state = snapshot(self.env.pyboy)
        if state['room'] != [1, 0, room]:
            raise RouteBlocker(f'Expected room {room:02X}; got {state["room"]}')
        if not state['health'] or state['health'] < self.health:
            raise RouteBlocker(f'Health interrupted: {self.health} -> {state["health"]}')
        if mode(state) != 'world':
            raise RouteBlocker(f'Expected playable room {room:02X}; got {mode(state)}')
        return state

    def require(self, room, predicate, description):
        state = self.check(room)
        if not predicate(state):
            raise RouteBlocker(f'{description}; got {state}')

    def move(self, room, direction, done, *, jump=False, budget=180):
        self.check(room)
        if jump:
            if self.env.pyboy.memory[0xDB00] != 0x0A:
                raise RouteBlocker('Jump requires feather equipped on B')
            if self.env.pyboy.memory[0xFFA2] or self.env.pyboy.memory[0xC11C]:
                raise RouteBlocker('Jump requires grounded normal movement')
        stagnant = 0
        for index in range(budget):
            state = self.check(room)
            if done(state):
                self.env.step_buttons([], action_frames=1)
                self.check(room)
                return
            self.env.step_buttons([direction] + (['b'] if jump and index == 0 else []), action_frames=1)
            new = self.check(room)
            stagnant = stagnant + 1 if (state['x'], state['y']) == (new['x'], new['y']) else 0
            if stagnant >= 12:
                raise RouteBlocker(f'Blocked {direction} in {room:02X} at {(new["x"], new["y"])}')
        raise RouteBlocker(f'Movement budget exhausted in {room:02X}')

    def travel(self, room, direction, dest, budget=180):
        self.check(room)
        for _ in range(budget):
            self.env.step_buttons([direction], action_frames=1)
            state = snapshot(self.env.pyboy)
            if state['room'] == [1, 0, dest]:
                self.env.step_buttons([], action_frames=1)
                return self.check(dest)
            self.check(room)
        raise RouteBlocker(f'Transition budget exhausted: {room:02X} -> {dest:02X}')


def upper_staircase_approach(env):
    """Room08 south handoff -> room09 south entrance, pending reliability gate."""
    r = RouteSteps(env)
    r.require(0x08, lambda s: 68 <= s['x'] <= 82 and s['y'] >= 110,
              'Requires room08 lower south doorway lane')
    if env.pyboy.memory[0xDBD0] < 1 or env.pyboy.memory[0xDB00] != 0x0A:
        raise RouteBlocker('Approach requires a Small Key and feather on B')
    r.travel(0x08, 'down', 0x0E)
    r.move(0x0E, 'down', lambda s: s['y'] >= 27)
    r.move(0x0E, 'right', lambda s: s['x'] >= 111, jump=True)
    r.move(0x0E, 'right', lambda s: s['x'] >= 136)
    r.move(0x0E, 'down', lambda s: s['y'] >= 48)
    r.travel(0x0E, 'right', 0x0F)
    r.require(0x0F, lambda s: s['x'] <= 20 and 40 <= s['y'] <= 50,
              'Requires upper west entry, above the solid block barrier')
    r.move(0x0F, 'right', lambda s: s['x'] >= 25)
    r.move(0x0F, 'up', lambda s: s['y'] <= 32)
    r.move(0x0F, 'right', lambda s: s['x'] >= 120)
    return r.travel(0x0F, 'up', 0x09)


def acquire_nightmare_key(env):
    """Fresh room08 lower handoff through closed Nightmare Key receipt."""
    r = RouteSteps(env)
    r.check(0x08)
    if env.pyboy.memory[0xDBCF]:
        raise RouteBlocker('Nightmare Key already held; not a fresh acquisition')
    upper_staircase_approach(env)
    r.move(9, 'up', lambda s: s['y'] <= 96)
    r.move(9, 'left', lambda s: s['x'] <= 104)
    r.move(9, 'left', lambda s: s['x'] <= 64, jump=True)
    r.move(9, 'left', lambda s: s['x'] <= 55)
    keys = int(env.pyboy.memory[0xDBD0])
    if env.pyboy.memory[0xD711 + 0x52] != 0xDE:
        raise RouteBlocker('Expected closed staircase key block')
    for _ in range(120):
        r.check(9)
        if env.pyboy.memory[0xD711 + 0x52] != 0xDE:
            break
        env.step_buttons(['left'], action_frames=1)
    else:
        raise RouteBlocker('Staircase key block did not open')
    if env.pyboy.memory[0xDBD0] != keys - 1:
        raise RouteBlocker('Staircase unlock did not spend exactly one Small Key')
    r.move(9, 'left', lambda s: s['x'] <= 40)
    r.move(9, 'up', lambda s: s['y'] <= 48)
    r.travel(9, 'left', 8)
    r.move(8, 'left', lambda s: s['x'] <= 124)
    r.move(8, 'up', lambda s: s['y'] <= 32)
    r.move(8, 'left', lambda s: s['x'] <= 84)
    r.move(8, 'down', lambda s: s['y'] >= 40)
    r.move(8, 'left', lambda s: s['x'] <= 72)
    for index in range(40):
        r.check(8)
        if env.pyboy.memory[0xDBCF]:
            break
        env.step_buttons(['up'] + (['a'] if index == 0 else []), action_frames=1)
    else:
        raise RouteBlocker('Nightmare Key chest did not grant key')
    env.step_buttons([], action_frames=1)
    for _ in range(240):
        state = snapshot(env.pyboy)
        if state['room'] != [1, 0, 8] or state['health'] < r.health:
            raise RouteBlocker('Nightmare Key receipt interrupted')
        if state['dialog_state']:
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Nightmare Key receipt dialogue never appeared')
    from gameboy_agent.progression_skills import dismiss_dialogue
    dismiss_dialogue(env)
    final = r.check(8)
    if not env.pyboy.memory[0xDBCF]:
        raise RouteBlocker('Nightmare Key missing after receipt')
    return final

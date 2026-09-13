"""Bounded onward development helpers. Not a qualified route teacher."""
from gameboy_agent.nightmare_key_route import RouteSteps, RouteBlocker


def armed_move(env, room, direction, done, budget=500, reactive_stalfos=False):
    r = SafeRouteSteps(env) if reactive_stalfos else RouteSteps(env)
    r.check(room)
    if env.pyboy.memory[0xDB01] != 1:
        raise RouteBlocker('Armed passage requires sword on A')
    stagnant = 0
    for index in range(budget):
        state = r.check(room)
        if done(state):
            env.step_buttons([], action_frames=1)
            return r.check(room)
        m=env.pyboy.memory
        strike=(any(m[0xC280+i]==5 and m[0xC3A0+i]==30
                    and abs(int(m[0xC200+i])-state['x'])<36
                    and abs(int(m[0xC210+i])-state['y'])<36 for i in range(16))
                if reactive_stalfos else index%32==0)
        env.step_buttons([direction] + (['a'] if strike else []), action_frames=1)
        new = r.check(room)
        stagnant = stagnant + 1 if (state['x'], state['y']) == (new['x'], new['y']) else 0
        if stagnant >= 48:
            raise RouteBlocker(f'Armed passage blocked in {room:02X} at {(new["x"], new["y"])}')
    raise RouteBlocker('Armed passage budget exhausted')


class SafeRouteSteps(RouteSteps):
    """Reject a fall or buffered damage before treating positive HP as safe."""
    def check(self, room):
        state = super().check(room)
        if self.env.pyboy.memory[0xDB94]:
            raise RouteBlocker('Damage is still being applied; not a safe route state')
        if self.env.pyboy.memory[0xC11C] == 6:
            raise RouteBlocker('Link is falling into a pit; movement cannot recover this state')
        return state


def cross_room10(env):
    """Observe the outer Spark passing, use the interior lane, then jump east."""
    route = SafeRouteSteps(env)
    route.require(0x10, lambda s: s['x'] <= 20 and 68 <= s['y'] <= 76,
                  'Room10 crossing requires its west doorway')
    if not env.pyboy.memory[0xDBCF] or env.pyboy.memory[0xDB00] != 10:
        raise RouteBlocker('Room10 crossing requires Nightmare Key and feather B')
    route.move(16, 'right', lambda s: s['x'] >= 25)
    route.move(16, 'up', lambda s: s['y'] <= 32)
    route.move(16, 'right', lambda s: s['x'] >= 88)
    for _ in range(90):
        route.check(16)
        m = env.pyboy.memory
        sparks = [i for i in range(16) if m[0xC280+i] and m[0xC3A0+i] == 23]
        if len(sparks) != 1:
            raise RouteBlocker('Room10 requires one observed outer clockwise Spark')
        i = sparks[0]
        if m[0xC200+i] >= 120 and m[0xC210+i] <= 40 and 0 < m[0xC240+i] < 128:
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Outer Spark never cleared the northern turn')
    route.move(16, 'right', lambda s: s['x'] >= 104)
    route.move(16, 'down', lambda s: s['y'] >= 72)
    route.move(16, 'right', lambda s: s['x'] >= 140, jump=True)
    return route.travel(16, 'right', 17)

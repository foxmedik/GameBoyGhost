"""Guided post-miniboss development route, pending full-route qualification."""
from gameboy_agent.battle_ready_endpoint import open_battle_ready_door
from gameboy_agent.boss_door_route import SafeRouteSteps
from gameboy_agent.nightmare_key_route import RouteBlocker


def open_door_after_miniboss(env, evidence):
    r = SafeRouteSteps(env)
    r.require(17, lambda s: s['health'] == 24 and 76 <= s['x'] <= 84
              and 96 <= s['y'] <= 112, 'Requires full-health lower combat lane')
    m = env.pyboy.memory
    if not m[0xD911] & 32 or not m[0xDBCF] or list(m[0xDB00:0xDB02]) != [10, 1]:
        raise RouteBlocker('Requires cleared miniboss, Nightmare Key and battle loadout')
    for _ in range(90):
        r.check(17)
        if not m[0xC188] and not m[0xC18C] and not m[0xC18D]:
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Miniboss shutters did not settle')
    # Pass east of the central portal rather than walking into it.
    r.move(17, 'right', lambda s: s['x'] >= 104)
    r.move(17, 'up', lambda s: s['y'] <= 32)
    r.move(17, 'left', lambda s: s['x'] <= 80)
    r.travel(17, 'up', 11)
    r.move(11, 'up', lambda s: s['y'] <= 96, jump=True)
    for _ in range(40):
        r.check(11)
        if not m[0xFFA2] and not m[0xC11C]:
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Lower trap crossing did not land')
    r.move(11, 'left', lambda s: s['x'] <= 40)
    r.move(11, 'up', lambda s: s['y'] <= 48)
    r.move(11, 'right', lambda s: s['x'] >= 80)
    r.move(11, 'down', lambda s: s['y'] >= 52)

    def traps():
        r.check(11)
        if m[0xDB93] or list(m[0xDB00:0xDB02]) != [10, 1]:
            raise RouteBlocker('Trap approach health or loadout changed')
        ids = [i for i in range(16) if m[0xC280+i] and m[0xC3A0+i] == 39
               and m[0xC2C0+i] == 32 and m[0xC2B0+i] in (24, 136)]
        if len(ids) != 2:
            raise RouteBlocker('Expected two observed upper trap home anchors')
        return sorted(ids, key=lambda i: m[0xC2B0+i])

    for _ in range(240):
        ids = traps()
        if all(m[0xC290+i] == 1 and not m[0xC2E0+i] for i in ids):
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Upper traps did not become ready at home')
    r.move(11, 'up', lambda s: s['y'] <= 49, budget=8)
    for _ in range(12):
        ids = traps()
        if all(m[0xC290+i] == 2 for i in ids):
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Both upper traps did not charge')
    r.move(11, 'down', lambda s: s['y'] >= 52, budget=8)
    for _ in range(240):
        left, right = traps()
        if (m[0xC290+left] == m[0xC290+right] == 3
                and m[0xC200+left] <= 48 and m[0xC200+right] >= 112):
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Upper traps did not clear the central approach')
    evidence.append(dict(kind='upper_traps_returning_outward', frame=env.frames,
                         left_x=int(m[0xC200+left]), right_x=int(m[0xC200+right])))
    r.move(11, 'up', lambda s: s['y'] <= 32, budget=30)
    return open_battle_ready_door(env)

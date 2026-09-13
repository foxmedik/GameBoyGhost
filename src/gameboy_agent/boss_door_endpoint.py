"""Physical door-opening candidate; requires a live fixture before qualification.

Separate from the legacy progression journal to preserve old replay schemas.
"""
from gameboy_agent.nightmare_key_route import RouteSteps, RouteBlocker
from gameboy_agent.progression import snapshot


def open_boss_door(env, budget=240):
    route = RouteSteps(env)
    route.require(0x0B, lambda s: 76 <= s['x'] <= 83 and 24 <= s['y'] <= 40,
                  'Boss door requires centered north approach')
    memory = env.pyboy.memory
    if not memory[0xDBCF]:
        raise RouteBlocker('Boss door requires Nightmare Key')
    if memory[0xD90B] & 4:
        raise RouteBlocker('Boss door already open; no opening transition to prove')
    if memory[0xC188] or memory[0xDB94]:
        raise RouteBlocker('Boss door requires settled door and health state')
    initial = snapshot(env.pyboy)
    started = False
    opened_frame = None
    for _ in range(budget):
        state = snapshot(env.pyboy)
        if state['room'] != [1, 0, 0x0B] or state['health'] < initial['health'] or not state['health']:
            raise RouteBlocker('Door opening left antechamber or lost health')
        if state['dialog_state']:
            raise RouteBlocker('Unexpected dialogue during boss-door opening')
        if memory[0xC188] or memory[0xD90B] & 4:
            started = True
        if memory[0xD90B] & 4 and opened_frame is None:
            opened_frame = env.frames
        if started and opened_frame is not None and not memory[0xC188]:
            env.step_buttons([], action_frames=1)
            final = route.check(0x0B)
            if memory[0xDB94] or not memory[0xD90B] & 4:
                raise RouteBlocker('Door did not remain open with settled health')
            return dict(status='boss_door_opened_alive_outside', before=initial, after=final,
                        opened_frame=opened_frame, final_frame=env.frames)
        env.step_buttons([] if started else ['up'], action_frames=1)
    raise RouteBlocker('Boss-door opening budget exhausted')

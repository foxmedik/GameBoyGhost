"""Assembled guided final stages; qualification remains external and mandatory."""
from gameboy_agent.nightmare_key_route import acquire_nightmare_key
from gameboy_agent.nightmare_key_return import reach_rolling_bones
from gameboy_agent.rolling_bones_spacing import fight
from gameboy_agent.post_rolling_bones import open_door_after_miniboss
from gameboy_agent.battle_ready_endpoint import require_battle_ready
from gameboy_agent.progression import snapshot


def execute(env,evidence):
    for name,run in [
        ('nightmare_key',lambda:acquire_nightmare_key(env)),
        ('rolling_bones_arrival',lambda:reach_rolling_bones(env)),
        ('rolling_bones_defeated',lambda:fight(env,evidence)),
        ('boss_door_open',lambda:open_door_after_miniboss(env,evidence)),
    ]:
        run()
        evidence.append(dict(kind=name,frame=env.frames,state=snapshot(env.pyboy)))
    return require_battle_ready(env)

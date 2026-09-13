"""Full-health boss-door endpoint, version 2. Legacy endpoint remains unchanged."""
from gameboy_agent.boss_door_endpoint import open_boss_door
from gameboy_agent.progression import snapshot, mode
from gameboy_agent.nightmare_key_route import RouteBlocker


def require_battle_ready(env):
    state = snapshot(env.pyboy)
    if state['room'] != [1, 0, 0x0B]:
        raise RouteBlocker(f'Battle readiness requires boss antechamber 0B; got {state["room"]}')
    capacity = state['max_hearts'] * 8
    if capacity <= 0 or state['health'] != capacity:
        raise RouteBlocker(f'Full health required: {state["health"]}/{capacity} raw units')
    m = env.pyboy.memory
    if m[0xDB93] or m[0xDB94]:
        raise RouteBlocker('Health is still changing; wait for healing/damage to settle')
    if mode(state) != 'world' or state['dialog_state'] or m[0xC11C] or m[0xFFA2]:
        raise RouteBlocker('Battle readiness requires grounded playable state without dialogue')
    if state['inventory'][:2] != [10, 1]:
        raise RouteBlocker('Battle loadout requires feather B and sword A')
    return state


def open_battle_ready_door(env, budget=240):
    before = require_battle_ready(env)
    result = open_boss_door(env, budget=budget)
    after = require_battle_ready(env)
    return dict(result, status='boss_door_opened_full_health_ready',
                endpoint_version=2, before=before, after=after,
                health_capacity=after['max_hearts'] * 8)

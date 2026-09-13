"""Bounded physical inventory skill for the progression interface.

Slot/cursor senses are privileged read-only information. Every change is made
by the game's menu controls; no item is granted or slot edited by the skill.
"""
from gameboy_agent.progression import snapshot, mode


class InteractionFailure(RuntimeError):
    pass


def dismiss_dialogue(env, *, max_pulses=12):
    """Release movement and advance observed dialogue with bounded physical A.

    Waiting lets unskippable text render. The ID is evidence of an interruption,
    not a claim to have decoded its text or speaker.
    """
    from gameboy_agent.transitions import BUTTONS
    initial = snapshot(env.pyboy)
    if not initial['dialog_state']:
        return dict(status='absent', pulses=0)
    env.step_input_events(release=BUTTONS, frames=1)
    for count in range(max_pulses):
        env.step_input_events(frames=120)
        if not snapshot(env.pyboy)['dialog_state']:
            return dict(status='closed', dialog_id=initial['dialog_id'], pulses=count)
        env.step_input_events(['a'], frames=1, release_after=['a'])
        env.step_input_events(frames=1)
        if not snapshot(env.pyboy)['dialog_state']:
            return dict(status='closed', dialog_id=initial['dialog_id'], pulses=count+1)
    raise InteractionFailure(f'Dialogue {initial["dialog_id"]:03X} did not close within {max_pulses} pulses')


def equip_item(env, item, *, button='a', budget=40):
    if button not in ('a', 'b') or item not in range(1, 14) or item == 9:
        raise ValueError('Unsupported item/button; ocarina submenu requires a separate skill')
    start = env.total_steps
    slot = 1 if button == 'a' else 0
    initial = snapshot(env.pyboy)
    if item not in initial['inventory']:
        raise InteractionFailure('Requested item is not possessed')
    if mode(initial) not in ('world', 'inventory'):
        raise InteractionFailure('Equipping requires settled gameplay without dialogue or an inventory screen')

    def pulse(key):
        if env.total_steps - start + 2 > budget:
            raise InteractionFailure('Equip decision budget exhausted')
        for keys in ([key], []):
            _, _, terminated, truncated, _ = env.step_buttons(keys, action_frames=1)
            if terminated or truncated:
                raise InteractionFailure('Episode ended during equipping')

    if initial['inventory'][slot] != item:
        if mode(initial) == 'world':
            pulse('start')
        if mode(snapshot(env.pyboy)) != 'inventory':
            raise InteractionFailure('Inventory did not open')
        # An item on the other active button must first be placed in the pack.
        current = snapshot(env.pyboy)
        other = 1 - slot
        if current['inventory'][other] == item:
            pulse('a' if other == 1 else 'b')
        current = snapshot(env.pyboy)
        target = current['inventory'].index(item) - 2
        if target < 0:
            raise InteractionFailure('Item did not enter the inventory pack')
        for _ in range(10):
            current = snapshot(env.pyboy)
            if current['inventory_cursor'] == target:
                break
            pulse('right')
        else:
            raise InteractionFailure('Inventory cursor did not reach the item')
        pulse(button)
        if snapshot(env.pyboy)['inventory'][slot] != item:
            raise InteractionFailure('Physical equip did not put the item on the requested button')
    if mode(snapshot(env.pyboy)) == 'inventory':
        pulse('start')
    final = snapshot(env.pyboy)
    if mode(final) != 'world' or final['inventory'][slot] != item:
        raise InteractionFailure('Equip skill did not return to gameplay with the requested item')
    return dict(status='succeeded', item=item, button=button, decisions=env.total_steps-start)

"""Observation and action vocabulary for the autonomous room-15 experiment."""
import numpy as np


ACTIONS = ((('b',), 1), (('left', 'b'), 1), (('up', 'b'), 1),
           (('down', 'b'), 1), (('left', 'a'), 10), (('up', 'a'), 10),
           (('a',), 1), ((), 1), ((), 3))


def action_index(command):
    item = (tuple(command.get('buttons', ())), command.get('action_frames', 1))
    return ACTIONS.index(item) if item in ACTIONS else None


def action_command(index):
    buttons, frames = ACTIONS[index]
    return list(buttons), frames


def feature(observation, history=()):
    state = observation['state']
    values = [state['x'] / 160, state['y'] / 144, state['health'] / 24]
    by_slot = {entity['slot']: entity for entity in observation['entities']}
    for slot in range(16):
        entity = by_slot.get(slot)
        if entity is None:
            values.extend((0,) * 8)
            continue
        vx = entity['vx'] if entity['vx'] < 128 else entity['vx'] - 256
        vy = entity['vy'] if entity['vy'] < 128 else entity['vy'] - 256
        values.extend((1, entity['type'] / 255, entity['status'] / 5, entity['state'] / 255,
                       (entity['x'] - state['x']) / 160, (entity['y'] - state['y']) / 144,
                       vx / 32, vy / 32))
    padded = [0] * (4 - len(history)) + list(history[-4:])
    values.extend(index / (len(ACTIONS) - 1) for index in padded)
    return np.asarray(values, dtype=np.float32)

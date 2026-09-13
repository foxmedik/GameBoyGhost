"""V4 action vocabulary: temporal observability plus an explicit wait macro."""
import numpy as np

from gameboy_agent.room15_model import feature as spatial_feature


ACTIONS = ((('b',), 1), (('left', 'b'), 1), (('up', 'b'), 1),
           (('down', 'b'), 1), (('left', 'a'), 10), (('up', 'a'), 10),
           (('a',), 1), ((), 1), ((), 3), ((), 120))


def action_index(command):
    item = (tuple(command.get('buttons', ())), command.get('action_frames', 1))
    return ACTIONS.index(item) if item in ACTIONS else None


def action_command(index):
    buttons, frames = ACTIONS[index]
    return list(buttons), frames


def intent(action):
    buttons, _ = ACTIONS[action]
    return ({'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
            .get(next((button for button in buttons if button in ('left', 'right', 'up', 'down')), None), (0, 0)))


def temporal_feature(observation, history=()):
    values = list(spatial_feature(observation, ()))
    padded = [(0, 0, 0)] * (6 - len(history)) + list(history[-6:])
    for action, dx, dy in padded:
        ix, iy = intent(action)
        values.extend((action / (len(ACTIONS) - 1), ix, iy, dx / 16, dy / 16,
                       float(ix != 0 or iy != 0) * float(dx == 0 and dy == 0)))
    return np.asarray(values, dtype=np.float32)


def update(history, action, before, after):
    return list(history[-5:]) + [(action, after['x'] - before['x'], after['y'] - before['y'])]

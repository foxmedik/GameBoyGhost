"""Temporal observability features for room-15 blocked-intent detection."""
import numpy as np

from gameboy_agent.room15_model import ACTIONS, feature as spatial_feature


def intent(action):
    """Requested directional displacement, independent of whether it occurred."""
    buttons, _ = ACTIONS[action]
    return ({'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
            .get(next((button for button in buttons if button in ('left', 'right', 'up', 'down')), None), (0, 0)))


def temporal_feature(observation, history=()):
    """Current spatial state plus six action/result pairs.

    Each history item is ``(action, dx, dy)`` where dx/dy are the observed
    displacement after that action. This makes a blocked request explicit:
    repeated Down intent paired with zero observed dy differs from stationary
    sword combat, which carries no directional intent.
    """
    values = list(spatial_feature(observation, ()))
    padded = [(0, 0, 0)] * (6 - len(history)) + list(history[-6:])
    for action, dx, dy in padded:
        ix, iy = intent(action)
        values.extend((action / (len(ACTIONS) - 1), ix, iy, dx / 16, dy / 16,
                       float(ix != 0 or iy != 0) * float(dx == 0 and dy == 0)))
    return np.asarray(values, dtype=np.float32)


def update(history, action, before, after):
    return list(history[-5:]) + [(action, after['x'] - before['x'], after['y'] - before['y'])]

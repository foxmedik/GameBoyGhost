"""Read-only geometry for bounded room-15 projectile recovery."""


class BypassRecovery:
    """Follow the lower chest corridor, with two bounded blocked-step escapes."""

    def __init__(self):
        self.previous = None
        self.stalled = 0
        self.escapes = 0
        self.escape_remaining = 0
        self.escape_direction = None
        self.waited_for_animation = False

    def action(self, state):
        position = (state['x'], state['y'])
        self.stalled = self.stalled + 1 if position == self.previous else 0
        self.previous = position
        # The eastern lower wall stops Link at y=80. y=92 is unreachable here.
        direction = 'down' if state['y'] < 80 else 'left'
        if state['x'] < 88 and state['y'] < 80:
            direction = 'right'
        if self.stalled >= 12 and not self.escape_remaining:
            if not self.waited_for_animation:
                # A combat pickup can freeze actors before dialog_state rises.
                # Give that transition a bounded window before trying geometry.
                self.waited_for_animation = True
                self.escape_remaining = 64
                self.escape_direction = None
                self.stalled = 0
            else:
                if self.escapes >= 2:
                    raise RuntimeError(f'Room-15 bypass blocked at {position} after two recovery attempts')
                self.escapes += 1
                self.escape_remaining = 8
                self.escape_direction = 'left' if direction == 'down' else 'down'
                self.stalled = 0
        recovering = bool(self.escape_remaining)
        if recovering:
            self.escape_remaining -= 1
            direction = self.escape_direction
        return direction, recovering


def projectile_threat(state, shots):
    """Return the most imminent shot crossing Link's collision neighbourhood.

    Entity velocities are signed sixteenth-pixels per frame. Ignore receding
    shots and paths that miss, rather than treating every shot above as lethal.
    """
    threats = []
    for shot in shots:
        vx, vy = (shot[k] if shot[k] < 128 else shot[k] - 256 for k in ('vx', 'vy'))
        vx, vy = vx / 16, vy / 16
        dx, dy = shot['x'] - state['x'], shot['y'] - state['y']
        speed = vx * vx + vy * vy
        if not speed:
            continue
        t = -(dx * vx + dy * vy) / speed
        if not 0 <= t <= 24:
            continue
        if (dx + vx * t) ** 2 + (dy + vy * t) ** 2 > 14 ** 2:
            continue
        direction = ('left' if vx > 0 else 'right') if abs(vx) > abs(vy) else ('up' if vy > 0 else 'down')
        threats.append((t, shot['slot'], direction))
    return min(threats)[2] if threats else None

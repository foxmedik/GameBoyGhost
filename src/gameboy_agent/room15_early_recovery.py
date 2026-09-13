"""Bounded, state-checked early intervention for y=80 recovery diagnosis."""


class EarlyY80Recovery:
    """Request a leftward shielded bypass before a stationary y=80 loop becomes terminal.

    This is a guided diagnostic controller, not an autonomous student policy.
    It deliberately exposes every intervention to the caller for later correction
    collection and must never be used to score an autonomous candidate.
    """
    def __init__(self, *, stall_limit=12, left_steps=24):
        self.previous = None
        self.stationary = 0
        self.remaining = 0
        self.stall_limit = stall_limit
        self.left_steps = left_steps
        self.interventions = 0

    def action(self, state):
        position = (state['x'], state['y'])
        self.stationary = self.stationary + 1 if position == self.previous else 0
        self.previous = position
        if self.remaining:
            self.remaining -= 1
            return ['left', 'b'], True
        if 80 <= state['y'] <= 84 and self.stationary >= self.stall_limit:
            self.remaining = self.left_steps - 1
            self.interventions += 1
            self.stationary = 0
            return ['left', 'b'], True
        return None, False

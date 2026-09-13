"""Explicit recovery for Hardhat Beetle right-wall pins."""
from gameboy_agent.tail_cave_teacher import BeetleTeacher


class DisengagingBeetleTeacher(BeetleTeacher):
    """Back away behind the shield before resuming the pit-push teacher."""

    def action(self, state, targets):
        nearest = min(abs(target['x'] - state['x']) + abs(target['y'] - state['y'])
                      for target in targets)
        if state['x'] > 132 and nearest <= 40:
            self.phase = None
            return ['left', 'b'], 3
        return super().action(state, targets)

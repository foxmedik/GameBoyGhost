"""Bounded skills and an explicit two-stage research planner.

The planner is scripted, not a general game planner. Exploration uses visited
positions and observed movement failures, without a game route or reward signal.
"""
from dataclasses import asdict, dataclass, field
from typing import Callable, Protocol


@dataclass(frozen=True)
class Senses:
    room: tuple[int, int, int]
    x: int
    y: int
    dialogue: bool
    sword: bool
    health: int
    a_item: int
    b_item: int

    @property
    def cell(self):
        return ':'.join(map(str, (*self.room, self.x // 8, self.y // 8)))


class Controller(Protocol):
    def action(self, senses: Senses) -> list[int]: ...


@dataclass
class Skill:
    name: str
    controller: Controller
    success: Callable[[Senses], bool]
    budget: int
    steps: int = 0

    def status(self, senses):
        # Death takes precedence over a coincident objective flag.
        if senses.health == 0:
            return 'failed_death'
        if self.success(senses):
            return 'succeeded'
        if self.steps >= self.budget:
            return 'budget_exhausted'
        return 'running'


@dataclass
class Explorer:
    visits: dict = field(default_factory=dict)
    attempts: dict = field(default_factory=dict)
    blocked: dict = field(default_factory=dict)
    previous: dict | None = None
    last_direction: int = 0
    ticks: int = 0
    remaining: int = 0
    stalled: int = 0
    hazards: dict = field(default_factory=dict)

    def action(self, senses):
        self.ticks += 1
        # Alternate press/release: holding A does not dismiss successive text.
        if senses.dialogue:
            self.previous = None
            self.remaining = 0
            return [0, self.ticks % 2]
        key = senses.cell
        damaged = False
        if self.previous:
            prev = self.previous
            damaged = senses.health < prev['health']
            if damaged:
                self.hazards[key] = self.hazards.get(key, 0) + 1
            moved = (list(senses.room) != prev['room'] or
                     abs(senses.x - prev['x']) + abs(senses.y - prev['y']) >= 1)
            self.stalled = 0 if moved else self.stalled + 1
            if self.stalled >= 3:
                edge = prev['edge']
                self.blocked[edge] = self.blocked.get(edge, 0) + 1
                self.remaining = 0
        self.visits[key] = self.visits.get(key, 0) + 1
        # Candidate cells use local screen coordinates. Actual room transitions
        # are learned from observations; no overworld map arithmetic is assumed.
        candidates = []
        for direction, dx, dy in ((1, 0, -1), (2, 0, 1), (3, -1, 0), (4, 1, 0)):
            target = ':'.join(map(str, (*senses.room, senses.x // 8 + dx, senses.y // 8 + dy)))
            edge = f'{key}/{direction}'
            score = (self.visits.get(target, 0) + 2 * self.attempts.get(edge, 0)
                     + 12 * self.blocked.get(edge, 0)
                     + 24 * self.hazards.get(target, 0)
                     - (0.4 if direction == self.last_direction else 0))
            candidates.append((score, direction, edge))
        if damaged:
            direction = {1: 2, 2: 1, 3: 4, 4: 3}[self.last_direction]
            edge = f'{key}/{direction}'
            self.remaining = 3
        elif self.remaining > 0:
            direction = self.last_direction
            edge = f'{key}/{direction}'
            self.remaining -= 1
        else:
            _, direction, edge = min(candidates)
            # Commit long enough to cross a cell even during sword animation.
            self.remaining = 7
            self.stalled = 0
        self.attempts[edge] = self.attempts.get(edge, 0) + 1
        self.previous = dict(room=list(senses.room), x=senses.x, y=senses.y,
                             edge=edge, health=senses.health)
        self.last_direction = direction
        # Sword is item 1 in this adapter. Only press its existing physical slot;
        # do not invoke the inherited inventory-switch RAM action.
        button = (1 if senses.a_item == 1 else 2 if senses.b_item == 1 else 0)
        return [direction, button if self.ticks % 2 else 0]

    def state(self):
        return asdict(self)


class SequentialPlanner:
    """Explicit scripted prerequisite selection with bounded failure handling."""

    def __init__(self, sword_controller, *, sword_budget=1600, explore_budget=2000):
        self.explorer = Explorer()
        self.skills = [Skill('acquire_sword', sword_controller, lambda s: s.sword, sword_budget),
                       Skill('explore', self.explorer, lambda s: False, explore_budget)]
        self.index = 0
        self.events = []

    def action(self, senses, step):
        skill = self.skills[self.index]
        status = skill.status(senses)
        if status != 'running':
            self.events.append(dict(step=step, skill=skill.name, status=status, steps=skill.steps))
            if status != 'succeeded' or self.index + 1 == len(self.skills):
                return None
            self.index += 1
            skill = self.skills[self.index]
            self.events.append(dict(step=step, skill=skill.name, status='started', steps=0))
        action = skill.controller.action(senses)
        skill.steps += 1
        return action

    def state(self):
        return dict(index=self.index, steps=[s.steps for s in self.skills],
                    events=self.events, explorer=self.explorer.state())

"""State-checked progression beyond Tail Cave's first Small Key."""

from gameboy_agent.progression import snapshot
from gameboy_agent.progression_skills import dismiss_dialogue
from gameboy_agent.tail_cave_teacher import SMALL_KEYS, entities, move_until
from gameboy_agent.transitions import BUTTONS
from gameboy_agent.room15_recovery import BypassRecovery, projectile_threat

GEL = 0x9B
FIREBALL = 0x7D


def projectile_direction(env, state):
    shots = entities(env, FIREBALL)
    for shot in shots:
        shot['vx'] = int(env.pyboy.memory[0xC240 + shot['slot']])
        shot['vy'] = int(env.pyboy.memory[0xC250 + shot['slot']])
    return projectile_threat(state, shots)


class GelTeacher:
    """Approach the nearest live Gel behind the shield, then swing once close."""

    def __init__(self):
        self.phase = None

    def action(self, state, targets):
        if self.phase == "settle":
            self.phase = None
            return [], 3
        target = min(
            targets,
            key=lambda entity: abs(entity["x"] - state["x"])
            + abs(entity["y"] - state["y"]),
        )
        dx, dy = target["x"] - state["x"], target["y"] - state["y"]
        direction = (
            ("right" if dx > 0 else "left")
            if abs(dx) > abs(dy)
            else ("down" if dy > 0 else "up")
        )
        distance = abs(dx) + abs(dy)
        # A hiding Zol emerges after Link enters its trigger radius.  Wait
        # behind the already-facing shield during the noninteractive rise,
        # then swing as soon as its damaging state begins.
        if distance <= 28 and target.get("state", 4) < 4:
            return ["b"], 1
        if distance <= 28:
            self.phase = "settle"
            return [direction, "a"], 10
        return [direction, "b"], 1


def enter_compass_room(env, evidence):
    state = snapshot(env.pyboy)
    if (
        state["room"] != [1, 0, 0x16]
        or not state["health"]
        or int(env.pyboy.memory[SMALL_KEYS]) != 1
    ):
        raise RuntimeError(
            "Compass-room stage requires living Tail Cave room 16 with exactly "
            f"one Small Key, got room={state['room']} health={state['health']} "
            f"keys={int(env.pyboy.memory[SMALL_KEYS])}"
        )
    env.step_input_events(release=BUTTONS, frames=1)
    move_until(env, "down" if state["y"] < 68 else "up", lambda s: abs(s["y"] - 68) <= 1,
               budget=32, frames=1)
    move_until(env, "left", lambda s: s["room"] != [1, 0, 0x16], budget=64)
    state = snapshot(env.pyboy)
    if state["room"] != [1, 0, 0x15] or not state["health"]:
        raise RuntimeError(f"Expected living Tail Cave room 15, got {state['room']}")
    env.step_input_events(release=BUTTONS, frames=60)
    active = entities(env, GEL)
    if len(active) != 4:
        raise RuntimeError(f"Expected four active room-15 Gels, observed {len(active)}")
    evidence.append(
        dict(kind="tail_cave_compass_room_entered", frame=env.frames,
             health=state["health"], entities=active)
    )


def clear_compass_room(env, evidence, *, budget=512):
    initial_health = snapshot(env.pyboy)["health"]
    teacher = GelTeacher()
    guard_facing = None
    bypass_recovery = BypassRecovery()
    for decision in range(budget):
        state = snapshot(env.pyboy)
        if state["room"] != [1, 0, 0x15] or not state["health"]:
            raise RuntimeError(f"Gel teacher left living room-15 contract: {state['room']}")
        if state["dialog_state"]:
            result = dismiss_dialogue(env)
            bypass_recovery = BypassRecovery()
            evidence.append(
                dict(kind="tail_cave_combat_pickup_dialogue_dismissed", frame=env.frames,
                     **result)
            )
            continue
        targets = entities(env, GEL)
        if not targets:
            # Block any projectile already in flight while the room-clear
            # trigger disables the statues and opens the door.
            for _ in range(96):
                state = snapshot(env.pyboy)
                if not state["health"]:
                    raise RuntimeError("Room-15 clear animation ended after lethal projectile damage")
                shots = entities(env, FIREBALL)
                if not shots:
                    break
                direction = projectile_direction(env, state)
                env.step_buttons([direction, 'b'] if direction and direction != guard_facing else ['b'], action_frames=1)
                guard_facing = direction
            state = snapshot(env.pyboy)
            evidence.append(
                dict(kind="tail_cave_compass_room_cleared", frame=env.frames,
                     decisions=decision, damage_raw=initial_health-state["health"])
            )
            return
        direction = projectile_direction(env, state)
        if direction:
            env.step_buttons([direction, 'b'] if direction != guard_facing else ['b'], action_frames=1)
            guard_facing = direction
            continue
        guard_facing = None
        if max(target["x"] for target in targets) <= 48 and state["x"] >= 70:
            # The central chest plinth blocks a direct path to the left pair.
            # Walk around its lower edge using live coordinates.
            bypass, recovering = bypass_recovery.action(state)
            if recovering:
                evidence.append(dict(kind='room15_bypass_recovery', frame=env.frames,
                                     x=state['x'], y=state['y'], direction=bypass,
                                     attempt=bypass_recovery.escapes))
            env.step_buttons([bypass, "b"] if bypass else ['b'], action_frames=1)
            continue
        bypass_recovery = BypassRecovery()
        buttons, frames = teacher.action(state, targets)
        env.step_buttons(buttons, action_frames=frames)
    state = snapshot(env.pyboy)
    raise RuntimeError(f"Room-15 teacher exhausted {budget}-decision budget at "
                       f"{(state['x'], state['y'])}; remaining targets={entities(env, GEL)}")


def execute_compass_room(env, evidence):
    enter_compass_room(env, evidence)
    clear_compass_room(env, evidence)
    state = snapshot(env.pyboy)
    if state["room"] != [1, 0, 0x15] or not state["health"] or entities(env, GEL):
        raise RuntimeError("Compass-room clear completion contract failed")

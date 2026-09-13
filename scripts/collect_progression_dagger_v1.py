"""Collect room-52 teacher recoveries from candidate-created development states."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np

from control_context import ControlContext
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.navigation import NavigationController, encode
from gameboy_agent.progression import mode, snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.terrain_navigation import cell, exits, paths, steer_path, terrain
from gameboy_agent.world_memory import file_hash
from progression_local_control import json_state
from run_toadstool_progression import Trace, apply


PLAN = ROOT / "configs/progression_dagger_v1_collection_v2.json"
DURATIONS = (1, 3, 10)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def action_tuple(command):
    movement = next(({"up": 1, "down": 2, "left": 3, "right": 4}[b]
                     for b in command.get("buttons", []) if b in ("up", "down", "left", "right")), 0)
    button = 1 if "a" in command.get("buttons", []) else 2 if "b" in command.get("buttons", []) else 0
    duration = min(range(len(DURATIONS)), key=lambda i: abs(DURATIONS[i] - command.get("action_frames", 3)))
    return movement, button, duration


def history_features(commands, length=4):
    values = [action_tuple(command) for command in commands[-length:]]
    values = [(0, 0, 1)] * (length - len(values)) + values
    scale = np.asarray([4.0, 2.0, 2.0] * length, dtype=np.float32)
    return np.asarray(values, dtype=np.float32).reshape(-1) / scale


def frozen_goal(env):
    state = json_state(snapshot(env.pyboy))
    candidates = [candidate for candidate in exits(terrain(env.pyboy), cell(state["x"], state["y"]), 0x52)
                  if candidate["direction"] == 2]
    interior = [candidate for candidate in candidates if candidate["cell"][0] not in (0, 9)]
    if not candidates:
        raise RuntimeError("No southern room-52 goal at the frozen arrival")
    chosen = min(interior or candidates, key=lambda candidate: len(candidate["path"]))
    return {"room": [0, 0, 0x62], "x": chosen["cell"][0] * 16 + 8,
            "y": chosen["cell"][1] * 16 + 12, "cell": chosen["cell"]}


def feature(base, context, state, goal):
    observation = context.observation(base.get_observation())
    return np.concatenate([encode(observation, state["room"], goal["room"], goal["x"], goal["y"]),
                           history_features(base.episode_actions)]).astype(np.float32)


def buttons(action):
    movement = (None, "up", "down", "left", "right")[action[0]]
    button = (None, "a", "b")[action[1]]
    return [value for value in (movement, button) if value]


def teacher_action(base, goal, recovery_index):
    state = json_state(snapshot(base.pyboy))
    if cell(state["x"], state["y"]) == tuple(goal["cell"]):
        # Reaching the boundary cell completes approach; continue outward
        # instead of steering back to the cell centre.
        return [2, 2, 1]
    route = paths(terrain(base.pyboy), cell(state["x"], state["y"])).get(tuple(goal["cell"]))
    if route is None:
        direction = (3, 4, 1, 2)[recovery_index % 4]
        return [direction, 2, 1]
    waypoint = route[0] if route else goal["cell"]
    direction = steer_path(state["x"], state["y"], waypoint)
    if direction is None:
        direction = 2
    memory = base.pyboy.memory
    hostiles = [(int(memory[0xC200+i])-state["x"], int(memory[0xC210+i])-state["y"])
                for i in range(16) if memory[0xC280+i] and memory[0xC3A0+i] in (0x09, 0x0B, 0x14, 0x1B, 0xC5)]
    near = [enemy for enemy in hostiles if abs(enemy[0]) + abs(enemy[1]) <= 24]
    if near and state["inventory"][1] == 1:
        dx, dy = min(near, key=lambda enemy: abs(enemy[0]) + abs(enemy[1]))
        face = 4 if abs(dx) > abs(dy) and dx > 0 else 3 if abs(dx) > abs(dy) else 2 if dy > 0 else 1
        return [face, 1, 2]
    return [direction, 2, 1]


def collect_case(root, spec, plan):
    source = ROOT / plan["source_teacher"] / spec["source_case"]
    out = root / spec["id"]
    out.mkdir(parents=True, exist_ok=False)
    for name in ("game.gbc", "initial.state"):
        shutil.copy2(source / name, out / name)
    manifest = json.loads((source / "manifest.json").read_text())
    for name, expected in manifest["artifacts"].items():
        if file_hash(source / name) != expected:
            raise ValueError(f"Teacher source changed: {spec['source_case']}/{name}")
    source_rows = [json.loads(line) for line in (source / "trajectory.jsonl").read_text().splitlines()]
    start = next(i for i, row in enumerate(source_rows) if row["before"]["room"] == [0, 0, 0x52]
                 and not row["before"]["toadstool"] and not row["before"]["powder"])
    base = ProgressionEnv(out / "game.gbc", out / "initial.state", max_steps=12288, max_frames=300000)
    rows, samples, failure = [], [], None
    began = time.monotonic()
    with (out / "trajectory.jsonl").open("x") as stream:
        env = Trace(base, stream, rows)
        try:
            base.reset(seed=0)
            for row in source_rows[:start]:
                apply(env, row["command"])
                if rows[-1]["fingerprint"] != row["fingerprint"]:
                    raise RuntimeError(f"Source prefix changed at {row['decision']}")
            if spec["arrival_idle_frames"]:
                env.step_input_events(release=("up", "down", "left", "right", "a", "b", "start", "select"),
                                      frames=spec["arrival_idle_frames"])
            goal = frozen_goal(base)
            controller = NavigationController(ROOT / plan["candidate"])
            context = ControlContext(base)
            previous, stationary = None, 0
            for _ in range(spec["learner_steps"]):
                state = json_state(snapshot(base.pyboy))
                if state["room"] != [0, 0, 0x52] or not state["health"]:
                    break
                action = controller.action(context.observation(base.get_observation()), state["room"], goal)
                env.step_buttons(buttons(action), action_frames=3, legacy_action=action)
                now = json_state(snapshot(base.pyboy)); pose = (now["x"], now["y"])
                stationary = stationary + 1 if pose == previous else 0; previous = pose
                if stationary >= 12:
                    break
            teacher_start = len(rows)
            previous, stationary, recoveries = None, 0, 0
            for _ in range(plan["teacher_budget"]):
                state = json_state(snapshot(base.pyboy))
                if state["room"] == [0, 0, 0x62]:
                    break
                if state["room"] != [0, 0, 0x52] or not state["health"]:
                    raise RuntimeError(f"Teacher cannot recover from {state['room']} health {state['health']}")
                action = teacher_action(base, goal, recoveries)
                samples.append((feature(base, context, state, goal), action,
                                [spec["id"], base.total_steps]))
                env.step_buttons(buttons(action), action_frames=DURATIONS[action[2]], legacy_action=action[:2])
                now = json_state(snapshot(base.pyboy)); pose = (now["x"], now["y"])
                stationary = stationary + 1 if pose == previous else 0; previous = pose
                if stationary >= 12:
                    recoveries += 1; stationary = 0
                    if recoveries > 4:
                        raise RuntimeError(f"Teacher stalled at {pose}")
            else:
                raise RuntimeError("Teacher recovery budget exhausted")
            if json_state(snapshot(base.pyboy))["room"] != [0, 0, 0x62]:
                raise RuntimeError("Teacher did not complete the southern crossing")
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
        finally:
            final = json_state(snapshot(base.pyboy)); journal = deepcopy(base.journal.state()); base.close()
    replay = ProgressionEnv(out / "game.gbc", out / "initial.state", max_steps=12288, max_frames=300000)
    try:
        replay.reset(seed=0)
        for row in rows:
            info = apply(replay, row["command"])[4]
            assert fingerprint(replay) == row["fingerprint"]
            assert json_state(snapshot(replay.pyboy)) == json_state(row["after"])
            assert replay.frames == row["frame"] and info["events"] == row["events"]
        assert replay.journal.state() == journal
    finally:
        replay.close()
    if samples:
        np.savez_compressed(out / "corrections.npz", x=np.stack([s[0] for s in samples]),
                            y=np.asarray([s[1] for s in samples], dtype=np.int64),
                            provenance=np.asarray([s[2] for s in samples]))
    result = {"spec": spec, "success": failure is None, "failure": failure,
              "source_prefix_decisions": start, "learner_decisions": teacher_start - start,
              "teacher_decisions": len(samples), "final": final, "exact_replay": True,
              "damage_raw": journal["damage_raw"], "healing_raw": journal["healing_raw"],
              "seconds": round(time.monotonic() - began, 3)}
    write(out / "result.json", result)
    write(out / "manifest.json", {"artifacts": {path.name: file_hash(path) for path in out.iterdir()
                                                  if path.is_file() and path.name != "game.gbc"}})
    print(json.dumps(result), flush=True)
    return result


def main(out):
    plan = json.loads(PLAN.read_text())
    if "specification_source" in plan:
        source = ROOT / plan["specification_source"]
        if file_hash(source) != plan["specification_source_sha256"]:
            raise ValueError("Frozen DAgger specifications changed")
        frozen = json.loads(source.read_text())
        plan["collection_specs"] = frozen["collection_specs"]
        plan["development_panel"] = frozen["development_panel"]
    if file_hash(Path(__file__)) != plan["collector_sha256"]:
        raise ValueError("Frozen DAgger collector changed")
    if file_hash(ROOT / plan["candidate"]) != plan["candidate_sha256"]:
        raise ValueError("Frozen inducing candidate changed")
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(PLAN, out / "plan.json")
    shutil.copy2(Path(__file__), out / "collector-source.py")
    results = []
    for spec in plan["collection_specs"]:
        results.append(collect_case(out, spec, plan))
        write(out / "summary.json", {"cases": len(results), "successes": sum(r["success"] for r in results),
                                     "required_successes": plan["teacher_required_successes"],
                                     "correction_rows": sum(r["teacher_decisions"] for r in results),
                                     "results": results, "validation_loaded": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--out", type=Path, required=True)
    main(parser.parse_args().out)

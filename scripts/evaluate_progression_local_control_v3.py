"""Frozen live arrival evaluation for progression local-control candidate 3."""
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

from control_context import ControlContext
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.navigation import NavigationController
from gameboy_agent.progression import mode, snapshot
from gameboy_agent.progression_contracts import adjacent_direction
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression_skills import dismiss_dialogue
from gameboy_agent.terrain_navigation import cell, exits, terrain
from gameboy_agent.world_memory import file_hash
from progression_local_control import command_label, destination, json_state
from run_toadstool_progression import Trace, apply


PLAN = ROOT / "configs/progression_local_control_v3_live_panel_v2.json"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def matches(state, stage):
    if stage == "mushroom_52_to_62":
        return state["room"] == [0, 0, 0x52] and not state["toadstool"] and not state["powder"] and not state["tarin"]
    if stage == "witch_52_to_42":
        return state["room"] == [0, 0, 0x52] and bool(state["toadstool"])
    if stage == "witch_42_to_43":
        return state["room"] == [0, 0, 0x42] and bool(state["toadstool"])
    if stage == "tarin_42_to_52":
        return state["room"] == [0, 0, 0x42] and bool(state["powder"]) and not state["tarin"]
    if stage == "tarin_52_to_62":
        return state["room"] == [0, 0, 0x52] and bool(state["powder"]) and not state["tarin"]
    raise ValueError(f"Unknown live stage: {stage}")


def goal(env, state, next_room):
    direction, _ = adjacent_direction(state["room"], next_room)
    candidates = [candidate for candidate in exits(terrain(env.pyboy), cell(state["x"], state["y"]), state["room"][2])
                  if candidate["direction"] == direction]
    interior = [candidate for candidate in candidates if not
                (candidate["cell"][0] in (0, 9) and candidate["cell"][1] in (0, 7))]
    if not candidates:
        raise RuntimeError(f"No live target from {state['room']} toward {next_room:02X}")
    chosen = min(interior or candidates, key=lambda candidate: len(candidate["path"]))
    return {"room": [0, 0, next_room], "x": chosen["cell"][0] * 16 + 8, "y": chosen["cell"][1] * 16 + 12}


def run_case(root, spec, plan):
    source = ROOT / plan["source_teacher"] / spec["source_case"]
    out = root / spec["id"]
    out.mkdir(parents=True, exist_ok=False)
    for name in ("game.gbc", "initial.state"):
        shutil.copy2(source / name, out / name)
    source_manifest = json.loads((source / "manifest.json").read_text())
    for name, expected in source_manifest["artifacts"].items():
        if file_hash(source / name) != expected:
            raise ValueError(f"Source artifact changed: {spec['source_case']}/{name}")
    source_rows = [json.loads(line) for line in (source / "trajectory.jsonl").read_text().splitlines()]
    start = next(index for index, row in enumerate(source_rows) if matches(row["before"], spec["stage"]))
    write(out / "plan.json", {"spec": spec, "source_prefix_decisions": start,
          "source_trajectory_sha256": file_hash(source / "trajectory.jsonl"),
          "candidate_sha256": plan["candidate_sha256"], "action_frames": plan["action_frames"],
          "decision_budget": plan["decision_budget"], "validation_loaded": False})
    base = ProgressionEnv(out / "game.gbc", out / "initial.state", max_steps=12288, max_frames=300000)
    rows, failure, recoveries = [], None, 0
    began = time.monotonic()
    with (out / "trajectory.jsonl").open("x") as stream:
        env = Trace(base, stream, rows)
        try:
            base.reset(seed=0)
            for row in source_rows[:start]:
                apply(env, row["command"])
                if rows[-1]["fingerprint"] != row["fingerprint"]:
                    raise RuntimeError(f"Source prefix changed at {row['decision']}")
            controller = NavigationController(ROOT / plan["candidate"])
            context = ControlContext(base)
            origin = json_state(snapshot(base.pyboy))["room"]
            next_room = destination(json_state(snapshot(base.pyboy)))
            expected = [0, 0, next_room]
            previous, stationary = None, 0
            for _ in range(plan["decision_budget"]):
                state = json_state(snapshot(base.pyboy))
                if state["health"] == 0:
                    raise RuntimeError("Candidate died before the target crossing")
                if state["room"] == expected:
                    break
                if state["room"] != origin:
                    raise RuntimeError(f"Candidate entered {state['room']}, expected {expected}")
                if state["dialog_state"]:
                    dismiss_dialogue(env)
                    continue
                if mode(state) != "world":
                    raise RuntimeError(f"Candidate lost world control: {mode(state)}")
                target = goal(base, state, next_room)
                observation = context.observation(base.get_observation())
                action = controller.action(observation, state["room"], target)
                names, buttons = (None, "up", "down", "left", "right"), (None, "a", "b")
                pressed = [value for value in (names[action[0]], buttons[action[1]]) if value]
                env.step_buttons(pressed, action_frames=plan["action_frames"], legacy_action=action)
                now = json_state(snapshot(base.pyboy))
                pose = (tuple(now["room"]), now["x"], now["y"])
                stationary = stationary + 1 if pose == previous else 0
                previous = pose
                if stationary >= plan["stationary_before_recovery"]:
                    if recoveries >= plan["maximum_recoveries"]:
                        raise RuntimeError(f"Candidate stalled at {pose[1:]}")
                    direction = ("left", "right", "up", "down")[recoveries]
                    env.step_buttons([direction, "b"], action_frames=3)
                    recoveries += 1
                    stationary = 0
            else:
                raise RuntimeError("Candidate exhausted the crossing decision budget")
            final = json_state(snapshot(base.pyboy))
            if final["room"] != expected or not final["health"]:
                raise RuntimeError(f"Candidate crossing did not settle: {final}")
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
        finally:
            final = json_state(snapshot(base.pyboy))
            journal = deepcopy(base.journal.state())
            base.close()
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
    result = {"spec": spec, "success": failure is None, "failure": failure, "final": final,
              "source_prefix_decisions": start, "candidate_decisions": len(rows) - start,
              "recoveries": recoveries, "damage_raw": journal["damage_raw"],
              "healing_raw": journal["healing_raw"], "exact_replay": True,
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
            raise ValueError("Frozen live specifications changed")
        plan["specs"] = json.loads(source.read_text())["specs"]
    if file_hash(Path(__file__)) != plan["evaluator_sha256"]:
        raise ValueError("Frozen live evaluator changed")
    if file_hash(ROOT / plan["candidate"]) != plan["candidate_sha256"]:
        raise ValueError("Frozen candidate changed")
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(PLAN, out / "panel.json")
    shutil.copy2(Path(__file__), out / "evaluator-source.py")
    results = []
    for spec in plan["specs"]:
        results.append(run_case(out, spec, plan))
        write(out / "summary.json", {"cases": len(results), "successes": sum(r["success"] for r in results),
                                     "required_successes": plan["required_successes"], "results": results,
                                     "validation_loaded": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    main(parser.parse_args().out)

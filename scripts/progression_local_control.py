"""Extract and train the frozen room 52/42 local-control candidate."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np

from control_context import ControlContext
from gameboy_agent.navigation import NavigationNet, encode
from gameboy_agent.progression import mode, snapshot
from gameboy_agent.progression_contracts import adjacent_direction
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.terrain_navigation import cell, exits, terrain
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import apply


CONFIG = ROOT / "configs/progression_local_control_v1.json"
TEACHER = ROOT / "runs/state-driven-teacher-development-v3"
BASE_CACHE = ROOT / "runs/navigation-cache-v1"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def json_state(value):
    """Normalize tuples exactly as the JSONL evidence format does."""
    return json.loads(json.dumps(value))


def source_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def destination(state):
    """Return the teacher's explicit next-room goal in the two focus rooms."""
    if state["room"][:2] != [0, 0]:
        return None
    room = state["room"][2]
    if room == 0x52:
        if state["toadstool"]:
            return 0x42
        if not state["tarin"]:
            return 0x62
    if room == 0x42:
        if state["toadstool"]:
            return 0x43
        if state["powder"] and not state["tarin"]:
            return 0x52
    return None


def command_label(command):
    if command.get("timing") == "emulated_frames":
        return None
    buttons = command["buttons"]
    if any(button not in ("up", "down", "left", "right", "a", "b") for button in buttons):
        return None
    movements = [button for button in buttons if button in ("up", "down", "left", "right")]
    actions = [button for button in buttons if button in ("a", "b")]
    if len(movements) > 1 or len(actions) > 1:
        return None
    movement = {None: 0, "up": 1, "down": 2, "left": 3, "right": 4}[movements[0] if movements else None]
    button = {None: 0, "a": 1, "b": 2}[actions[0] if actions else None]
    return [movement, button]


def target(env, state, next_room):
    direction, _ = adjacent_direction(state["room"], next_room)
    candidates = [candidate for candidate in exits(terrain(env.pyboy), cell(state["x"], state["y"]), state["room"][2])
                  if candidate["direction"] == direction]
    interior = [candidate for candidate in candidates if not
                (candidate["cell"][0] in (0, 9) and candidate["cell"][1] in (0, 7))]
    if not candidates:
        raise RuntimeError(f"No focus-room target from {state['room']} toward {next_room:02X}")
    chosen = min(interior or candidates, key=lambda candidate: len(candidate["path"]))
    return [0, 0, next_room], chosen["cell"][0] * 16 + 8, chosen["cell"][1] * 16 + 12


def verify_teacher(config):
    if file_hash(TEACHER / "panel.json") != config["teacher"]["panel_sha256"]:
        raise ValueError("Frozen teacher panel changed")
    if file_hash(TEACHER / "summary.json") != config["teacher"]["summary_sha256"]:
        raise ValueError("Frozen teacher summary changed")
    summary = json.loads((TEACHER / "summary.json").read_text())
    if (summary["cases"], summary["successes"]) != (20, 18):
        raise ValueError("Frozen teacher gate changed")
    return summary


def extract(out):
    config = json.loads(CONFIG.read_text())
    summary = verify_teacher(config)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(CONFIG, out / "frozen-config.json")
    shutil.copy2(Path(__file__), out / "extractor-source.py")
    results = {result["spec"]["id"]: result for result in summary["results"]}
    split_cases = {
        "train": config["learner_data"]["training_cases"],
        "development": config["learner_data"]["visible_development_cases"],
    }
    manifest = {
        "schema": "progression-local-control-data-v1",
        "config_sha256": file_hash(CONFIG),
        "extractor_sha256": source_digest(),
        "teacher_panel_sha256": file_hash(TEACHER / "panel.json"),
        "teacher_summary_sha256": file_hash(TEACHER / "summary.json"),
        "validation_loaded": False,
        "splits": {},
    }
    for split, cases in split_cases.items():
        features, labels, durations, rooms, targets, provenance = [], [], [], [], [], []
        for case_id in cases:
            result = results[case_id]
            if not result["success"] or not result["exact_replay"]:
                raise ValueError(f"Training source is not a successful exact replay: {case_id}")
            source = TEACHER / case_id
            case_manifest = json.loads((source / "manifest.json").read_text())
            for name, expected in case_manifest["artifacts"].items():
                if file_hash(source / name) != expected:
                    raise ValueError(f"Teacher artifact changed: {case_id}/{name}")
            rows = [json.loads(line) for line in (source / "trajectory.jsonl").read_text().splitlines()]
            env = ProgressionEnv(source / "game.gbc", source / "initial.state", max_steps=12288, max_frames=300000)
            context = ControlContext(env)
            try:
                env.reset(seed=0)
                for row in rows:
                    state = json_state(snapshot(env.pyboy))
                    if state != row["before"]:
                        raise RuntimeError(f"Replay start mismatch: {case_id}/{row['decision']}")
                    next_room = destination(state)
                    label = command_label(row["command"])
                    if (next_room is not None and label is not None and not state["dialog_state"]
                            and mode(state) == "world"):
                        goal_room, goal_x, goal_y = target(env, state, next_room)
                        observation = context.observation(env.get_observation())
                        features.append(encode(observation, state["room"], goal_room, goal_x, goal_y))
                        labels.append(label)
                        durations.append(row["command"]["action_frames"])
                        rooms.append(state["room"][2])
                        targets.append(next_room)
                        provenance.append([case_id, row["decision"]])
                    info = apply(env, row["command"])[4]
                    if (json_state(snapshot(env.pyboy)) != row["after"] or env.frames != row["frame"]
                            or info["events"] != row["events"]):
                        raise RuntimeError(f"Replay result mismatch: {case_id}/{row['decision']}")
            finally:
                env.close()
        artifact = out / f"{split}.npz"
        np.savez_compressed(artifact, x=np.stack(features), y=np.asarray(labels, dtype=np.int64),
                            duration=np.asarray(durations, dtype=np.int64), room=np.asarray(rooms, dtype=np.int64),
                            target_room=np.asarray(targets, dtype=np.int64), provenance=np.asarray(provenance))
        manifest["splits"][split] = {
            "cases": cases,
            "rows": len(features),
            "room_counts": {str(room): rooms.count(room) for room in sorted(set(rooms))},
            "target_counts": {str(room): targets.count(room) for room in sorted(set(targets))},
            "sha256": file_hash(artifact),
        }
    write(out / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2), flush=True)


def divergence(candidate, parent):
    import torch.nn.functional as functional
    return (functional.kl_div(functional.log_softmax(candidate[:, :5], dim=1),
                              functional.softmax(parent[:, :5].detach(), dim=1), reduction="batchmean")
            + 0.25 * functional.kl_div(functional.log_softmax(candidate[:, 5:], dim=1),
                                       functional.softmax(parent[:, 5:].detach(), dim=1), reduction="batchmean"))


def training_result(out, config, manifest, selected, history):
    plan = config["candidate"]["candidate_1"]
    model_dir = out / "model"
    checkpoint = model_dir / f"epoch-{plan['epochs']:03}.pt"
    arrays = {split: np.load(out / "data" / f"{split}.npz") for split in ("train", "development")}
    return {
        "schema": "progression-local-control-training-result-v1",
        "status": "trained_unevaluated",
        "selected_checkpoint": str(checkpoint),
        "selected_checkpoint_sha256": file_hash(checkpoint),
        "selection": plan["selection"],
        "config_sha256": file_hash(CONFIG),
        "data_manifest_sha256": file_hash(out / "data" / "manifest.json"),
        "trainer_sha256": file_hash(out / "trainer-source.py"),
        "parent_sha256": selected["policy_sha256"],
        "training_rows": len(arrays["train"]["x"]),
        "visible_development_rows": len(arrays["development"]["x"]),
        "validation_loaded": False,
        "live_evaluation_performed": False,
        "history": history,
    }


def train(out):
    import torch
    config = json.loads(CONFIG.read_text())
    plan = config["candidate"]["candidate_1"]
    data = out / "data"
    manifest = json.loads((data / "manifest.json").read_text())
    if manifest["config_sha256"] != file_hash(CONFIG) or manifest["validation_loaded"]:
        raise ValueError("Feature cache does not match the frozen no-validation experiment")
    for split in ("train", "development"):
        if file_hash(data / f"{split}.npz") != manifest["splits"][split]["sha256"]:
            raise ValueError(f"Feature cache changed: {split}")
    selected = json.loads((ROOT / "configs/navigation_experiment.json").read_text())
    parent_path = ROOT / selected["policy_path"]
    if file_hash(parent_path) != selected["policy_sha256"]:
        raise ValueError("Selected navigation parent changed")
    cache_manifest = json.loads((BASE_CACHE / "manifest.json").read_text())
    if file_hash(BASE_CACHE / "train-x.npy") != cache_manifest["artifacts"]["train-x.npy"]:
        raise ValueError("Retention cache changed")
    out.mkdir(parents=True, exist_ok=True)
    model_dir = out / "model"
    model_dir.mkdir(exist_ok=False)
    shutil.copy2(CONFIG, out / "frozen-config.json")
    shutil.copy2(Path(__file__), out / "trainer-source.py")
    saved = torch.load(parent_path, map_location="cpu")
    model = NavigationNet(saved["inputs"])
    model.load_state_dict(saved["model"])
    model.eval()
    parent = NavigationNet(saved["inputs"])
    parent.load_state_dict(deepcopy(saved["model"]))
    parent.eval()
    for parameter in parent.parameters():
        parameter.requires_grad_(False)
    arrays = {split: np.load(data / f"{split}.npz") for split in ("train", "development")}
    normalize = lambda value: torch.from_numpy((value - saved["mean"]) / saved["scale"] * saved["input_mask"])
    tx = normalize(arrays["train"]["x"])
    ty = torch.from_numpy(arrays["train"]["y"])
    dx = normalize(arrays["development"]["x"])
    dy = torch.from_numpy(arrays["development"]["y"])
    retention_rows = plan["retention_rows"]
    retention = normalize(np.load(BASE_CACHE / "train-x.npy", mmap_mode="r")[:retention_rows])
    with torch.no_grad():
        parent_retention = torch.cat([parent(batch) for batch in retention.split(2048)])
    torch.set_num_threads(8)
    torch.manual_seed(plan["seed"])
    generator = torch.Generator().manual_seed(plan["seed"] + 1)
    optimizer = torch.optim.Adam(model.parameters(), lr=plan["learning_rate"])
    cross_entropy = torch.nn.CrossEntropyLoss()

    def action_loss(logits, labels):
        return cross_entropy(logits[:, :5], labels[:, 0]) + 0.25 * cross_entropy(logits[:, 5:], labels[:, 1])

    def metrics(x, y):
        model.eval()
        with torch.no_grad():
            logits = model(x)
            return {
                "loss": float(action_loss(logits, y)),
                "movement_accuracy": float((logits[:, :5].argmax(1) == y[:, 0]).float().mean()),
                "button_accuracy": float((logits[:, 5:].argmax(1) == y[:, 1]).float().mean()),
            }

    history = []
    for epoch in range(1, plan["epochs"] + 1):
        model.train()
        order = torch.randperm(len(tx), generator=generator)
        total = 0.0
        batches = 0
        for indices in order.split(256):
            retain_indices = torch.randint(len(retention), (min(1024, len(retention)),), generator=generator)
            optimizer.zero_grad()
            logits = model(tx[indices])
            retain_logits = model(retention[retain_indices])
            loss = action_loss(logits, ty[indices]) + plan["retention_weight"] * divergence(
                retain_logits, parent_retention[retain_indices])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(loss.detach())
            batches += 1
        record = {"epoch": epoch, "train_objective": total / batches,
                  "train": metrics(tx, ty), "development": metrics(dx, dy)}
        history.append(record)
        checkpoint = model_dir / f"epoch-{epoch:03}.pt"
        torch.save({**saved, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                    "epoch": epoch, "history": history, "experiment_config_sha256": file_hash(CONFIG),
                    "data_manifest_sha256": file_hash(data / "manifest.json")}, checkpoint)
        write(checkpoint.with_suffix(".json"), {"sha256": file_hash(checkpoint), "epoch": epoch})
        print(json.dumps(record), flush=True)
    result = training_result(out, config, manifest, selected, history)
    write(out / "result.json", result)
    print(json.dumps(result, indent=2), flush=True)


def finalize(out):
    config = json.loads(CONFIG.read_text())
    manifest = json.loads((out / "data" / "manifest.json").read_text())
    selected = json.loads((ROOT / "configs/navigation_experiment.json").read_text())
    checkpoint = out / "model" / f"epoch-{config['candidate']['candidate_1']['epochs']:03}.pt"
    sidecar = json.loads(checkpoint.with_suffix(".json").read_text())
    if file_hash(checkpoint) != sidecar["sha256"]:
        raise ValueError("Final checkpoint changed")
    import torch
    saved = torch.load(checkpoint, map_location="cpu")
    result = training_result(out, config, manifest, selected, saved["history"])
    result["report_recovered_after_wrapper_error"] = True
    write(out / "result.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("extract", "train", "finalize"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "extract":
        extract(args.out)
    elif args.mode == "finalize":
        finalize(args.out)
    else:
        train(args.out)

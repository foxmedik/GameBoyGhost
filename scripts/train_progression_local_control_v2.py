"""Train frozen candidate 2 with balanced room/button supervision."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import torch
import torch.nn.functional as functional

from gameboy_agent.navigation import NavigationNet
from gameboy_agent.world_memory import file_hash


CONFIG = ROOT / "configs/progression_local_control_v2.json"
DATA = ROOT / "runs/progression-local-control-v1/data"
BASE_CACHE = ROOT / "runs/navigation-cache-v1"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def divergence(candidate, parent):
    return (functional.kl_div(functional.log_softmax(candidate[:, :5], dim=1),
                              functional.softmax(parent[:, :5], dim=1), reduction="batchmean")
            + 0.25 * functional.kl_div(functional.log_softmax(candidate[:, 5:], dim=1),
                                       functional.softmax(parent[:, 5:], dim=1), reduction="batchmean"))


def run(out):
    config = json.loads(CONFIG.read_text())
    if file_hash(Path(__file__)) != config["trainer_sha256"]:
        raise ValueError("Frozen candidate-2 trainer changed")
    if file_hash(DATA / "manifest.json") != config["data_manifest_sha256"]:
        raise ValueError("Frozen candidate-2 data changed")
    data_manifest = json.loads((DATA / "manifest.json").read_text())
    if data_manifest["validation_loaded"]:
        raise ValueError("Validation-tainted cache rejected")
    for split in ("train", "development"):
        if file_hash(DATA / f"{split}.npz") != data_manifest["splits"][split]["sha256"]:
            raise ValueError(f"Feature cache changed: {split}")
    selected = json.loads((ROOT / "configs/navigation_experiment.json").read_text())
    parent_path = ROOT / selected["policy_path"]
    if file_hash(parent_path) != config["parent_sha256"]:
        raise ValueError("Frozen navigation parent changed")
    cache_manifest = json.loads((BASE_CACHE / "manifest.json").read_text())
    if file_hash(BASE_CACHE / "train-x.npy") != cache_manifest["artifacts"]["train-x.npy"]:
        raise ValueError("Retention cache changed")

    out.mkdir(parents=True, exist_ok=False)
    (out / "model").mkdir()
    shutil.copy2(CONFIG, out / "frozen-config.json")
    shutil.copy2(Path(__file__), out / "trainer-source.py")
    train = np.load(DATA / "train.npz")
    development = np.load(DATA / "development.npz")
    saved = torch.load(parent_path, map_location="cpu")
    model = NavigationNet(saved["inputs"])
    model.load_state_dict(saved["model"])
    parent = NavigationNet(saved["inputs"])
    parent.load_state_dict(deepcopy(saved["model"]))
    parent.eval()
    for parameter in parent.parameters():
        parameter.requires_grad_(False)
    normalize = lambda value: torch.from_numpy((value - saved["mean"]) / saved["scale"] * saved["input_mask"])
    tx, ty = normalize(train["x"]), torch.from_numpy(train["y"])
    dx, dy = normalize(development["x"]), torch.from_numpy(development["y"])
    strata = [torch.from_numpy(np.flatnonzero((train["room"] == room) & (train["y"][:, 1] == button)))
              for room in (0x42, 0x52) for button in (0, 1, 2)]
    if any(not len(indices) for indices in strata):
        raise ValueError("Every frozen room/button stratum must contain labels")
    retention_rows = config["retention_rows"]
    retention = normalize(np.load(BASE_CACHE / "train-x.npy", mmap_mode="r")[:retention_rows])
    with torch.no_grad():
        parent_retention = torch.cat([parent(batch) for batch in retention.split(2048)])
    torch.set_num_threads(8)
    torch.manual_seed(config["seed"])
    generator = torch.Generator().manual_seed(config["seed"] + 1)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    cross_entropy = torch.nn.CrossEntropyLoss()

    def action_loss(logits, labels):
        return cross_entropy(logits[:, :5], labels[:, 0]) + config["button_loss_weight"] * cross_entropy(logits[:, 5:], labels[:, 1])

    def metrics(x, y):
        model.eval()
        with torch.no_grad():
            logits = model(x)
            return {"loss": float(action_loss(logits, y)),
                    "movement_accuracy": float((logits[:, :5].argmax(1) == y[:, 0]).float().mean()),
                    "button_accuracy": float((logits[:, 5:].argmax(1) == y[:, 1]).float().mean())}

    history = []
    for epoch in range(1, config["epochs"] + 1):
        model.train()
        total = 0.0
        for _ in range(config["batches_per_epoch"]):
            indices = torch.cat([group[torch.randint(len(group), (config["rows_per_stratum"],), generator=generator)]
                                 for group in strata])
            retain_indices = torch.randint(len(retention), (config["retention_batch_rows"],), generator=generator)
            optimizer.zero_grad()
            loss = (action_loss(model(tx[indices]), ty[indices])
                    + config["retention_weight"] * divergence(model(retention[retain_indices]),
                                                               parent_retention[retain_indices]))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(loss.detach())
        record = {"epoch": epoch, "train_objective": total / config["batches_per_epoch"],
                  "train": metrics(tx, ty), "development": metrics(dx, dy)}
        history.append(record)
        checkpoint = out / "model" / f"epoch-{epoch:03}.pt"
        torch.save({**saved, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                    "epoch": epoch, "history": history, "experiment_config_sha256": file_hash(CONFIG),
                    "data_manifest_sha256": file_hash(DATA / "manifest.json")}, checkpoint)
        write(checkpoint.with_suffix(".json"), {"sha256": file_hash(checkpoint), "epoch": epoch})
        print(json.dumps(record), flush=True)
    checkpoint = out / "model" / f"epoch-{config['epochs']:03}.pt"
    result = {"schema": "progression-local-control-training-result-v2", "status": "trained_unevaluated",
              "selected_checkpoint": str(checkpoint), "selected_checkpoint_sha256": file_hash(checkpoint),
              "selection": "final epoch only", "config_sha256": file_hash(CONFIG),
              "data_manifest_sha256": file_hash(DATA / "manifest.json"), "trainer_sha256": file_hash(Path(__file__)),
              "parent_sha256": file_hash(parent_path), "training_rows": len(tx),
              "visible_development_rows": len(dx), "validation_loaded": False,
              "live_evaluation_performed": False, "history": history}
    write(out / "result.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out)

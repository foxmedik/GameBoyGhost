"""Train the frozen history/duration candidate on verified learner-state corrections."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import torch
from torch import nn
import torch.nn.functional as functional

from gameboy_agent.navigation import NavigationNet
from gameboy_agent.world_memory import file_hash


PLAN = ROOT / "configs/progression_dagger_v1_training.json"


class DaggerNet(nn.Module):
    def __init__(self, inputs):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(inputs, 256), nn.ReLU(), nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, 11))

    def forward(self, value):
        return self.net(value)


def initialize(saved):
    parent = NavigationNet(saved["inputs"]); parent.load_state_dict(saved["model"])
    model = DaggerNet(saved["inputs"] + 12)
    with torch.no_grad():
        model.net[0].weight[:, :saved["inputs"]].copy_(parent.net[0].weight)
        model.net[0].weight[:, saved["inputs"]:].zero_(); model.net[0].bias.copy_(parent.net[0].bias)
        model.net[2].weight.copy_(parent.net[2].weight); model.net[2].bias.copy_(parent.net[2].bias)
        model.net[4].weight[:8].copy_(parent.net[4].weight); model.net[4].bias[:8].copy_(parent.net[4].bias)
        model.net[4].weight[8:].zero_(); model.net[4].bias[8:].zero_()
    return model, parent


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(out):
    plan = json.loads(PLAN.read_text())
    if file_hash(Path(__file__)) != plan["trainer_sha256"]: raise ValueError("Frozen trainer changed")
    collection = ROOT / plan["collection"]
    if file_hash(collection / "summary.json") != plan["collection_summary_sha256"]: raise ValueError("Collection summary changed")
    summary = json.loads((collection / "summary.json").read_text())
    if summary["successes"] < summary["required_successes"] or summary["validation_loaded"]: raise ValueError("Teacher gate failed")
    xs, ys = [], []
    for result in summary["results"]:
        if not result["success"] or not result["exact_replay"]: continue
        folder = collection / result["spec"]["id"]
        manifest = json.loads((folder / "manifest.json").read_text())
        for name, expected in manifest["artifacts"].items():
            if file_hash(folder / name) != expected: raise ValueError(f"Correction changed: {folder/name}")
        data = np.load(folder / "corrections.npz"); xs.append(data["x"]); ys.append(data["y"])
    x = np.concatenate(xs); y = np.concatenate(ys)
    if len(x) != plan["correction_rows"]: raise ValueError("Correction row count changed")
    parent_path = ROOT / plan["parent"]
    if file_hash(parent_path) != plan["parent_sha256"]: raise ValueError("Parent changed")
    saved = torch.load(parent_path, map_location="cpu")
    model, parent = initialize(saved); parent.eval()
    base = np.load(ROOT / plan["retention_data"])["x"]
    count = min(plan["retention_rows"], len(base)); base = base[:count]
    normalized_base = torch.from_numpy((base-saved["mean"])/saved["scale"]*saved["input_mask"])
    padded_base = torch.cat([normalized_base, torch.zeros((count, 12))], dim=1)
    normalized = torch.from_numpy(np.concatenate([((x[:, :saved["inputs"]]-saved["mean"])/saved["scale"]*saved["input_mask"]),
                                                   x[:, saved["inputs"]:]], axis=1))
    labels = torch.from_numpy(y)
    with torch.no_grad(): parent_logits = parent(normalized_base)
    torch.set_num_threads(8); torch.manual_seed(plan["seed"]); generator = torch.Generator().manual_seed(plan["seed"]+1)
    optimizer = torch.optim.Adam(model.parameters(), lr=plan["learning_rate"]); ce = nn.CrossEntropyLoss(); history=[]
    def loss(z, target): return ce(z[:, :5], target[:, 0]) + ce(z[:, 5:8], target[:, 1]) + ce(z[:, 8:], target[:, 2])
    for epoch in range(1, plan["epochs"]+1):
        model.train(); total=0.0
        for _ in range(plan["batches_per_epoch"]):
            idx=torch.randint(len(normalized),(plan["batch_rows"],),generator=generator)
            ri=torch.randint(count,(plan["retention_batch_rows"],),generator=generator)
            optimizer.zero_grad(); z=model(normalized[idx]); rz=model(padded_base[ri])
            retain=(functional.kl_div(functional.log_softmax(rz[:,:5],1),functional.softmax(parent_logits[ri,:5],1),reduction="batchmean")
                    +.25*functional.kl_div(functional.log_softmax(rz[:,5:8],1),functional.softmax(parent_logits[ri,5:8],1),reduction="batchmean"))
            value=loss(z,labels[idx])+plan["retention_weight"]*retain; value.backward(); nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step();total+=float(value.detach())
        model.eval()
        with torch.no_grad():
            z=model(normalized); metrics={"loss":float(loss(z,labels)),"movement_accuracy":float((z[:,:5].argmax(1)==labels[:,0]).float().mean()),
                "button_accuracy":float((z[:,5:8].argmax(1)==labels[:,1]).float().mean()),"duration_accuracy":float((z[:,8:].argmax(1)==labels[:,2]).float().mean())}
        history.append({"epoch":epoch,"objective":total/plan["batches_per_epoch"],**metrics});print(json.dumps(history[-1]),flush=True)
    out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/"plan.json");shutil.copy2(Path(__file__),out/"trainer-source.py")
    checkpoint=out/"candidate.pt";torch.save({"model":model.state_dict(),"inputs":saved["inputs"]+12,"base_inputs":saved["inputs"],
        "mean":saved["mean"],"scale":saved["scale"],"input_mask":saved["input_mask"],"history":history,"duration_classes":[1,3,10]},checkpoint)
    result={"status":"trained_live_development_pending","checkpoint":str(checkpoint),"checkpoint_sha256":file_hash(checkpoint),
        "plan_sha256":file_hash(PLAN),"correction_rows":len(x),"teacher_successes":summary["successes"],"teacher_cases":summary["cases"],
        "validation_loaded":False,"selection":"final epoch only","final":history[-1]};write(out/"result.json",result);print(json.dumps(result,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);run(p.parse_args().out)

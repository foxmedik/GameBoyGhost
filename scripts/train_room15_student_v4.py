"""Train v4 with clean-data retention and lightly weighted targeted escapes."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import torch
from torch import nn
from gameboy_agent.world_memory import file_hash
from train_room15_student_v1 import Room15Net


def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--data', type=Path, required=True); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    for path, expected in plan['frozen_inputs'].items():
        if file_hash(ROOT / path) != expected: raise RuntimeError(f'Frozen input changed: {path}')
    manifest = json.loads((args.data / 'manifest.json').read_text())
    if manifest['experiment_sha256'] != file_hash(args.plan) or manifest['validation_loaded']: raise RuntimeError('Frozen data changed')
    train, dev = np.load(args.data / 'train.npz'), np.load(args.data / 'development.npz')
    raw, y, row_weight = train['x'].astype(np.float32), train['y'], train['weight'].astype(np.float32)
    mean, scale = raw.mean(0), raw.std(0); scale[scale < 1e-4] = 1
    x = torch.from_numpy((raw - mean) / scale); target = torch.from_numpy(y); weight = torch.from_numpy(row_weight)
    devx = torch.from_numpy((dev['x'].astype(np.float32) - mean) / scale); devy = torch.from_numpy(dev['y'])
    clean = row_weight == 1; counts = np.bincount(y[clean], minlength=plan['actions'])
    class_weight = torch.tensor(clean.sum() / np.maximum(counts, 1) / plan['actions'], dtype=torch.float32)
    clean_index = torch.from_numpy(np.flatnonzero(clean)); recovery_index = torch.from_numpy(np.flatnonzero(~clean))
    torch.set_num_threads(8); torch.manual_seed(plan['model']['seed']); generator = torch.Generator().manual_seed(plan['model']['seed'] + 1)
    model = Room15Net(x.shape[1], plan['actions']); optimizer = torch.optim.Adam(model.parameters(), lr=plan['model']['learning_rate'])
    loss_fn = nn.CrossEntropyLoss(weight=class_weight, reduction='none'); history = []
    recovery_n = round(plan['model']['batch_rows'] * plan['model']['recovery_batch_fraction']); clean_n = plan['model']['batch_rows'] - recovery_n
    for epoch in range(1, plan['model']['epochs'] + 1):
        model.train(); objective = 0.0
        for _ in range(plan['model']['batches_per_epoch']):
            index = torch.cat((clean_index[torch.randint(len(clean_index), (clean_n,), generator=generator)], recovery_index[torch.randint(len(recovery_index), (recovery_n,), generator=generator)]))
            optimizer.zero_grad(); losses = loss_fn(model(x[index]), target[index]); value = (losses * weight[index]).sum() / weight[index].sum(); value.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1); optimizer.step(); objective += float(value.detach())
        model.eval()
        with torch.no_grad():
            history.append({'epoch': epoch, 'objective': objective / plan['model']['batches_per_epoch'], 'train_accuracy': float((model(x).argmax(1) == target).float().mean()), 'development_accuracy': float((model(devx).argmax(1) == devy).float().mean())})
        print(json.dumps(history[-1]), flush=True)
    args.out.mkdir(parents=True, exist_ok=False); shutil.copy2(args.plan, args.out / 'plan.json'); checkpoint = args.out / 'candidate.pt'
    torch.save({'model': model.state_dict(), 'inputs': x.shape[1], 'outputs': plan['actions'], 'mean': mean, 'scale': scale, 'history': history}, checkpoint)
    write(args.out / 'result.json', {'status': 'trained_live_gate_pending', 'checkpoint': str(checkpoint), 'checkpoint_sha256': file_hash(checkpoint), 'rows': len(x), 'recovery_rows': int((~clean).sum()), 'development_rows': len(devx), 'final': history[-1], 'validation_loaded': False})


if __name__ == '__main__': main()

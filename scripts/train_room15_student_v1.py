"""Train exactly one frozen room-15 imitation candidate."""
import argparse, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import torch
from torch import nn
from gameboy_agent.world_memory import file_hash


class Room15Net(nn.Module):
    def __init__(self, inputs, outputs):
        super().__init__(); self.net = nn.Sequential(nn.Linear(inputs, 192), nn.ReLU(), nn.Linear(192, 192), nn.ReLU(), nn.Linear(192, outputs))
    def forward(self, value): return self.net(value)


def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--data', type=Path, required=True); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if file_hash(Path(__file__)) != plan['trainer_sha256']: raise RuntimeError('Frozen trainer changed')
    manifest = json.loads((args.data / 'manifest.json').read_text())
    if manifest['experiment_sha256'] != file_hash(args.plan) or manifest['validation_loaded']: raise RuntimeError('Frozen data changed')
    train, development = np.load(args.data / 'train.npz'), np.load(args.data / 'development.npz')
    for split in ('train', 'development'):
        if file_hash(args.data / f'{split}.npz') != manifest['splits'][split]['sha256']: raise RuntimeError(f'{split} data changed')
    raw, y = train['x'].astype(np.float32), train['y']; mean, scale = raw.mean(0), raw.std(0); scale[scale < 1e-4] = 1
    x = torch.from_numpy((raw - mean) / scale); target = torch.from_numpy(y); devx = torch.from_numpy((development['x'].astype(np.float32) - mean) / scale); devy = torch.from_numpy(development['y'])
    counts = np.bincount(y, minlength=plan['actions']); weights = torch.tensor(len(y) / np.maximum(counts, 1) / plan['actions'], dtype=torch.float32)
    torch.set_num_threads(8); torch.manual_seed(plan['model']['seed']); generator = torch.Generator().manual_seed(plan['model']['seed'] + 1)
    model = Room15Net(x.shape[1], plan['actions']); optimizer = torch.optim.Adam(model.parameters(), lr=plan['model']['learning_rate']); loss = nn.CrossEntropyLoss(weight=weights); history=[]
    for epoch in range(1, plan['model']['epochs'] + 1):
        model.train(); objective = 0.0
        for _ in range(plan['model']['batches_per_epoch']):
            index = torch.randint(len(x), (plan['model']['batch_rows'],), generator=generator); optimizer.zero_grad(); value = loss(model(x[index]), target[index]); value.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1); optimizer.step(); objective += float(value.detach())
        model.eval()
        with torch.no_grad():
            row = {'epoch': epoch, 'objective': objective / plan['model']['batches_per_epoch'], 'train_accuracy': float((model(x).argmax(1) == target).float().mean()), 'development_accuracy': float((model(devx).argmax(1) == devy).float().mean())}
        history.append(row); print(json.dumps(row), flush=True)
    args.out.mkdir(parents=True, exist_ok=False); shutil.copy2(args.plan, args.out / 'plan.json'); checkpoint = args.out / 'candidate.pt'
    torch.save({'model': model.state_dict(), 'inputs': x.shape[1], 'outputs': plan['actions'], 'mean': mean, 'scale': scale, 'history': history}, checkpoint)
    write(args.out / 'result.json', {'status': 'trained_live_gate_pending', 'checkpoint': str(checkpoint), 'checkpoint_sha256': file_hash(checkpoint), 'rows': len(x), 'development_rows': len(devx), 'final': history[-1], 'validation_loaded': False})


if __name__ == '__main__': main()

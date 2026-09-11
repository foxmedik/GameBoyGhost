"""Validate committed corpus shards and optionally replay sampled episodes."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import numpy as np
import pyarrow.parquet as pq
from gameboy_agent.dataset import SCHEMA, sha256, unpack_observation, pack_observation


def verify(batch, *, replay=0):
    batch = Path(batch).resolve()
    from data_workset import verify_runtime
    verify_runtime(batch)
    manifests = sorted((batch / 'train').glob('*/*/manifest.json'))
    episodes, total, ids = [], 0, set()
    for path in manifests:
        meta = json.loads(path.read_text())
        if meta['episode_id'] in ids or meta['split'] != 'train':
            raise ValueError('Duplicate episode or split contamination')
        ids.add(meta['episode_id'])
        for filename, field in (('steps.parquet', 'parquet_sha256'), ('final.state','final_state_sha256'),
                                ('events.json','events_sha256')):
            if sha256(path.parent / filename) != meta[field]:
                raise ValueError(f'Artifact hash mismatch: {path.parent / filename}')
        data = pq.read_table(path.parent / 'steps.parquet')
        if data.num_rows != meta['rows'] or not data.schema.equals(SCHEMA, check_metadata=False):
            raise ValueError('Row count/schema mismatch')
        if data['step'].to_pylist() != list(range(meta['rows'])):
            raise ValueError('Noncontiguous episode steps')
        if set(data['split'].to_pylist()) != {'train'}:
            raise ValueError('Evaluation rows in training corpus')
        if set(data['episode_id'].to_pylist()) != {meta['episode_id']}:
            raise ValueError('Episode provenance mismatch')
        before, after = data['observation'].to_pylist(), data['next_observation'].to_pylist()
        if after[:-1] != before[1:]:
            raise ValueError('Observation discontinuity')
        for row in data.select(['reward_total','reward_components']).to_pylist():
            if not np.isclose(row['reward_total'], sum(json.loads(row['reward_components']).values()), atol=1e-6):
                raise ValueError('Reward components mismatch')
        total += data.num_rows
        episodes.append((path, meta))
    replayed = []
    # Evenly sample the committed episode list, including its boundaries.
    indices = np.linspace(0, len(episodes)-1, min(replay, len(episodes)), dtype=int) if episodes else []
    for index in indices:
        path, meta = episodes[index]
        from gameboy_agent.training_env import TrainingEnv
        from gameboy_agent.checkpoint import fingerprint
        from control_context import ControlContext
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'game.gbc'
            shutil.copy2(batch / 'assets/game.gbc', rom)
            base = TrainingEnv(rom, batch / 'assets' / f'{meta["start"]}.state',
                               max_steps=meta['max_steps'], sword_curriculum=False)
            env = ControlContext(base)
            try:
                obs, _ = env.reset(seed=meta['seed'])
                data = pq.read_table(path.parent / 'steps.parquet').to_pylist()
                for row in data:
                    if pack_observation(obs, meta['observation_layout']) != row['observation']:
                        raise ValueError('Pre-action observation replay mismatch')
                    obs, reward, done, truncated, info = env.step(np.asarray(row['action']))
                    if pack_observation(obs, meta['observation_layout']) != row['next_observation']:
                        raise ValueError('Post-action observation replay mismatch')
                    if reward != row['reward_total'] or done != row['terminated'] or truncated != row['truncated']:
                        raise ValueError('Reward/termination replay mismatch')
                if fingerprint(base) != meta['fingerprint']:
                    raise ValueError('Final emulator replay mismatch')
                replayed.append(dict(episode_id=meta['episode_id'], rows=meta['rows'], exact=True))
            finally:
                env.close()
    return dict(committed_episodes=len(episodes), rows=total, replayed=replayed,
                observation_continuity=True, hashes_valid=True, completion_evaluated=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('batch', type=Path)
    parser.add_argument('--replay', type=int, default=3)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.batch, replay=args.replay)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result), flush=True)

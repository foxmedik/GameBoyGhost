"""Parallel collection, measured scaling, immutable episodes, restartable batch.

The supervisor imports the numerical stack only inside spawned workers.
"""
import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import shutil
import signal
import socket
import sys
import time
import uuid

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
STOP = False


def publish(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def initialize_worker(batch, ready):
    global BATCH, np, TrainingEnv, ControlContext, senses, predict, features, Explorer
    global EpisodeWriter, observation_layout, pack_observation, screen_bytes, fingerprint, PRODUCER
    import numpy as np
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from gameboy_agent.training_env import TrainingEnv
    from gameboy_agent.skills import Explorer
    from gameboy_agent.dataset import EpisodeWriter, observation_layout, pack_observation, screen_bytes
    from gameboy_agent.checkpoint import fingerprint
    from control_context import ControlContext
    from run_skill_chain import senses
    from tree_controller import predict, features
    BATCH = Path(batch)
    PRODUCER = json.loads((BATCH / 'plan.json').read_text())['producer_id']
    # ROM ownership is per process; workers never write another worker's state.
    local = BATCH / 'workers' / str(os.getpid())
    local.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BATCH / 'assets/game.gbc', local / 'game.gbc')
    ready.put(os.getpid())


def collect(job):
    import random
    import hashlib
    index, split, budget, namespace = job
    seed = (900_000_000 if split == 'eval' else 100_000) + index
    rng = random.Random(seed)
    start = ('house', 'beach', 'approach')[index % 3]
    epsilon = (0.0, 0.02, 0.05, 0.10, 0.20)[(index // 3) % 5]
    episode_id = str(uuid.uuid5(uuid.UUID(namespace), f'{split}/{index}'))
    attempt_id = str(uuid.uuid4())
    directory = BATCH / split / f'{index:08d}' / attempt_id
    base = TrainingEnv(BATCH / 'workers' / str(os.getpid()) / 'game.gbc',
                       BATCH / 'assets' / f'{start}.state', max_steps=budget, sword_curriculum=False)
    env = ControlContext(base)
    writer, actions, events, rooms = None, [], [], set()
    began = time.monotonic()
    status, acquired_at, previous_skill = 'budget_exhausted', None, None
    # The old sword validation uses waits <=15. New collection uses >=16;
    # future evaluation setup lengths are disjoint from training's range.
    idle_count = rng.randrange(256, 320) if split == 'eval' else rng.randrange(16, 256)
    movement = rng.randrange(5)
    setup = [[0, 0]] * idle_count + [[movement, 0]] * rng.randrange(5)
    policy = json.loads((BATCH / 'assets/policy.json').read_text())
    explorer = Explorer()
    random_direction, random_remaining = 0, 0
    try:
        obs, _ = env.reset(seed=seed)
        layout = observation_layout(obs)
        metadata = dict(batch_id=namespace, run_id=attempt_id, producer_id=PRODUCER,
                        episode_id=episode_id, split=split, seed=seed, index=index, start=start,
                        epsilon=epsilon, max_steps=budget, setup_actions=setup,
                        human_intervened=False, harness_privilege='D',
                        supervision='mixed_learned_sword_and_scripted_exploration',
                        completion_evaluated=False, asset_manifest='assets.json')
        writer = EpisodeWriter(directory, metadata, layout)
        for step in range(budget):
            before = senses(base)
            if step < len(setup):
                action, skill = setup[step], 'physical_setup'
            elif not before.sword:
                if step - len(setup) >= 1600:
                    status = 'sword_timeout'
                    break
                action, skill = predict(policy, features(obs)).tolist(), 'acquire_sword'
            else:
                skill = 'explore'
                action = explorer.action(before)
                # Keep the underlying novelty controller's memory; randomized
                # interventions are labeled explicitly and serialized as actions.
                if before.dialogue:
                    random_remaining = 0
                elif random_remaining:
                    action[0] = random_direction
                    random_remaining -= 1
                elif rng.random() < epsilon:
                    random_direction = rng.randrange(1, 5)
                    random_remaining = rng.randrange(1, 8)
                    action[0] = random_direction
                if not before.dialogue and explorer.previous:
                    # Credit the action actually executed, including randomized
                    # interventions, when updating blocked/hazard memory.
                    explorer.previous['edge'] = f'{before.cell}/{action[0]}'
                    explorer.last_direction = action[0]
                    if random_remaining:
                        explorer.remaining = 0
            if skill != previous_skill:
                events.append(dict(step=step, event='skill_started', skill=skill))
                previous_skill = skill
            before_blob = pack_observation(obs, layout)
            next_obs, reward, done, truncated, info = env.step(np.asarray(action))
            after = senses(base)
            actions.append(action)
            rooms.add(after.room)
            if acquired_at is None and after.sword:
                acquired_at = step + 1
                events.append(dict(step=step + 1, event='sword_acquired'))
            if after.health < before.health:
                events.append(dict(step=step, event='damage', amount=before.health - after.health))
            screenshot = screen_bytes(base.pyboy) if (step % 32 == 0 or done or truncated
                                                       or (after.sword and not before.sword)) else None
            writer.add(dict(schema_version='gameboy-motor-v1', run_id=attempt_id,
                producer_id=PRODUCER, episode_id=episode_id, split=split, seed=seed,
                step=step, action=action, skill=skill,
                supervision='learned_imitation' if skill == 'acquire_sword' else 'scripted',
                observation=before_blob, next_observation=pack_observation(next_obs, layout),
                room=list(before.room), next_room=list(after.room), x=before.x, y=before.y,
                health=before.health, next_x=after.x, next_y=after.y, next_health=after.health,
                sword=after.sword, reward_total=reward, reward_components=json.dumps(info['reward']),
                frames_advanced=info['frames_advanced'], wait_frames=info['wait_frames'],
                terminated=done, truncated=truncated, screen_png=screenshot,
                harness_privilege='D', completion_evaluated=False))
            obs = next_obs
            if done or truncated:
                status = 'death' if after.health == 0 else 'budget_exhausted'
                break
        events.append(dict(step=len(actions), event='episode_end', status=status))
        # State at the terminal boundary is for inspection; replay starts from
        # the content-hashed initial state and every recorded physical action.
        with (directory / 'final.state').open('xb') as stream:
            base.pyboy.save_state(stream)
        (directory / 'events.json').write_text(json.dumps(events))
        from gameboy_agent.dataset import sha256
        result = writer.finish(dict(status=status, sword_acquired=acquired_at is not None,
            sword_step=acquired_at, rooms=[list(r) for r in sorted(rooms)],
            final_health=senses(base).health, fingerprint=fingerprint(base),
            action_sha256=hashlib.sha256(json.dumps(actions).encode()).hexdigest(),
            final_state_sha256=sha256(directory / 'final.state'),
            events_sha256=sha256(directory / 'events.json'),
            wall_seconds=time.monotonic() - began))
        return dict(index=index, split=split, directory=str(directory), rows=result['rows'],
                    bytes=sum(p.stat().st_size for p in directory.iterdir()), status=status,
                    sword_acquired=result['sword_acquired'], rooms=len(rooms),
                    wall_seconds=result['wall_seconds'])
    except Exception as exc:
        if writer:
            writer.abort()
        directory.mkdir(parents=True, exist_ok=True)
        publish(directory / 'failure.json', dict(error=repr(exc), index=index, split=split,
                                                steps=len(actions), seed=seed))
        return dict(index=index, split=split, directory=str(directory), rows=0, bytes=0,
                    status='failed', error=repr(exc))
    finally:
        env.close()


def pool_start(batch, workers):
    ctx = mp.get_context('spawn')
    ready = ctx.Queue()
    started = time.monotonic()
    pool = ctx.Pool(workers, initializer=initialize_worker, initargs=(str(batch), ready))
    try:
        for _ in range(workers):
            ready.get(timeout=180)
    except BaseException:
        pool.terminate()
        pool.join()
        raise
    return pool, time.monotonic() - started


def resources():
    import psutil
    current = psutil.Process()
    procs = [current] + current.children(recursive=True)
    rss = cpu = 0
    for proc in procs:
        try:
            rss += proc.memory_info().rss
            times = proc.cpu_times()
            cpu += times.user + times.system
        except psutil.Error:
            pass
    return dict(rss_gib=rss / 1024**3, process_cpu_seconds=cpu,
                available_gib=psutil.virtual_memory().available / 1024**3,
                free_disk_gib=shutil.disk_usage(ROOT).free / 1024**3)


def benchmark(batch, counts, steps):
    namespace = json.loads((batch / 'plan.json').read_text())['batch_id']
    results = []
    for workers in counts:
        publish(batch / 'status.json', dict(status='benchmarking', workers=workers, results=results))
        pool, startup = pool_start(batch, workers)
        start = time.monotonic()
        before = resources()
        # Identical seeds, starts, budgets, and policies at every worker count.
        jobs = [(500000 + i, f'benchmark-{workers}', steps, namespace) for i in range(128)]
        try:
            tasks = [pool.apply_async(collect, (job,)) for job in jobs]
            peak = before['rss_gib']
            while not all(task.ready() for task in tasks):
                usage = resources()
                peak = max(peak, usage['rss_gib'])
                if STOP or (batch / 'STOP').exists() or usage['available_gib'] < 32:
                    pool.terminate()
                    raise RuntimeError('Benchmark stopped by request or memory limit')
                time.sleep(1)
            output = [task.get() for task in tasks]
            after = resources()
        finally:
            pool.close()
            pool.join()
        elapsed = time.monotonic() - start
        rows = sum(r['rows'] for r in output)
        result = dict(workers=workers, startup_seconds=startup, wall_seconds=elapsed,
                      rows=rows, steps_per_second=rows / elapsed, peak_rss_gib=peak,
                      cpu_core_equivalents=(after['process_cpu_seconds']-before['process_cpu_seconds']) / elapsed,
                      failures=sum(r['status']=='failed' for r in output))
        results.append(result)
        publish(batch / 'benchmark.json', results)
        print(json.dumps(result), flush=True)
    valid = [r for r in results if not r['failures'] and r['peak_rss_gib'] < 192]
    if not valid:
        raise RuntimeError('No valid worker configuration')
    best = max(r['steps_per_second'] for r in valid)
    # Prefer fewer processes within 10% of the measured best throughput.
    return min(r['workers'] for r in valid if r['steps_per_second'] >= best * .9)


def prepare(batch, target_steps, hours):
    from gameboy_agent.dataset import sha256
    batch.mkdir(parents=True, exist_ok=False)
    (batch / 'assets').mkdir()
    sources = {'game.gbc': next(ROOT.glob('*.gbc')),
               'house.state': ROOT / 'references/LADXExperiments/ladx.gbc.state',
               'beach.state': ROOT / 'runs/sword-curriculum-v1/beach_route.state',
               'approach.state': ROOT / 'runs/sword-curriculum-v1/sword_approach.state'}
    selected = json.loads((ROOT / 'configs/sword_controller.json').read_text())
    sources['policy.json'] = ROOT / selected['policy_path']
    if sha256(sources['policy.json']) != selected['policy_sha256']:
        raise ValueError('Selected policy mismatch')
    for name, path in sources.items():
        shutil.copy2(path, batch / 'assets' / name)
    publish(batch / 'assets.json', {name: sha256(batch / 'assets' / name) for name in sources})
    # Freeze project and upstream runtime code before long-running collection.
    runtime = batch / 'runtime'
    for folder in ('src', 'scripts', 'configs'):
        shutil.copytree(ROOT / folder, runtime / folder,
                        ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT / 'references/LADXExperiments', runtime / 'references/LADXExperiments',
                    ignore=shutil.ignore_patterns('.git', '__pycache__'))
    import importlib.metadata
    publish(batch / 'runtime.json', dict(versions={p: importlib.metadata.version(p) for p in
        ('pyboy','numpy','torch','gymnasium','stable-baselines3','pyarrow','psutil')},
        files={str(p.relative_to(runtime)):sha256(p) for p in runtime.rglob('*') if p.is_file()}))
    import platform
    plan = dict(schema='data-workset-plan-v1', batch_id=str(uuid.uuid4()), target_steps=target_steps,
                episode_steps=4096, max_hours=hours, output_limit_gib=256,
                minimum_free_disk_gib=100, minimum_available_ram_gib=32,
                created_at=time.time(), producer_id=f'{socket.gethostname()}-{uuid.uuid4()}',
                hardware=dict(machine=platform.machine(), cpu_count=os.cpu_count(), os=platform.platform()),
                git_commit=None, source_identity='runtime.json SHA-256 manifest; project has no git history',
                training_seed_base=100000, frozen_eval_seed_base=900000000,
                frozen_eval_episodes=96, completion_evaluated=False,
                eval_note='Disjoint setup wait ranges; same three development savestates. Not held-out games.',
                planner='scripted_novelty_with_randomized_exploration', harness_privilege='D')
    publish(batch / 'plan.json', plan)
    publish(batch / 'frozen-eval.json', dict(episodes=[dict(index=i, seed=900000000+i,
        start=('house','beach','approach')[i % 3]) for i in range(96)],
        excluded_from_collection=True, excluded_from_training=True))
    return runtime


def verify_runtime(batch):
    from gameboy_agent.dataset import sha256
    import importlib.metadata
    manifest = json.loads((batch / 'runtime.json').read_text())
    for name, version in manifest['versions'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f'Runtime dependency mismatch: {name}')
    for name, expected in manifest['files'].items():
        if sha256(batch / 'runtime' / name) != expected:
            raise ValueError(f'Runtime source mismatch: {name}')
    for name, expected in json.loads((batch / 'assets.json').read_text()).items():
        if sha256(batch / 'assets' / name) != expected:
            raise ValueError(f'Asset mismatch: {name}')


def train_collection(batch, workers):
    global STOP
    plan = json.loads((batch / 'plan.json').read_text())
    # Reconcile complete episode manifests after an interrupted supervisor.
    completed = {}
    from gameboy_agent.dataset import sha256
    for path in (batch / 'train').glob('*/*/manifest.json'):
        meta = json.loads(path.read_text())
        for filename, field in (('steps.parquet','parquet_sha256'), ('final.state','final_state_sha256'),
                                ('events.json','events_sha256')):
            if sha256(path.parent / filename) != meta[field]:
                raise ValueError(f'Committed episode integrity mismatch: {path}')
        if meta['index'] in completed:
            raise RuntimeError('Duplicate committed episode index')
        completed[meta['index']] = dict(index=meta['index'], split='train', directory=str(path.parent),
            rows=meta['rows'], status=meta['status'], sword_acquired=meta['sword_acquired'],
            bytes=sum(p.stat().st_size for p in path.parent.iterdir()))
    rows = sum(r['rows'] for r in completed.values())
    output_bytes = sum(r['bytes'] for r in completed.values())
    history_path = batch / 'progress.json'
    prior = json.loads(history_path.read_text()) if history_path.exists() else {}
    elapsed_before = prior.get('active_seconds', 0)
    started = time.monotonic()
    pool, startup = pool_start(batch, workers)
    pending, failures, next_index = {}, [], 0
    status = 'running'
    stop_reason = None
    progress = dict(status=status, pid=os.getpid(), workers=workers, rows=rows,
                    target_steps=plan['target_steps'], episodes=len(completed), pending=0,
                    active_seconds=elapsed_before, bytes=output_bytes, failures=[],
                    sword_episodes=sum(r.get('sword_acquired',False) for r in completed.values()),
                    deaths=sum(r['status']=='death' for r in completed.values()),
                    resources=resources(), updated_at=time.time(), stop_reason=None)
    try:
        while pending or rows < plan['target_steps']:
            resource = resources()
            elapsed = elapsed_before + time.monotonic() - started
            if STOP:
                stop_reason = 'user_stop'
            elif (batch / 'STOP').exists():
                stop_reason = 'stop_file'
            elif elapsed >= plan['max_hours'] * 3600:
                stop_reason = 'time_limit'
            elif output_bytes >= plan['output_limit_gib'] * 1024**3:
                stop_reason = 'output_limit'
            elif resource['free_disk_gib'] < plan['minimum_free_disk_gib']:
                stop_reason = 'disk_limit'
            elif resource['available_gib'] < plan['minimum_available_ram_gib']:
                stop_reason = 'memory_limit'
            elif len(failures) >= 20:
                stop_reason = 'repeated_worker_failures'
            if stop_reason and not pending:
                status = 'paused_' + stop_reason
                break
            reserved = sum(limit for _, limit in pending.values())
            while not stop_reason and len(pending) < workers and rows + reserved < plan['target_steps']:
                while next_index in completed:
                    next_index += 1
                limit = min(plan['episode_steps'], plan['target_steps'] - rows - reserved)
                task = pool.apply_async(collect, ((next_index, 'train', limit, plan['batch_id']),))
                pending[next_index] = (task, limit)
                reserved += limit
                next_index += 1
            for index, (task, limit) in list(pending.items()):
                if task.ready():
                    result = task.get()
                    del pending[index]
                    with (batch / 'commits.jsonl').open('a') as log:
                        log.write(json.dumps(result) + '\n')
                    if result['status'] == 'failed':
                        failures.append(result)
                    else:
                        completed[index] = result
                        rows += result['rows']
                        output_bytes += result['bytes']
            progress = dict(status=status, pid=os.getpid(), workers=workers, rows=rows,
                target_steps=plan['target_steps'], episodes=len(completed), pending=len(pending),
                active_seconds=elapsed, bytes=output_bytes, failures=failures,
                sword_episodes=sum(r.get('sword_acquired',False) for r in completed.values()),
                deaths=sum(r['status']=='death' for r in completed.values()),
                resources=resource, updated_at=time.time(), stop_reason=stop_reason)
            publish(history_path, progress)
            publish(batch / 'status.json', progress)
            if rows >= plan['target_steps'] and not pending:
                break
            time.sleep(2)
        if rows >= plan['target_steps']:
            status = 'completed'
    finally:
        pool.close()
        pool.join()
    progress.update(status=status, pending=0, updated_at=time.time(), stop_reason=stop_reason)
    publish(history_path, progress)
    publish(batch / 'status.json', progress)
    print(json.dumps(progress), flush=True)


def main():
    global STOP
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--target-steps', type=int, default=16_777_216)
    parser.add_argument('--hours', type=float, default=8)
    parser.add_argument('--benchmark', action='store_true')
    parser.add_argument('--counts', default='8,16,24,32,48,64')
    parser.add_argument('--benchmark-steps', type=int, default=768)
    parser.add_argument('--workers', type=int)
    args = parser.parse_args()
    batch = args.directory.resolve()
    if args.target_steps < 1 or args.hours <= 0 or (args.workers is not None and args.workers < 1):
        parser.error('Positive budgets and workers required')
    if args.prepare:
        print(prepare(batch, args.target_steps, args.hours), flush=True)
        return
    if ROOT != batch / 'runtime':
        parser.error('Run the frozen runtime/scripts/data_workset.py inside the selected batch')
    verify_runtime(batch)
    import fcntl
    with (batch / 'supervisor.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def request_stop(signum, frame):
            global STOP
            STOP = True
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        if args.benchmark:
            workers = benchmark(batch, [int(n) for n in args.counts.split(',')], args.benchmark_steps)
            publish(batch / 'selected-workers.json', dict(workers=workers, rule='smallest within 10% of peak SPS'))
        else:
            workers = args.workers or json.loads((batch / 'selected-workers.json').read_text())['workers']
            train_collection(batch, workers)


if __name__ == '__main__':
    main()

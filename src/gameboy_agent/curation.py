"""Observable trajectory labels, not claims of optimal actions or causality."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from gameboy_agent.dataset import sha256, unpack_observation

CONFIG = dict(version='ladx-curation-v1', navigation_window=32, safety_lookahead=16,
              recovery_horizon=64, damage_cluster_gap=8, minimum_displacement=24,
              development_percent=10, split_salt='ladx-curation-v1-fixed')
COLUMNS = ['step', 'skill', 'room', 'next_room', 'x', 'y', 'next_x', 'next_y',
           'health', 'next_health', 'sword', 'terminated', 'truncated']
INDEX_SCHEMA = pa.schema([
    ('segment_id', pa.string()), ('split', pa.string()), ('cohort_id', pa.string()),
    ('source_batch_id', pa.string()), ('source_run_id', pa.string()),
    ('source_episode_id', pa.string()), ('source_path', pa.string()),
    ('source_sha256', pa.string()), ('start', pa.string()), ('epsilon', pa.float64()),
    ('step_start', pa.int32()), ('step_end', pa.int32()), ('anchor_step', pa.int32()),
    ('label', pa.string()), ('lane', pa.string()), ('imitation_eligible', pa.bool_()),
    ('contains_setup', pa.bool_()), ('terminal_episode_outcome', pa.string()),
    ('target_room', pa.list_(pa.int16(), 3)), ('target_x', pa.int16()), ('target_y', pa.int16()),
    ('harness_privilege', pa.string()), ('completion_evaluated', pa.bool_()),
])


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def cohort(meta, state_hash):
    # All epsilon variants with the same physical setup stay together. This is
    # a development split; it is not a replacement for frozen game evaluation.
    key = stable_hash([state_hash, meta['setup_actions']])
    value = int(stable_hash([CONFIG['split_salt'], key])[:16], 16) % 100
    return key, 'dev' if value < CONFIG['development_percent'] else 'train'


def label_episode(data, meta):
    """Return half-open step ranges; all horizons count recorded actions."""
    n = len(data['step'])
    if data['step'] != list(range(n)) or n != meta['rows']:
        raise ValueError('Episode step/count mismatch')
    skill = np.asarray(data['skill'])
    room, nxt = np.asarray(data['room']), np.asarray(data['next_room'])
    x, y = np.asarray(data['x']), np.asarray(data['y'])
    nx, ny = np.asarray(data['next_x']), np.asarray(data['next_y'])
    health, nh = np.asarray(data['health']), np.asarray(data['next_health'])
    damage = nh < health
    terminal = np.asarray(data['terminated']) | np.asarray(data['truncated'])
    labels = []

    def moved(a, b):
        return bool(np.any(room[a] != nxt[b - 1]) or
                    abs(int(nx[b - 1]) - int(x[a])) + abs(int(ny[b - 1]) - int(y[a]))
                    >= CONFIG['minimum_displacement'])

    def emit(a, b, label, lane, *, anchor=None, eligible=False):
        if not 0 <= a < b <= n:
            raise ValueError('Invalid segment boundaries')
        labels.append(dict(step_start=a, step_end=b, anchor_step=a if anchor is None else anchor,
                           label=label, lane=lane, imitation_eligible=eligible,
                           contains_setup=bool(np.any(skill[a:b] == 'physical_setup')),
                           target_room=nxt[b-1].tolist(), target_x=int(nx[b-1]), target_y=int(ny[b-1])))

    # Later death does not invalidate an already completed, clean prerequisite.
    sword_steps = np.flatnonzero(skill == 'acquire_sword')
    end = meta.get('sword_step')
    if sword_steps.size and end is not None:
        a, b = int(sword_steps[0]), int(end)
        if (a < b <= n and np.all(skill[a:b] == 'acquire_sword') and
                data['sword'][b-1] and nh[b-1] > 0 and not damage[a:b].any()):
            emit(a, b, 'clean_sword_acquisition', 'imitation', eligible=True)

    w, guard = CONFIG['navigation_window'], CONFIG['safety_lookahead']
    exploration = np.flatnonzero(skill == 'explore')
    if exploration.size:
        for a in range(int(exploration[0]), n - w - guard + 1, w):
            b, horizon = a + w, a + w + guard
            if (np.all(skill[a:horizon] == 'explore') and not damage[a:horizon].any()
                    and not terminal[a:horizon].any() and moved(a, b)):
                emit(a, b, 'observed_safe_navigation', 'hindsight_navigation')

    hits = np.flatnonzero(damage).tolist()
    clusters = []
    for step in hits:
        if clusters and step - clusters[-1][-1] <= CONFIG['damage_cluster_gap']:
            clusters[-1].append(step)
        else:
            clusters.append([step])
    for cluster in clusters:
        first, last = cluster[0], cluster[-1]
        emit(max(0, first-16), min(n, last+17), 'damage_event', 'event', anchor=first)
        if nh[last] == 0 or last + 1 >= n:
            # There is no recorded recovery action after a lethal/final hit.
            continue
        a, limit = last + 1, min(n, last + 1 + CONFIG['recovery_horizon'])
        deaths = np.flatnonzero(nh[a:limit] == 0)
        repeats = np.flatnonzero(damage[a:limit])
        if deaths.size:
            b = a + int(deaths[0]) + 1
            label = 'recovery_ended_in_death'
        elif repeats.size:
            b = a + int(repeats[0]) + 1
            label = 'recovery_repeat_damage'
        elif limit - a < CONFIG['recovery_horizon'] or terminal[a:limit].any():
            b, label = limit, 'recovery_censored'
        elif moved(a, limit):
            b, label = limit, 'observed_safe_recovery'
        else:
            b, label = limit, 'recovery_no_net_progress'
        emit(a, b, label, 'recovery', anchor=last)

    if meta['status'] in ('death', 'sword_timeout'):
        emit(max(0, n-64), n, meta['status'] + '_context', 'failure', anchor=n-1)
    return labels


def load_segment(curated, segment, *, allowed_split='train', allow_candidates=False):
    """Default loader accepts only the training imitation lane.

    Other labels require explicit opt-in; hindsight endpoints are observations,
    not objectives that were supplied to the behavior policy.
    """
    curated = Path(curated)
    manifest = json.loads((curated / 'manifest.json').read_text())
    index = curated / 'segments.parquet'
    if sha256(index) != manifest['artifacts']['segments.parquet']:
        raise ValueError('Curated index integrity mismatch')
    selected = pq.read_table(index, filters=[('segment_id', '=', segment['segment_id'])]).to_pylist()
    if len(selected) != 1 or selected[0] != segment:
        raise ValueError('Segment not registered in curated index')
    if segment['split'] != allowed_split:
        raise ValueError('Split not allowed')
    if not allow_candidates and not segment['imitation_eligible']:
        raise ValueError('Segment is not an imitation target')
    source = Path(manifest['source_batch']) / segment['source_path']
    if sha256(source) != segment['source_sha256']:
        raise ValueError('Source integrity mismatch')
    table = pq.read_table(source)
    meta = json.loads((source.parent / 'manifest.json').read_text())
    if meta['episode_id'] != segment['source_episode_id'] or meta['split'] != 'train':
        raise ValueError('Source provenance mismatch')
    a, b = segment['step_start'], segment['step_end']
    if not 0 <= a < b <= table.num_rows:
        raise ValueError('Segment outside source episode')
    rows = table.slice(a, b-a).to_pylist()
    return dict(segment=segment, rows=rows,
                observations=[unpack_observation(r['observation'], meta['observation_layout']) for r in rows])

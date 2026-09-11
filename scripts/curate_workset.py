"""Create immutable training indexes from verified raw episode shards."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import pyarrow as pa
import pyarrow.parquet as pq
from gameboy_agent.dataset import sha256
from gameboy_agent.curation import CONFIG, COLUMNS, INDEX_SCHEMA, cohort, label_episode, stable_hash, load_segment


def build(batch, out, workers=8):
    batch, out = Path(batch).resolve(), Path(out).resolve()
    if workers < 1:
        raise ValueError('Worker count must be positive')
    status = json.loads((batch / 'status.json').read_text())
    if status['status'] != 'completed':
        raise ValueError('Curation requires a completed immutable batch')
    assets = json.loads((batch / 'assets.json').read_text())
    for name, digest in assets.items():
        if sha256(batch / 'assets' / name) != digest:
            raise ValueError('Source asset mismatch')
    sources, canonical, inventory = [], {}, []
    raw_rows, duplicate_rows = 0, 0
    for path in sorted((batch / 'train').glob('*/*/manifest.json')):
        meta = json.loads(path.read_text())
        if meta['split'] != 'train':
            raise ValueError('Evaluation data must not be curated into training')
        raw_rows += meta['rows']
        group, split = cohort(meta, assets[meta['start'] + '.state'])
        signature = stable_hash([assets[meta['start'] + '.state'], meta['action_sha256'], meta['fingerprint']])
        duplicate_of = canonical.get(signature)
        record = dict(source_episode_id=meta['episode_id'], source_run_id=meta['run_id'],
                      source_path=str((path.parent / 'steps.parquet').relative_to(batch)),
                      source_sha256=meta['parquet_sha256'], manifest_sha256=sha256(path),
                      rows=meta['rows'], cohort_id=group, split=split, duplicate_of=duplicate_of)
        inventory.append(record)
        if duplicate_of:
            duplicate_rows += meta['rows']
        else:
            canonical[signature] = meta['episode_id']
            sources.append((path, meta, record))
    if raw_rows != status['rows'] or len(inventory) != status['episodes']:
        raise ValueError('Raw inventory does not match completion status')
    if len({r['source_episode_id'] for r in inventory}) != len(inventory):
        raise ValueError('Duplicate source episode IDs')

    out.mkdir(parents=True, exist_ok=False)
    (out / 'curation.py').write_bytes((ROOT / 'src/gameboy_agent/curation.py').read_bytes())
    shutil.copy2(Path(__file__), out / 'curate_workset.py')
    (out / 'source-inventory.json').write_text(json.dumps(inventory, indent=2))
    counts, splits, ranges, seen_ids = Counter(), Counter(), Counter(), set()
    paths = []
    writer = pq.ParquetWriter(out / 'segments.parquet.partial', INDEX_SCHEMA, compression='zstd')

    def process(item):
        path, meta, record = item
        source = path.parent / 'steps.parquet'
        if sha256(source) != meta['parquet_sha256']:
            raise ValueError('Source shard integrity mismatch')
        for filename, key in (('final.state','final_state_sha256'), ('events.json','events_sha256')):
            if sha256(path.parent / filename) != meta[key]:
                raise ValueError('Source supporting artifact mismatch')
        data = pq.read_table(source, columns=COLUMNS).to_pydict()
        result = []
        for label in label_episode(data, meta):
            segment = dict(**label, split=record['split'], cohort_id=record['cohort_id'],
                source_batch_id=meta['batch_id'], source_run_id=meta['run_id'],
                source_episode_id=meta['episode_id'], source_path=record['source_path'],
                source_sha256=meta['parquet_sha256'], start=meta['start'], epsilon=meta['epsilon'],
                terminal_episode_outcome=meta['status'], harness_privilege='D', completion_evaluated=False)
            segment['segment_id'] = stable_hash([CONFIG['version'], meta['episode_id'], label])
            result.append(segment)
        return result

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for index, segments in enumerate(executor.map(process, sources)):
                if segments:
                    writer.write_table(pa.Table.from_pylist(segments, schema=INDEX_SCHEMA))
                for s in segments:
                    if s['segment_id'] in seen_ids:
                        raise ValueError('Duplicate segment ID')
                    seen_ids.add(s['segment_id'])
                    counts[s['label']] += 1
                    splits[f"{s['split']}/{s['lane']}"] += 1
                    ranges[s['label']] += s['step_end'] - s['step_start']
                    if s['imitation_eligible'] and s['contains_setup']:
                        raise ValueError('Setup leaked into imitation lane')
                if (index + 1) % 500 == 0:
                    print(json.dumps(dict(episodes=index+1, total_episodes=len(sources), segments=len(seen_ids))), flush=True)
    finally:
        writer.close()
    (out / 'segments.parquet.partial').rename(out / 'segments.parquet')
    # A compact materialized index per split/lane enables explicit training APIs.
    table = pq.read_table(out / 'segments.parquet')
    import pyarrow.compute as pc
    for key in splits:
        split, lane = key.split('/')
        selected = table.filter(pc.and_(pc.equal(table['split'], split), pc.equal(table['lane'], lane)))
        path = out / split / f'{lane}.parquet'
        path.parent.mkdir(exist_ok=True)
        pq.write_table(selected, path, compression='zstd')
        paths.append(str(path.relative_to(out)))
    manifest = dict(schema=CONFIG['version'], config=CONFIG, source_batch=str(batch),
        source_batch_id=json.loads((batch / 'plan.json').read_text())['batch_id'],
        source_status_sha256=sha256(batch / 'status.json'), assets=assets,
        raw_episodes=len(inventory), raw_rows=raw_rows, retained_episodes=len(sources),
        excluded_duplicate_episodes=len(inventory)-len(sources), excluded_duplicate_rows=duplicate_rows,
        segments=len(seen_ids), labels=dict(counts), split_lanes=dict(splits),
        range_rows_with_overlap=dict(ranges), interval_convention='start inclusive, end exclusive',
        split_note='Grouped development split; shared base savestates, not independent benchmark evaluation',
        imitation_note='Only clean sword acquisition is eligible by default; navigation/recovery are observed outcome candidates',
        completion_evaluated=False, harness_privilege='D')
    manifest['artifacts'] = {str(p.relative_to(out)):sha256(p) for p in out.rglob('*') if p.is_file()}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest), flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('batch', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    build(args.batch, args.out, args.workers)

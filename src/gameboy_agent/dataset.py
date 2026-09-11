"""Versioned, immutable Parquet episode shards with complete observations."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

VERSION = 'gameboy-motor-v1'
SCHEMA = pa.schema([
    ('schema_version', pa.string()), ('run_id', pa.string()), ('producer_id', pa.string()),
    ('episode_id', pa.string()), ('split', pa.string()), ('seed', pa.int64()),
    ('step', pa.int32()), ('action', pa.list_(pa.int8(), 2)), ('skill', pa.string()),
    ('supervision', pa.string()), ('observation', pa.binary()), ('next_observation', pa.binary()),
    ('room', pa.list_(pa.int16(), 3)), ('next_room', pa.list_(pa.int16(), 3)),
    ('x', pa.int16()), ('y', pa.int16()), ('health', pa.int16()),
    ('next_x', pa.int16()), ('next_y', pa.int16()), ('next_health', pa.int16()),
    ('sword', pa.bool_()), ('reward_total', pa.float64()), ('reward_components', pa.string()),
    ('frames_advanced', pa.int32()), ('wait_frames', pa.int32()),
    ('terminated', pa.bool_()), ('truncated', pa.bool_()), ('screen_png', pa.binary()),
    ('harness_privilege', pa.string()), ('completion_evaluated', pa.bool_()),
])


def observation_layout(obs):
    return [{'name': k, 'shape': list(v.shape), 'dtype': v.dtype.str, 'bytes': v.nbytes}
            for k, v in sorted(obs.items())]


def pack_observation(obs, layout):
    chunks = []
    for field in layout:
        value = np.ascontiguousarray(obs[field['name']])
        if (list(value.shape) != field['shape'] or value.dtype.str != field['dtype']
                or value.nbytes != field['bytes']):
            raise ValueError('Observation layout changed')
        chunks.append(value.tobytes())
    return b''.join(chunks)


def unpack_observation(blob, layout):
    if len(blob) != sum(f['bytes'] for f in layout):
        raise ValueError('Observation size mismatch')
    result, offset = {}, 0
    for field in layout:
        result[field['name']] = np.frombuffer(blob[offset:offset + field['bytes']],
            dtype=field['dtype']).reshape(field['shape']).copy()
        offset += field['bytes']
    return result


def screen_bytes(boy):
    output = io.BytesIO()
    boy.screen.image.save(output, format='PNG')
    return output.getvalue()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


class EpisodeWriter:
    """Manifest is the commit marker; incomplete attempts remain uncommitted."""
    def __init__(self, directory, metadata, layout):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.metadata, self.layout = metadata, layout
        schema = SCHEMA.with_metadata({b'observation_layout': json.dumps(layout).encode(),
                                      b'schema_version': VERSION.encode()})
        self.writer = pq.ParquetWriter(self.directory / 'steps.parquet.partial', schema,
                                       compression='zstd', compression_level=3)
        self.rows, self.count = [], 0

    def add(self, row):
        self.rows.append(row)
        self.count += 1
        if len(self.rows) >= 256:
            self.flush()

    def flush(self):
        if self.rows:
            self.writer.write_table(pa.Table.from_pylist(self.rows, schema=SCHEMA))
            self.rows.clear()

    def finish(self, outcome):
        self.flush()
        self.writer.close()
        temporary = self.directory / 'steps.parquet.partial'
        final = self.directory / 'steps.parquet'
        temporary.rename(final)
        meta = {**self.metadata, **outcome, 'schema_version': VERSION,
                'rows': self.count, 'observation_layout': self.layout,
                'parquet_sha256': sha256(final), 'parquet_bytes': final.stat().st_size}
        with (self.directory / 'manifest.json').open('x') as stream:
            json.dump(meta, stream, indent=2)
        return meta

    def abort(self):
        self.writer.close()

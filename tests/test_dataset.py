"""Lossless observations, explicit schema, and shard commit boundaries."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ModuleNotFoundError:
    raise unittest.SkipTest('Optional data-workset dependencies are not installed')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.dataset import (EpisodeWriter, SCHEMA, observation_layout,
                                  pack_observation, unpack_observation, sha256)


class DatasetTest(unittest.TestCase):
    def test_exact_observation_roundtrip_and_shape_guard(self):
        obs = dict(ids=np.array([0, 255], dtype=np.int32),
                   values=np.array([[-.5, 1.25]], dtype=np.float32),
                   tiles=np.arange(12, dtype=np.uint8).reshape(3, 4)[:, ::2])
        layout = observation_layout(obs)
        packed = pack_observation(obs, layout)
        result = unpack_observation(packed, json.loads(json.dumps(layout)))
        for name in obs:
            np.testing.assert_array_equal(obs[name], result[name])
            self.assertEqual(obs[name].dtype, result[name].dtype)
        with self.assertRaisesRegex(ValueError, 'size mismatch'):
            unpack_observation(packed[:-1], layout)
        with self.assertRaisesRegex(ValueError, 'layout changed'):
            pack_observation({**obs, 'ids': obs['ids'].astype(np.uint8)}, layout)

    def test_commit_marker_and_exclusive_episode_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'episode'
            writer = EpisodeWriter(root, {'episode_id': 'test'}, [])
            self.assertFalse((root / 'manifest.json').exists())
            row = {}
            for field in SCHEMA:
                if pa.types.is_fixed_size_list(field.type):
                    value = [0] * field.type.list_size
                elif pa.types.is_string(field.type):
                    value = ''
                elif pa.types.is_binary(field.type):
                    value = b''
                elif pa.types.is_boolean(field.type):
                    value = False
                else:
                    value = 0
                row[field.name] = value
            row.update(schema_version='gameboy-motor-v1', episode_id='test', step=0,
                       action=[1, 0], observation=b'abc', next_observation=b'def',
                       split='train', terminated=False, truncated=True)
            writer.add(row)
            result = writer.finish({'status': 'budget_exhausted'})
            self.assertEqual(result['rows'], 1)
            self.assertEqual(result['parquet_sha256'], sha256(root / 'steps.parquet'))
            self.assertEqual(pq.read_table(root / 'steps.parquet')['action'].to_pylist(), [[1, 0]])
            self.assertTrue((root / 'manifest.json').exists())
            self.assertFalse((root / 'steps.parquet.partial').exists())
            with self.assertRaises(FileExistsError):
                EpisodeWriter(root, {}, [])

    def test_aborted_attempt_has_no_commit_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'episode'
            writer = EpisodeWriter(root, {}, [])
            writer.abort()
            self.assertFalse((root / 'manifest.json').exists())
            self.assertTrue((root / 'steps.parquet.partial').exists())


if __name__ == '__main__':
    unittest.main()

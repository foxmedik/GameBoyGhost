import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('room15_labels', Path(__file__).resolve().parents[1] / 'scripts/extract_room15_teacher_labels.py')
labels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(labels)


class LabelBoundaryTests(unittest.TestCase):
    def test_diagnostic_collection_cannot_be_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'plan.json').write_text(json.dumps({'schema': 'room15-overnight-diagnostics-v1'}))
            output = root / 'labels'
            with patch('sys.argv', ['extract', '--collection', str(root), '--output', str(output)]):
                with self.assertRaisesRegex(RuntimeError, 'fresh, explicitly authorized'):
                    labels.main()
            self.assertFalse(output.exists())

    def test_failed_teacher_gate_blocks_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gate = root / 'gate.json'
            gate.write_text(json.dumps({'status': 'complete', 'gate_passed': False}))
            (root / 'plan.json').write_text(json.dumps(dict(
                schema='room15-teacher-demonstrations-v1', labels_authorized=True,
                teacher_gate_summary=str(gate), teacher_gate_sha256=labels.digest(gate))))
            output = root / 'labels'
            with patch('sys.argv', ['extract', '--collection', str(root), '--output', str(output)]):
                with self.assertRaisesRegex(RuntimeError, 'has not passed'):
                    labels.main()
            self.assertFalse(output.exists())

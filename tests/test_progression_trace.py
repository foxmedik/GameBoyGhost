"""Terminal quest results must remain recorded and distinguish success from failure."""
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('progression_runner', ROOT/'scripts/run_toadstool_progression.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TraceTerminalTests(unittest.TestCase):
    def test_terminal_success_is_retained_but_death_and_timeout_fail(self):
        for success, terminated, truncated in ((True,True,False),(False,True,False),(False,False,True)):
            with self.subTest(success=success, terminated=terminated, truncated=truncated):
                env = SimpleNamespace(pyboy=object(),total_steps=0,frames=0,episode_actions=[])
                rows, stream = [], io.StringIO()
                trace = runner.Trace(env,stream,rows)
                def step():
                    env.total_steps += 1
                    env.frames += 1
                    env.episode_actions.append({'buttons':[]})
                    return None,0,terminated,truncated,{'events':[], 'task_success':success}
                with patch.object(runner,'snapshot',return_value={'health':4 if success else 0}), patch.object(runner,'fingerprint',return_value='fingerprint'):
                    if success:
                        self.assertTrue(trace.record(step)[4]['task_success'])
                    else:
                        with self.assertRaisesRegex(RuntimeError,'Episode ended'):
                            trace.record(step)
                self.assertEqual(len(rows),1)
                self.assertEqual(json.loads(stream.getvalue()),rows[0])
                self.assertEqual(rows[0]['frame'],1)


if __name__ == '__main__':
    unittest.main()

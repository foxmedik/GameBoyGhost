"""The behavior-preservation loss must optimize the student, not its teacher."""
import sys
from pathlib import Path
import unittest
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
try:
    from navigation_recovery import parent_divergence
except ModuleNotFoundError:
    raise unittest.SkipTest('Optional navigation data dependencies not installed')


class RecoveryLossTest(unittest.TestCase):
    def test_identical_predictions_have_zero_divergence(self):
        torch.manual_seed(1)
        logits=torch.randn(32,8)
        self.assertAlmostEqual(float(parent_divergence(logits,logits)),0.0,places=6)

    def test_gradient_moves_student_toward_frozen_parent(self):
        torch.manual_seed(2)
        parent=torch.randn(32,8,requires_grad=True)
        student=torch.randn(32,8,requires_grad=True)
        before=parent_divergence(student,parent)
        before.backward()
        self.assertIsNone(parent.grad)
        self.assertTrue(torch.isfinite(student.grad).all())
        with torch.no_grad():student-=student.grad
        self.assertLess(float(parent_divergence(student,parent)),float(before))


if __name__=='__main__':unittest.main()

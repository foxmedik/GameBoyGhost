import sys,unittest
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from train_navigation_routes import action_margin_loss

class NavigationMarginTests(unittest.TestCase):
    def test_margin_satisfied_has_no_penalty_or_gradient(self):
        z=torch.tensor([[2.,0.,0.,0.,0.,0.,2.,0.]],requires_grad=True)
        loss=action_margin_loss(z,torch.tensor([[0,1]]),.25);loss.backward()
        self.assertEqual(loss.item(),0.)
        self.assertTrue(torch.equal(z.grad,torch.zeros_like(z)))

    def test_violation_pushes_toward_demonstrated_action(self):
        z=torch.tensor([[0.,1.,0.,0.,0.,1.,0.,0.]],requires_grad=True)
        loss=action_margin_loss(z,torch.tensor([[0,1]]),.25);loss.backward()
        self.assertAlmostEqual(loss.item(),1.5625)
        self.assertLess(z.grad[0,0].item(),0)
        self.assertGreater(z.grad[0,1].item(),0)
        self.assertLess(z.grad[0,6].item(),0)
        self.assertGreater(z.grad[0,5].item(),0)

if __name__=='__main__':unittest.main()

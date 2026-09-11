import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import torch
from gameboy_agent.navigation import NavigationNet
from button_only_training import freeze_movement,assert_movement_unchanged

class ButtonOnlyTests(unittest.TestCase):
    def test_adam_updates_buttons_without_changing_any_movement_logits(self):
        torch.manual_seed(71)
        model=NavigationNet(250);model.eval();x=torch.randn(32,250)
        reference=freeze_movement(model);before=model(x).detach().clone()
        optimizer=torch.optim.Adam(model.parameters(),lr=0.01)
        for _ in range(8):
            optimizer.zero_grad();z=model(x)
            # Include deliberately conflicting movement loss to exercise masking.
            loss=torch.nn.functional.cross_entropy(z[:,:5],torch.zeros(32,dtype=torch.long))+torch.nn.functional.cross_entropy(z[:,5:],torch.ones(32,dtype=torch.long))
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step()
            assert_movement_unchanged(model,reference)
            self.assertTrue(torch.equal(before[:,:5],model(x).detach()[:,:5]))
        self.assertFalse(torch.equal(before[:,5:],model(x).detach()[:,5:]))
        restored=NavigationNet(250);restored.load_state_dict(model.state_dict())
        self.assertTrue(torch.equal(before[:,:5],restored(x).detach()[:,:5]))

    def test_invariant_detects_movement_weight_change(self):
        model=NavigationNet(250);ref=freeze_movement(model)
        with torch.no_grad():model.net[4].bias[0]+=1
        with self.assertRaises(AssertionError):assert_movement_unchanged(model,ref)

if __name__=='__main__':unittest.main()

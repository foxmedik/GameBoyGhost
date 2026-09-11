"""Protect the selected navigation function while learning button logits."""
import torch


def freeze_movement(model):
    for p in model.parameters():
        p.requires_grad_(False)
    output=model.net[4]
    assert isinstance(output,torch.nn.Linear) and output.out_features==8
    output.weight.requires_grad_(True);output.bias.requires_grad_(True)
    def only_buttons(grad):
        grad=grad.clone();grad[:5]=0;return grad
    output.weight.register_hook(only_buttons);output.bias.register_hook(only_buttons)
    return {k:v.detach().clone() for k,v in model.state_dict().items()}


def assert_movement_unchanged(model,reference):
    for name,value in model.state_dict().items():
        if name in ('net.4.weight','net.4.bias'):
            assert torch.equal(value[:5],reference[name][:5]),name
        else:
            assert torch.equal(value,reference[name]),name

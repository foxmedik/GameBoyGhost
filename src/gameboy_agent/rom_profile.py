"""LADX English 1.1 profile verified by a byte-identical disassembly build."""
import hashlib
from pathlib import Path

ROM_SHA256 = '6285ba6201f17bc8595c600ebc2477d52561f0aff29b11f7fc3343bacb2e230b'
HOOKS = {
    'push': (0x15, 0x7415, bytes.fromhex('3e3ee0f2')),
    'collision': (0x02, 0x729F, bytes.fromhex('f0affe69')),
    'shield': (0x03, 0x6C45, bytes.fromhex('3e16e0f2')),
    'sword': (0x03, 0x7190, bytes.fromhex('793ceaacc1')),
}


def validate_rom(path: Path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != ROM_SHA256:
        raise ValueError('Unsupported ROM for structured LADX adapter; requires verified English 1.1 hash')
    for name, (bank, address, expected) in HOOKS.items():
        offset = bank * 0x4000 + address - 0x4000
        if data[offset:offset+len(expected)] != expected:
            raise ValueError(f'Hook signature mismatch: {name}')


class RevisionHooks:
    """Strict hook lifecycle; no shared mutation of upstream Register enums."""
    def _register_profile_hook(self, name, flag, registered, once=False):
        if getattr(self, registered):
            return
        bank, address, _ = HOOKS[name]
        def callback(env):
            setattr(env, flag, True)
            # Do not mutate PyBoy's active breakpoint table from its callback.
            # A boolean already coalesces repeated hits within the action;
            # the action's finally block deregisters after tick() returns.
        self.pyboy.hook_register(bank, address, callback, self)
        setattr(self, registered, True)

    def _deregister_profile_hook(self, name, registered):
        if not getattr(self, registered):
            return
        bank, address, _ = HOOKS[name]
        self.pyboy.hook_deregister(bank, address)
        setattr(self, registered, False)

    def register_collision(self):
        self._register_profile_hook('collision', 'collided_object', 'collided_object_registered')
    def deregister_collision(self):
        self._deregister_profile_hook('collision', 'collided_object_registered')
    def register_push_sfx(self):
        self._register_profile_hook('push', 'push_sfx', 'push_sfx_registered', once=True)
    def deregister_push_sfx(self):
        self._deregister_profile_hook('push', 'push_sfx_registered')
    def register_block_sfx(self):
        self._register_profile_hook('shield', 'block_sfx', 'block_sfx_registered')
    def deregister_block_sfx(self):
        self._deregister_profile_hook('shield', 'block_sfx_registered')
    def register_sword_dmg(self):
        self._register_profile_hook('sword', 'sword_dmg', 'sword_dmg_registered')
    def deregister_sword_dmg(self):
        self._deregister_profile_hook('sword', 'sword_dmg_registered')

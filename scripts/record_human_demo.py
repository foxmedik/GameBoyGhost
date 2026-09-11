"""Play from the house state and save an input-aligned human demonstration.

PyBoy owns the visible SDL window and Bluetooth controller. Every emulated
frame gets a PNG and an ``actions.jsonl`` row, so later training can match an
image to the buttons held for the frame without guessing from video.
"""
import argparse
import ctypes
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from pyboy import PyBoy
from pyboy.plugins import window_sdl2
import sdl2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gameboy_agent.progression import snapshot
from gameboy_agent.transitions import BUTTONS


DEFAULT_ROM = ROOT / "Legend of Zelda, The - Link's Awakening DX (USA, Europe) (Rev A) (SGB Enhanced).gbc"
DEFAULT_STATE = ROOT / "runs/navigation-chain-house-v1/initial.state"
TAG_KEYS = {
    sdl2.SDL_SCANCODE_1: "combat", sdl2.SDL_SCANCODE_2: "shield",
    sdl2.SDL_SCANCODE_3: "spin_slash", sdl2.SDL_SCANCODE_4: "cut_terrain",
    sdl2.SDL_SCANCODE_5: "item_use", sdl2.SDL_SCANCODE_6: "recovery",
    sdl2.SDL_SCANCODE_7: "npc_or_dialogue", sdl2.SDL_SCANCODE_8: "route_landmark",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE,
                        help="Initial state; default is the supplied house state.")
    parser.add_argument("--out", type=Path, default=ROOT / "runs/human-demos" / stamp)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--frame-stride", type=int, default=1,
                        help="Save one PNG every N emulated frames; 1 preserves every frame.")
    return parser.parse_args()


def make_boy(rom, state, scale):
    # PyBoy's own SDL window handles Bluetooth controllers. Keeping one SDL
    # runtime avoids the duplicate-SDL crash hazard from pygame + PyBoy.
    boy = PyBoy(str(rom), window="SDL2", scale=scale)
    with state.open("rb") as source:
        boy.load_state(source)
    for button in BUTTONS:
        boy.button_release(button)
    return boy


def open_connected_controller():
    """Open an already-paired controller, not just a newly-added SDL device."""
    if hasattr(window_sdl2, "_sdlcontroller"):
        return
    for index in range(sdl2.SDL_NumJoysticks()):
        if sdl2.SDL_IsGameController(index):
            window_sdl2._sdlcontroller = sdl2.SDL_GameControllerOpen(index)
            name = sdl2.SDL_GameControllerName(window_sdl2._sdlcontroller)
            print("Controller:", name.decode() if name else f"SDL device {index}")
            return
    print("Controller: none detected; connect one and restart, or use keyboard.")


def held_buttons(boy):
    """Read PyBoy's controller state after its SDL event pump ran this frame."""
    interaction = boy.mb.interaction
    directional, standard = int(interaction.directional), int(interaction.standard)
    result = set()
    for mask, button in ((1, "right"), (2, "left"), (4, "up"), (8, "down")):
        if not directional & mask:
            result.add(button)
    for mask, button in ((1, "a"), (2, "b"), (4, "select"), (8, "start")):
        if not standard & mask:
            result.add(button)
    return result


def pressed_scancodes():
    count = ctypes.c_int()
    keys = sdl2.SDL_GetKeyboardState(ctypes.byref(count))
    return {code for code in (*TAG_KEYS, sdl2.SDL_SCANCODE_R)
            if code < count.value and keys[code]}


def main():
    args = parse_args()
    if args.scale < 1 or args.frame_stride < 1:
        raise SystemExit("--scale and --frame-stride must be positive")
    for path in (args.rom, args.state):
        if not path.is_file():
            raise SystemExit(f"Missing file: {path}")
    out = args.out.resolve()
    if out.exists():
        raise SystemExit(f"Output already exists: {out}")
    frames_dir = out / "frames"
    frames_dir.mkdir(parents=True)

    print("Controls: PyBoy's SDL controller support: D-pad, B=Game Boy A, A=Game Boy B, Back=Select, Start=Start.")
    print("Keyboard fallback: arrows, A=Game Boy A, S=Game Boy B, Return=Start, Backspace=Select.")
    print("Tags: 1 combat, 2 shield, 3 spin, 4 cut, 5 item, 6 recovery, 7 NPC, 8 landmark. R resets; Esc ends.")

    boy = make_boy(args.rom, args.state, args.scale)
    open_connected_controller()
    frame = 0
    resets = 0
    tags = []
    previous_scancodes = set()
    running = True
    started = time.time()
    initial = snapshot(boy)
    actions = (out / "actions.jsonl").open("x")
    tag_file = (out / "tags.jsonl").open("x")
    try:
        while running:
            if not boy.tick(1, render=True):
                running = False
                break
            scancodes = pressed_scancodes()
            rising = scancodes - previous_scancodes
            previous_scancodes = scancodes
            if sdl2.SDL_SCANCODE_R in rising:
                if hasattr(window_sdl2, "_sdlcontroller"):
                    del window_sdl2._sdlcontroller
                boy.stop()
                boy = make_boy(args.rom, args.state, args.scale)
                open_connected_controller()
                resets += 1
                tags.append("reset")
                tag_file.write(json.dumps({"frame": frame, "tag": "reset"}) + "\n")
                continue
            for key in rising & TAG_KEYS.keys():
                tag = TAG_KEYS[key]
                tags.append(tag)
                tag_file.write(json.dumps({"frame": frame, "tag": tag, "state": snapshot(boy)}) + "\n")
                tag_file.flush()
            state = snapshot(boy)
            held = held_buttons(boy)
            actions.write(json.dumps({"frame": frame, "buttons": sorted(held), "state": state}) + "\n")
            if frame % args.frame_stride == 0:
                Image.fromarray(boy.screen.ndarray[:, :, :3]).save(frames_dir / f"{frame:08d}.png")
            frame += 1
            if frame % 60 == 0:
                actions.flush()
    finally:
        for button in BUTTONS:
            boy.button_release(button)
        final = snapshot(boy)
        boy.stop()
        actions.close(); tag_file.close()

    manifest = {
        "format": "gameboyghost-human-demo-v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "rom": str(args.rom.resolve()), "rom_sha256": sha256(args.rom),
        "initial_state": str(args.state.resolve()), "initial_state_sha256": sha256(args.state),
        "initial": initial, "final": final, "emulated_frames": frame, "resets": resets,
        "frame_stride": args.frame_stride, "frame_pattern": "frames/{frame:08d}.png",
        "actions": "actions.jsonl", "tags": "tags.jsonl", "wall_seconds": round(time.time() - started, 2),
        "controller_mapping": "PyBoy SDL defaults: D-pad; controller B=Game Boy A, A=Game Boy B, Back=Select, Start=Start",
        "tag_labels": sorted(set(tags)),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Saved {frame} emulated frames to {out}")


if __name__ == "__main__":
    main()

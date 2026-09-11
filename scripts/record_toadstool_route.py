"""Render the verified house-to-mushroom-cave route as a shareable MP4."""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.terrain_navigation import cell, paths, steer, terrain


RUN = ROOT / "runs/progression-forest-terrain-v5"
OUT = ROOT / "runs/videos/toadstool-full-route-v1"
FPS = 30


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    video = OUT / "toadstool-full-route.mp4"
    log = (OUT / "encoding.log").open("w")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    encoder = subprocess.Popen([
        ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", "160x144", "-r", str(FPS), "-i", "-", "-an", "-vf",
        "scale=640:576:flags=neighbor", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video),
    ], stdin=subprocess.PIPE, stderr=log)
    env = ProgressionEnv(RUN / "game.gbc", RUN / "initial.state", max_steps=8000,
                         max_frames=130000)
    frames = 0

    def state():
        memory = env.pyboy.memory
        return tuple(int(memory[address]) for address in
                     (0xDBA5, 0xFFF7, 0xFFF6, 0xFF98, 0xFF99, 0xDB4B))

    def emit():
        nonlocal frames
        image = env.pyboy.screen.ndarray[:, :, :3]
        encoder.stdin.write(image.tobytes())
        if frames == 0:
            Image.fromarray(image).resize((640, 576), Image.Resampling.NEAREST).save(OUT / "poster.png")
        frames += 1

    def raw(buttons, duration):
        for button in buttons:
            env.pyboy.button_press(button)
        for index in range(duration):
            env.pyboy.tick(1, render=True)
            if index % 3 == 0:
                emit()
        for button in buttons:
            env.pyboy.button_release(button)

    try:
        env.reset(seed=0)
        for line in (RUN / "trajectory.jsonl").read_text().splitlines():
            command = json.loads(line)["command"]
            env.step_buttons(command["buttons"], action_frames=command["action_frames"],
                             legacy_action=command["legacy_action"])
            emit()

        # Forest 52 -> outdoor cave mouth in 62.
        raw(("left",), 60)
        raw(("down",), 140)
        for _ in range(80):
            _, _, _, x, y, _ = state()
            route = paths(terrain(env.pyboy), cell(x, y)).get((7, 4), [])
            if not route:
                raise RuntimeError(f"No cave-mouth route from {state()}")
            direction = steer(x, y, route[min(1, len(route) - 1)])
            if direction is not None:
                env.step_buttons(({1: "up", 2: "down", 3: "left", 4: "right"}[direction],),
                                 action_frames=6, legacy_action=(direction, 0))
                emit()
        for direction in (1, 1, 4, 1, 4, 1):
            for _ in range(30):
                env.step_buttons(({1: "up", 4: "right"}[direction],), action_frames=3,
                                 legacy_action=(direction, 0))
                emit()
                if state()[0]:
                    break
            if state()[0]:
                break
        if state()[:3] != (1, 10, 189):
            raise RuntimeError(f"Cave entry failed: {state()}")

        # User-traced crumbling-floor path, then the two verified stone pushes.
        raw(("left", "up"), 18); raw(("left",), 42); raw(("up",), 70); raw(("right", "up"), 92)
        if state()[:3] != (1, 10, 172):
            raise RuntimeError(f"Crumbling-floor route failed: {state()}")
        raw(("up",), 70)
        for _ in range(100):
            raw(("left", "up"), 1)
            if state()[2] == 171:
                break
        raw((), 180)
        if state()[:3] != (1, 10, 171):
            raise RuntimeError(f"Stone room failed: {state()}")
        raw(("down",), 18); raw(("left",), 64)
        raw(("down",), 64)
        raw(("left",), 70); raw(("right",), 12); raw(("down",), 160)
        if state()[:3] != (0, 0, 80):
            raise RuntimeError(f"Overworld mushroom screen failed: {state()}")
        for _ in range(FPS * 3):
            raw((), 1)
    finally:
        env.close()
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError("ffmpeg encoding failed")
        log.close()

    manifest = {
        "video": str(video.relative_to(ROOT)), "poster": str((OUT / "poster.png").relative_to(ROOT)),
        "fps": FPS, "frames": frames, "duration_seconds": round(frames / FPS, 2),
        "source": "continuous physical replay from progression-forest-terrain-v5 initial state",
        "final_state": list(state()), "audio": False,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

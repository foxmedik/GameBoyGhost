"""Build a self-contained Apple-silicon .app for the human demo recorder."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "Legend of Zelda, The - Link's Awakening DX (USA, Europe) (Rev A) (SGB Enhanced).gbc"
STATE = ROOT / "runs/navigation-chain-house-v1/initial.state"
DIST = ROOT / "dist/GameBoyGhost Demo Recorder.app"
SDL2_PACKAGE = ROOT / ".venv-ladx/lib/python3.11/site-packages/sdl2"


def main():
    for path in (ROM, STATE):
        if not path.is_file():
            raise SystemExit(f"Missing required bundled asset: {path}")
    shutil.rmtree(ROOT / "build", ignore_errors=True)
    shutil.rmtree(DIST, ignore_errors=True)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed",
        "--name", "GameBoyGhost Demo Recorder", "--target-architecture", "arm64",
        "--add-data", f"{ROM}:assets", "--add-data", f"{STATE}:assets",
        "--onefile", "--collect-all", "sdl2", "--collect-all", "sdl2dll",
        "--collect-all", "PIL", "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"), str(ROOT / "apps/human_demo_app.py")]
    subprocess.run(command, check=True)
    print(DIST)


if __name__ == "__main__":
    main()

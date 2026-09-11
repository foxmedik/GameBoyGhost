"""Create a macOS .app launcher for the Studio's verified local runtime."""
import plistlib
import shlex
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist/GameBoyGhost Demo Recorder.app"


def main():
    shutil.rmtree(APP, ignore_errors=True)
    macos = APP / "Contents/MacOS"
    macos.mkdir(parents=True)
    (APP / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleName": "GameBoyGhost Demo Recorder",
        "CFBundleDisplayName": "GameBoyGhost Demo Recorder",
        "CFBundleIdentifier": "com.foxmedik.gameboyghost.demo-recorder",
        "CFBundleExecutable": "GameBoyGhost Demo Recorder",
        "CFBundlePackageType": "APPL",
    }))
    launcher = macos / "GameBoyGhost Demo Recorder"
    root = shlex.quote(str(ROOT))
    launcher.write_text(f'''#!/bin/zsh
cd {root}
exec {root}/.venv-ladx/bin/python {root}/apps/human_demo_app.py
''')
    launcher.chmod(0o755)
    print(APP)


if __name__ == "__main__":
    main()

"""Create this project's environment and install its game and fixed voices."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine.services.audio_files import migrate_legacy_audio  # noqa: E402 (standard library only)


def environment_python(root=ROOT, windows=None):
    windows = sys.platform == "win32" if windows is None else windows
    tail = "Scripts/python.exe" if windows else "bin/python"
    for name in (".venv", "venv"):
        python = Path(root) / name / tail
        if python.is_file():
            return python
    return None


def setup(root=ROOT, run=subprocess.run, with_pad=False):
    root = Path(root)
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required. Install it, then run setup again.")
    migrate_legacy_audio(root)
    python = environment_python(root)
    if python is None:
        environment = root / ".venv"
        if environment.exists():
            raise RuntimeError("The .venv folder exists but its Python is missing. Rename that folder and run setup again.")
        run([sys.executable, "-m", "venv", str(environment)], cwd=root, check=True)
        python = environment_python(root)
        if python is None:
            raise RuntimeError("Python could not create the project environment.")
    checked = run([str(python), "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"], cwd=root, check=False)
    if checked.returncode:
        raise RuntimeError("The project environment needs Python 3.11 or newer. Rename the old environment folder and run setup again.")
    # UTF-8 mode for the child Pythons too, whatever the Windows code page.
    env = {**os.environ, "PYTHONUTF8": "1"}
    commands = [[str(python), "-m", "pip", "install", "-r", str(root / "engine/requirements.txt")],
                [str(python), "-m", "pip", "check"],
                [str(python), str(root / "engine/tools/prepare_speech.py"), "--download"]]
    for command in commands:
        run(command, cwd=root, check=True, env=env)
    if with_pad:
        # Optional Bluetooth pad SDK: a failed download is reported but never fails the setup.
        result = run([str(python), str(root / "engine/launcher/prepare_pad.py")], cwd=root, check=False, env=env)
        if result.returncode:
            print("The Bluetooth pad SDK was not installed. The game works without it; run setup with --with-pad again to retry.",
                  file=sys.stderr)
    run([str(python), str(root / "engine/launcher/check_setup.py"), "--synthesize"], cwd=root, check=True, env=env)
    return python


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-pad", action="store_true",
                        help="Also download Dot Inc.'s Dot Pad SDK for the Bluetooth pad (optional)")
    args = parser.parse_args()
    try:
        python = setup(with_pad=args.with_pad)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Setup did not finish: {error}", file=sys.stderr)
        print("Completed downloads are kept. Fix the issue and run setup again.", file=sys.stderr)
        return 1
    print(f"Setup complete: {python}\nStart with start-mac.command or start-windows.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

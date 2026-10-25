"""Download Dot Inc.'s Dot Pad SDK 3.0.3 for the Bluetooth pad (optional).

The game runs without it: only the Bluetooth button needs the SDK; the USB pad and hand tracking do not.
Files come from Dot Inc.'s public SDK guide at a fixed commit and are checked against a pinned size and
SHA-256 before they are used. Run through the installer (install-windows.bat --with-pad or
install-mac.command --with-pad) or directly: python engine/launcher/prepare_pad.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine.tools.prepare_speech import download_file  # noqa: E402

SOURCE = "https://raw.githubusercontent.com/dotincorp/dotpad-sdk-guide/78661ff559eee6831dc85b5dea9e1e92b2a5798f/Web/3.0.3/DemoApp/src/sdk/"
FILES = {
    "DotPadSDK-3.0.3.js": {"size": 122136, "sha256": "6aa9b3e1821da0b383015e91f71c31ee7e51ba282cffdbe2e38e0b29bfc415be"},
    "DotPadSDK-3.0.3.d.ts": {"size": 5824, "sha256": "777449f4358b3bf8bf18ef96dd5ab4b28f5000884b05b801d2013a2042714ac8"},
}
SDK_DIR = "engine/web/core/pad/vendor"


def sdk_path(root=ROOT):
    return Path(root) / SDK_DIR / "DotPadSDK-3.0.3.js"


def main(root=ROOT):
    for name, expected in FILES.items():
        download_file(SOURCE + name, Path(root) / SDK_DIR / name, expected)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Bluetooth pad SDK setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)

"""Check this computer's game setup without starting or changing a game."""
import argparse
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine.services.speech import valid_model_file  # noqa: E402 (Piper itself is imported only for synthesis)

DEPENDENCIES = {"fastapi": ((0, 110), (1,)), "uvicorn": ((0, 29), (1,)),
                "piper-tts": ((1, 8, 0), (1, 8, 1)), "onnxruntime": (None, None)}
ASSETS = ("water", "soil", "cut", "cook", "crop", "correct", "sleep", "door", "coin",
          "background-basic", "background-minigame", "background-shop", "step", "pickaxe",
          "break", "shine", "destroy", "splash")
# Feature sounds moved next to their feature (game/<name>/audio/); the rest stay in engine/web/audio/.
FEATURE_SOUNDS = {"water": "farming", "soil": "farming", "crop": "harvest", "cut": "cooking", "cook": "cooking",
                  "pickaxe": "mining", "break": "mining", "splash": "fishing"}


def sound_path(name):
    """Path of a game sound relative to the project root."""
    folder = f"game/{FEATURE_SOUNDS[name]}/audio" if name in FEATURE_SOUNDS else "engine/web/audio"
    return f"{folder}/{name}.mp3"


def check_setup(root=ROOT, get_version=version, python_version=None, synthesize=False):
    root = Path(root)
    checks = []

    def add(name, ok, detail, fix=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "fix": "" if ok else fix})

    current = python_version or sys.version_info[:3]
    add("Python", current >= (3, 11), ".".join(map(str, current)),
        "Install Python 3.11 or newer, then run the setup file again.")
    for name, (minimum, maximum) in DEPENDENCIES.items():
        try:
            installed = get_version(name)
            numeric = tuple(int(part) for part in installed.split(".") if part.isdigit())
            valid = (minimum is None or numeric >= minimum) and (maximum is None or numeric < maximum)
            # Piper's exact engine version is part of the voice cache identity.
            if name == "piper-tts":
                valid = installed == "1.8.0"
            add(name, valid, installed, "Run install-mac.command or install-windows.bat to install engine/requirements.txt.")
        except PackageNotFoundError:
            add(name, False, "Not installed", "Run the setup file in this project folder.")

    required = ("engine/server/main.py", "engine/server/runtime.py", "engine/core/engine.py",
                "engine/services/speech.py", "engine/services/speech_queue.py", "engine/services/saves.py",
                "game/npc/feature.py", "engine/display/keypad.py", "game/flowers/feature.py",
                "game/fishing/feature.py", "game/seafood/feature.py", "engine/display/dotpad.py",
                "engine/spectator/state.py", "engine/config/game.json", "engine/config/npc.json", "engine/requirements.txt",
                "engine/web/game.html", "engine/web/core/game-audio.js", "engine/web/core/game-speech.js", "engine/web/core/game-keys.js",
                "engine/tools/prepare_demo.py", "engine/tools/prepare_speech.py",
                # Imported or loaded at start but missing from the list before (PR #2):
                "engine/display/icons.py", "game/village/feature.py",
                "engine/web/core/pad/hardware.mjs", "engine/web/core/pad/bluetooth-pad.mjs", "engine/web/core/pad/vendor/package.json",
                "engine/tools/audio_flow.py", "engine/tools/speech_inventory.py")
    missing = [name for name in required if not (root / name).is_file()]
    add("Game files", not missing, "Complete" if not missing else ", ".join(missing),
        "Copy the complete project source, including web and tools folders.")
    missing = [name for name in ASSETS if not (root / sound_path(name)).is_file()
               or not (root / sound_path(name)).stat().st_size]
    add("Game sounds", not missing, "18 files present" if not missing else ", ".join(missing),
        "Restore engine/web/audio and game/*/audio from the project source.")

    config = None
    try:
        config = json.loads((root / "engine/config/speech.json").read_text(encoding="utf-8-sig"))
        if not isinstance(config, dict):
            raise ValueError("Invalid voice configuration")
        if not isinstance(config.get("profiles"), dict) or not config["profiles"] or not config.get("samples"):
            raise ValueError("Invalid profiles or samples")
        for profile, entry in config["profiles"].items():
            if not isinstance(entry, dict) or not isinstance(entry.get("model"), str):
                raise ValueError("Invalid voice model entry")
            model = root / ".audio/voices" / (entry["model"] + ".onnx")
            model_config = model.with_suffix(".onnx.json")
            # Pinned size and SHA-256 from speech.json "downloads"; without them, presence and a valid config.
            expected = config.get("downloads", {}).get(entry["model"], {}).get("files", {})
            broken = [str(path) for path, extension in ((model, ".onnx"), (model_config, ".onnx.json"))
                      if not valid_model_file(path, expected.get(extension))]
            add("Voice: " + profile, not broken, entry["model"] if not broken else "Missing or damaged: " + ", ".join(broken),
                "Run install-mac.command or install-windows.bat again. Missing and damaged voice files are downloaded automatically.")
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        add("Voice configuration", False, "engine/config/speech.json is missing or invalid", "Restore engine/config/speech.json.")

    # Probe existing writable locations using disposable files; no saves or caches are removed.
    for name in ("saves", ".audio/cache"):
        directory = root / name
        parent = directory
        while not parent.exists() and parent != root.parent:
            parent = parent.parent
        try:
            with tempfile.TemporaryFile(dir=parent):
                pass
            add("Writable: " + name, not directory.exists() or directory.is_dir(), str(directory),
                "Move the project into a writable folder, outside protected system folders.")
        except OSError as error:
            add("Writable: " + name, False, str(error), "Move the project into a writable folder.")

    if synthesize and config and all(check["ok"] for check in checks):
        sys.path.insert(0, str(root))
        from engine.services.speech import SpeechService
        with tempfile.TemporaryDirectory(prefix="visionpad-voice-check-") as cache:
            service = SpeechService(root, cache_dir=cache)
            for profile in config["profiles"]:
                try:
                    result = service.generate("Voice check. Ready to play.", profile)
                    add("Voice synthesis: " + profile, service.valid_audio(service.audio_path(result["key"])),
                        "Generated valid WAV in temporary storage")
                except Exception as error:
                    add("Voice synthesis: " + profile, False, str(error),
                        "Run install-mac.command or install-windows.bat again and check the reported package or voice error.")

    return {"ready": all(check["ok"] for check in checks), "platform": platform.platform(),
            "python": sys.executable, "voice_synthesis_requested": synthesize, "checks": checks,
            "scope": "This computer only. Physical pad and headphone perception are not tested."}


def show_report(report):
    for check in report["checks"]:
        print(f"{'OK' if check['ok'] else 'FIX'}  {check['name']}: {check['detail']}")
        if check["fix"]:
            print("     " + check["fix"])
    print("Setup ready." if report["ready"] else "Setup needs attention. Follow the FIX messages above.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesize", action="store_true", help="Actually generate a short line in each voice")
    parser.add_argument("--report", type=Path, help="Optional JSON report location")
    args = parser.parse_args()
    result = check_setup(synthesize=args.synthesize)
    show_report(result)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

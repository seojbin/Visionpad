"""Where speech and audio runtime files live, and the move from the old locations.

Everything generated or downloaded for audio is in one hidden, gitignored folder at the root:
    .audio/voices/   Piper voice models (downloaded by the installer)
    .audio/cache/    generated speech WAVs
    .audio/reports/  voice previews, demo report, speech catalog, game-flow recording, effects reel

Older checkouts kept these in models/piper/, .cache/speech/ and output/audio/. The installer,
the launcher and the server move them here on start, so nobody downloads the voices again.
Only standard-library imports: the installer runs this before the project environment exists.
"""
from pathlib import Path
import shutil

AUDIO_DIR = ".audio"
VOICES_DIR = ".audio/voices"
CACHE_DIR = ".audio/cache"
REPORTS_DIR = ".audio/reports"
LEGACY_DIRS = (("models/piper", VOICES_DIR), (".cache/speech", CACHE_DIR), ("output/audio", REPORTS_DIR))


def voices_dir(root):
    return Path(root) / VOICES_DIR


def cache_dir(root):
    return Path(root) / CACHE_DIR


def reports_dir(root):
    return Path(root) / REPORTS_DIR


def migrate_legacy_audio(root, log=print):
    """Move files from the old locations into .audio/. A file that already exists in .audio/ is kept
    and the old copy is left in place; anything else in the old top folders is left untouched.
    Returns a list of "old -> new (count)" entries for the folders that were moved."""
    root = Path(root)
    moved, kept = [], []
    for old, new in LEGACY_DIRS:
        source, target = root / old, root / new
        if not source.is_dir():
            continue
        count = 0
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            destination = target / path.relative_to(source)
            if destination.exists():
                kept.append(path.relative_to(root).as_posix())
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
            count += 1
        remove_empty(source)
        if count:
            moved.append(f"{old}/ -> {new}/ ({count} file{'s' if count != 1 else ''})")
    leftover = []
    for top in {old.split("/")[0] for old, _ in LEGACY_DIRS}:
        folder = root / top
        if folder.is_dir():
            remove_empty(folder)
        if folder.is_dir():
            leftover += sorted(p.relative_to(root).as_posix() for p in folder.iterdir())
    if moved:
        log("Moved speech files to .audio/: " + "; ".join(moved) + ". Voices are not downloaded again.")
    if kept:
        log("Kept the old copies of files that already exist in .audio/: " + ", ".join(kept))
    if moved and leftover:
        log("Left in place (not speech files): " + ", ".join(sorted(leftover)))
    return moved


def remove_empty(folder):
    """Remove empty folders below and including folder."""
    for path in sorted((p for p in folder.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()

"""One loader for the JSON files in engine/config/. Keys are read exactly as stored."""
import json
from pathlib import Path

from engine.paths import ROOT

FILES = {"game": "game.json", "npc": "npc.json", "speech": "speech.json", "tracking": "tracking.json"}


def config_path(name, root=None):
    """Location of engine/config/<file> under root (the project root by default)."""
    return (Path(root) if root is not None else ROOT) / "engine" / "config" / FILES[name]


def load_config(name, root=None):
    return json.loads(config_path(name, root).read_text(encoding="utf-8"))

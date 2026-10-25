"""Filesystem locations used by the game, tools and tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "engine" / "config"
WEB_DIR = ROOT / "engine" / "web"
GAME_DIR = ROOT / "game"
SAVES_DIR = ROOT / "saves"

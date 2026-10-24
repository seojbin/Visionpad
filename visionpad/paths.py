"""Filesystem locations used by the game, tools and tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
WEB_DIR = ROOT / "web"
SAVES_DIR = ROOT / "saves"

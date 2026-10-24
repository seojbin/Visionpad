"""Every deprecated root module still imports and is the moved module itself."""
import importlib
from pathlib import Path
import re
import unittest

from visionpad.paths import ROOT


class RootAliasTests(unittest.TestCase):
    def test_every_root_alias_imports_the_moved_module(self):
        aliases = {}
        for path in sorted(ROOT.glob("*.py")):
            match = re.search(r"^import (visionpad\.[\w.]+)$", path.read_text(encoding="utf-8"), re.M)
            if match and "Deprecated location" in path.read_text(encoding="utf-8"):
                aliases[path.stem] = match.group(1)
        self.assertGreaterEqual(len(aliases), 13)
        for old, new in aliases.items():
            with self.subTest(alias=old):
                self.assertIs(importlib.import_module(old), importlib.import_module(new))

    def test_game_app_alias_serves_the_same_app(self):
        game_app = importlib.import_module("game_app")
        self.assertIs(game_app.app, importlib.import_module("visionpad.app.main").app)


if __name__ == "__main__":
    unittest.main()

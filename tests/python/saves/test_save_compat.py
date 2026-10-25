"""A save written before the modular refactor must keep loading unchanged."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine.config import load_config
from engine.core.engine import GameEngine
from engine.paths import ROOT
from engine.services.saves import decode

FIXTURE = ROOT / "tests" / "fixtures" / "saves" / "v1_day1_farm_started.json"


class SaveCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.slot = "save_fixture"
        shutil.copyfile(FIXTURE, Path(self.temp.name) / (self.slot + ".json"))
        config = load_config("game")
        self.engine = GameEngine(config, save_dir=self.temp.name)
        self.saved = decode(json.loads(FIXTURE.read_text(encoding="utf-8"))["state"])

    def load(self, slot):
        self.engine.open_load_game()
        return self.engine.load_game(slot)

    def test_fixture_loads_with_the_recorded_progress(self):
        result = self.load(self.slot)
        self.assertEqual(result["tts"], "Game loaded. Day 1. Home.")
        e = self.engine
        self.assertEqual((e.day, e.current_page, e.current_location), (1, "home", "home"))
        self.assertEqual(e.resources["coin"], 52)
        self.assertEqual(e.farm_plots["plot_1"]["seed_id"], "tomato")
        self.assertEqual(e.rowan_stage, "seeds_given")
        self.assertEqual(e.active_buff["source"], "rowan_soup")

    def test_loaded_state_matches_the_fixture_exactly(self):
        self.load(self.slot)
        self.assertEqual(self.engine.snapshot(), self.saved)

    def test_save_and_reload_round_trips(self):
        self.load(self.slot)
        self.engine.save_game()
        saved = sorted(Path(self.temp.name).glob("save_2*.json"))
        self.assertEqual(len(saved), 1)
        resaved = decode(json.loads(saved[0].read_text(encoding="utf-8"))["state"])
        self.assertEqual(resaved, self.saved)
        self.engine.reset()
        self.load(saved[0].stem)
        self.assertEqual(self.engine.snapshot(), self.saved)


if __name__ == "__main__":
    unittest.main()

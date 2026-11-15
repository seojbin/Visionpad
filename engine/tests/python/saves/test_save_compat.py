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

FIXTURE = ROOT / "engine" / "tests" / "fixtures" / "saves" / "v1_day1_farm_started.json"


class SaveCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.slot = "save_fixture"
        shutil.copyfile(FIXTURE, Path(self.temp.name) / (self.slot + ".json"))
        config = load_config("game")
        self.engine = GameEngine(config, save_dir=self.temp.name)
        self.saved = decode(json.loads(FIXTURE.read_text(encoding="utf-8"))["state"])
        self.saved["rowan_daily"] = {}  # New daily requests are absent in old saves.
        # Explicit defaults for the added features; the old fixture itself stays unchanged.
        self.saved.update(flower_seed_stock={'sunflower':0,'orchid':0}, pets=[], pet_next_id=1,
                          pet_selected=None, pet_active=None, pet_adoption=None, pet_motion={}, pet_contact=None, pet_pose_until=None,
                          roulette_goods={'special_feed':0,'plant_nutrient':0,'medicine':0,
                                          'gold_pickaxe':0,'gold_rod':0,'dog_voucher':0,'cat_voucher':0},
                          gold_tools={'pickaxe':False,'fishing_rod':False}, roulette_last_result=None, roulette_queue=[])
        import random
        from game.roulette.sequence import generate
        previous=random.getstate()
        random.setstate(self.saved['random_state'])
        self.saved['roulette_queue']=[generate(self.engine.config) for _ in range(5)]
        self.saved['random_state']=random.getstate()
        random.setstate(previous)
        for key, value in self.engine.snapshot().items():
            if key.startswith("pasture_"): self.saved[key] = value

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

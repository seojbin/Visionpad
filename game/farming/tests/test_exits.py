import tempfile
import unittest

from engine.config import load_config
from engine.core.engine import GameEngine


class FarmExitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.e = GameEngine(load_config("game"), save_dir=self.tmp.name)

    def press(self, x, y):
        self.e.pointer_down(x, y)
        self.e.pointer_up(x, y)

    def test_farm_has_tactile_exits_at_both_ends(self):
        e = self.e
        e.unlocked_plot_count = 6
        e.travel_to("farm")
        e.render()
        for x, label, place in ((1, "Pasture", "pasture"), (58, "Home", "home")):
            e.travel_to("farm")
            e.render()
            self.assertEqual(e.dotpad.matrix[37][x], 1)              # the arrow is raised
            obj = e.find_object(x, 37)
            self.assertEqual(e.get_object_tts(obj), label)
            self.press(x, 37)
            self.assertEqual(e.current_location, place)

    def test_pasture_exit_leads_back_to_the_farm(self):
        e = self.e
        e.travel_to("pasture")
        e.render()
        self.assertEqual(e.dotpad.matrix[26][58], 1)
        self.assertEqual(e.dotpad.matrix[26][57], 1)                 # arrow tip column, fence open here
        self.assertEqual(e.dotpad.matrix[23][57], 0)
        self.press(58, 26)
        self.assertEqual(e.current_location, "farm")


if __name__ == "__main__":
    unittest.main()

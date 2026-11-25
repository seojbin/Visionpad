import tempfile
import unittest

from engine.config import load_config
from engine.core.engine import GameEngine


class CareNavigationTests(unittest.TestCase):
    def test_arrow_keys_travel_from_the_care_page_like_from_home(self):
        """The Care page shows the home scene; Left/Right used to answer "Cannot go left/right"."""
        with tempfile.TemporaryDirectory() as tmp:
            e = GameEngine(load_config("game"), save_dir=tmp)
            for key, place in (("left", "farm"), ("right", "town")):
                e.travel_to("home")
                e.perform_action("pet:care", {})
                self.assertEqual(e.current_page, "care")
                e.navigate_key(key)
                self.assertEqual((e.current_page, e.current_location), (place, place))


if __name__ == "__main__":
    unittest.main()

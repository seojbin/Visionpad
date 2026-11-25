import tempfile
import unittest

from engine.config import load_config
from engine.core.engine import GameEngine
from game.guide.feature import ANIMALS, PER_PAGE, SYMBOL_KEY, TOPICS


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.e = GameEngine(load_config("game"), save_dir=self.tmp.name)

    def ids(self):
        return [o["id"] for o in self.e.get_layout_objects()]

    def test_map_has_a_guide_button_that_opens_the_topics(self):
        e = self.e
        reply = e.toggle_menu("minimap")
        self.assertIn("guide", reply["tts"].lower())
        button = next(o for o in e.get_objects() if o["id"] == "map_guide")
        self.assertEqual(e.find_object(button["x"], button["y"])["id"], "map_guide")
        e.pointer_down(button["x"], button["y"]); e.pointer_up(button["x"], button["y"])
        self.assertEqual(e.current_page, "guide")
        self.assertEqual([o for o in self.ids() if o.startswith("guide_") and o != "guide_back"],
                         [f"guide_{t[0]}" for t in TOPICS])

    def test_topics_speak_and_cost_nothing(self):
        e = self.e
        e.perform_action("guide_open", {})
        before = (e.time_used_cells, dict(e.resources, seeds=dict(e.resources["seeds"])))
        for topic_id, label, short, full in TOPICS:
            if full:
                self.assertEqual(e.perform_action(f"guide_topic:{topic_id}", {})["tts"], full)
        self.assertEqual((e.time_used_cells, e.resources["coin"]), (before[0], before[1]["coin"]))
        self.assertEqual(e.current_page, "guide")

    def test_symbol_key_pages_cover_every_symbol_and_arrows_walk_them(self):
        e = self.e
        e.perform_action("guide_open", {})
        e.perform_action("guide_symbols", {})
        seen = []
        pages = -(-len(SYMBOL_KEY) // PER_PAGE)
        for page in range(pages):
            self.assertEqual(e.current_page, f"guide_symbols_{page + 1}")
            seen += [o["symbol"] for o in e.get_objects() if o["type"] == "guide_symbol"]
            if page < pages - 1:
                e.navigate_key("right")
        self.assertEqual(seen, [s[0] for s in SYMBOL_KEY])
        e.navigate_key("right")                       # past the last page: back to the topics
        self.assertEqual(e.current_page, "guide")
        e.navigate_key("left")                        # leave the guide
        self.assertEqual(e.current_page, e.current_location)

    def test_animal_gallery_shows_each_large_drawing_with_its_description(self):
        """Practice with spoken names before meeting the animals in the game (Theurel et al. 2013)."""
        e = self.e
        reply = e.perform_action("guide_symbol:animal_cat", {})
        self.assertEqual(e.current_page, "guide_animal_cat")
        self.assertIn("pointed ears", reply["tts"])
        visited = [e.current_page]
        for _ in ANIMALS[1:]:
            e.navigate_key("right")
            visited.append(e.current_page)
        self.assertEqual(visited, [f"guide_animal_{a[0]}" for a in ANIMALS])
        e.render()
        self.assertGreater(sum(map(sum, e.dotpad.matrix)), 100)       # the drawing is on the pad
        e.navigate_key("right")
        self.assertTrue(e.current_page.startswith("guide_symbols_"))

    def test_symbol_selection_describes_shape_and_meaning(self):
        e = self.e
        e.perform_action("guide_symbols", {})
        reply = e.perform_action("guide_symbol:seed", {})
        self.assertIn("plus", reply["tts"])
        obj = next(o for o in e.get_objects() if o["id"] == "guide_symbol_seed")
        self.assertEqual(e.get_object_tts(obj), "Seed.")

    def test_guide_adds_nothing_to_saves_and_reopens_its_page(self):
        e = self.e
        fresh = set(e.snapshot())
        e.perform_action("guide_symbols", {})
        e.navigate_key("right")
        snap = e.snapshot()
        self.assertEqual(set(snap), fresh)
        e.restore_snapshot(snap)
        self.assertEqual(e.current_page, "guide_symbols_2")


if __name__ == "__main__":
    unittest.main()

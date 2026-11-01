"""The icon lab lists every pattern table and draws frames exactly as the game's icon code does."""
import unittest

from pydantic import ValidationError

from engine.display.dotpad import DotPad
from engine.display.icons import IconRenderer
from engine.server.routes import icon_lab


class CatalogTests(unittest.TestCase):
    def test_lists_shared_feature_and_config_patterns_once(self):
        entries = icon_lab.catalog()
        groups = {entry["group"] for entry in entries}
        self.assertIn("shared icons", groups)
        self.assertIn("flowers · FLOWER_STAGE_PATTERNS", groups)
        self.assertIn("game.json · recipes", groups)
        shared = [entry for entry in entries if entry["name"] == "coin"]
        self.assertEqual(len(shared), 1, "aliases of IconRenderer.PATTERNS must not repeat it")
        for entry in entries:
            self.assertTrue(icon_lab.is_rows(entry["rows"]), entry)


class RenderTests(unittest.TestCase):
    def test_grid_matches_icon_renderer(self):
        rows = list(IconRenderer.PATTERNS["coin"])
        result = icon_lab.compose(icon_lab.RenderRequest(layout="grid", items=[{"name": "coin", "rows": rows}] * 2))
        self.assertEqual([(s["x"], s["y"]) for s in result["slots"]], [(8, 6), (22, 6)])

        class Host:
            dotpad = DotPad(60, 40)
            draw_icon_pattern = icon_lab.Rendering.draw_icon_pattern
        host = Host()
        icons = IconRenderer(host)
        for slot in result["slots"]:
            obj = {"x": slot["x"], "y": slot["y"], "width": 12, "height": 10}
            icons.frame(obj)
            host.draw_icon_pattern(slot["x"], slot["y"], rows)
        self.assertEqual(result["dots"], host.dotpad.to_list())

    def test_single_without_frame_is_only_the_pattern(self):
        result = icon_lab.compose(icon_lab.RenderRequest(layout="single", frame=False, items=[{"rows": ["1"]}]))
        self.assertEqual(sum(map(sum, result["dots"])), 1)
        self.assertEqual(result["dots"][20][30], 1)
        self.assertEqual((result["time_width"], result["time_height"]), (40, 4))

    def test_rejects_rows_that_are_not_dots(self):
        with self.assertRaises(ValidationError):
            icon_lab.RenderRequest(items=[{"rows": ["0120"]}])
        with self.assertRaises(ValidationError):
            icon_lab.RenderRequest(items=[{"rows": ["1"]}] * 13)


if __name__ == "__main__":
    unittest.main()

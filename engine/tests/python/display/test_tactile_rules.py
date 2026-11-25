"""Tactile design rules (engine/display/tactile.py; README.md "Tactile design rules")."""
import tempfile
import unittest

from engine.config import load_config
from engine.core.engine import GameEngine
from engine.display import tactile
from engine.display.icons import IconRenderer, SYMBOLS, SYMBOL_ALIASES
from engine.tools import tactile_audit


class RulesTests(unittest.TestCase):
    def test_every_audited_page_follows_the_rules(self):
        """Gaps around symbols, outlines instead of large fills, at most five symbols per page."""
        lines = []
        total = tactile_audit.run(out=lines.append)
        self.assertEqual(total, 0, "\n".join(lines))
        self.assertGreaterEqual(sum(1 for line in lines if not line.startswith("    ")), 25)

    def test_symbol_vocabulary_is_small_and_fits_inside_a_frame(self):
        drawn = {name: rows for name, rows in SYMBOLS.items() if rows}
        arrows = {name for name in drawn if name.startswith("arrow_")}
        # One arrow sign (three directions) counts once: 14 symbols, down from 23 names.
        self.assertLessEqual(len(drawn) - len(arrows) + 1, 14)
        for name, rows in drawn.items():
            with self.subTest(symbol=name):
                self.assertLessEqual(len(rows), 5)
                self.assertLessEqual(max(map(len, rows)), 7)
                self.assertLessEqual(tactile.largest_solid_square([[c == "1" for c in r] for r in rows]),
                                     tactile.MAX_SOLID_SIDE)
                # BANA 2010 §3.4.3.11: distinguishable point symbols are at least ~6 mm (3 pins) across.
                self.assertGreaterEqual(max(len(rows), max(map(len, rows))), 3)
        self.assertEqual(len({rows for rows in drawn.values()}), len(drawn), "two symbols share a drawing")

    def test_each_symbol_is_felt_as_one_object(self):
        """A gap inside a symbol (the person's head above its shoulders) made it read as two objects."""
        several_parts = {"coin"}  # ring with a centre dot: the dot is the coin's distinguishing feature
        for name, rows in SYMBOLS.items():
            if not rows or name in several_parts:
                continue
            with self.subTest(symbol=name):
                _, boxes = tactile.components([[c == "1" for c in r] for r in rows])
                self.assertEqual(len(boxes), 1)

    def test_retired_names_resolve_to_their_replacement(self):
        table = IconRenderer.PATTERNS
        for old, new in SYMBOL_ALIASES.items():
            with self.subTest(old=old):
                self.assertIn(old, table)
                self.assertEqual(table[old], SYMBOLS[new])
                self.assertEqual(table.get(old), SYMBOLS[new])
        self.assertNotIn("rowan", list(table))  # iteration lists the canonical vocabulary only
        self.assertIsNone(table.get("no_such_symbol"))

    def test_outline_keeps_edges_and_lowers_the_interior(self):
        rows = ("11111", "11111", "11111", "11111")
        self.assertEqual(tactile.outline_rows(rows), ("11111", "10001", "10001", "11111"))
        self.assertEqual(tactile.outline_rows(("010", "111", "010")), ("010", "101", "010"))

    def test_isolation_detects_a_symbol_touching_a_line(self):
        matrix = [[0] * 20 for _ in range(10)]
        for x in range(20):
            matrix[2][x] = 1                      # a road edge
        for y in range(3, 6):
            for x in range(8, 11):
                matrix[y][x] = 1                  # a 3x3 symbol right under it
        obj = {"id": "sign", "x": 9, "y": 4, "width": 3, "height": 3}
        self.assertTrue(tactile.isolation_problems(matrix, obj))
        matrix[2] = [0] * 20
        self.assertEqual(tactile.isolation_problems(matrix, obj), [])

    def test_trace_finds_a_symbol_touching_its_own_frame(self):
        """The General goods bag (7 pins) touched its 8-pin-wide counter; the object box contained both,
        so only tracing which drawing raised each pin can see it."""
        with tempfile.TemporaryDirectory() as tmp:
            e = GameEngine(load_config("game"), save_dir=tmp)
            with tactile.SymbolTrace(e) as trace:
                e.dotpad.draw_box(10, 10, 8, 6)                       # frame x 6..14
                e.draw_icon_pattern(10, 10, SYMBOLS["bag"])           # bag x 7..13: touches the frame
            self.assertTrue(trace.contacts(e.dotpad.to_list()))
            e.dotpad.clear()
            with tactile.SymbolTrace(e) as trace:
                e.dotpad.draw_box(10, 10, 10, 8)                      # frame x 5..15: one pin of space
                e.draw_icon_pattern(10, 10, SYMBOLS["bag"])
            self.assertEqual(trace.contacts(e.dotpad.to_list()), [])
            # The trace removes its wrappers afterwards.
            self.assertNotIn("draw_icon_pattern", vars(e))
            self.assertNotIn("set_dot", vars(e.dotpad))

    def test_fur_texture_has_no_isolated_pins(self):
        """Single raised pins inside a body read as eyes or braille (Bhatnagar et al. 2023)."""
        from game.pets.shapes import DETAIL, drawing
        for species, poses in DETAIL.items():
            for pose in poses:
                with self.subTest(species=species, pose=pose):
                    rows = drawing(species, pose)
                    matrix = [[c == "1" for c in r] for r in rows]
                    _, boxes = tactile.components(matrix)
                    singles = [b for b in boxes if b[0] == b[2] and b[1] == b[3]]
                    self.assertEqual(singles, [])

    def test_shop_counters_show_their_own_symbols(self):
        """The Tools counter and button showed the General goods bag before."""
        with tempfile.TemporaryDirectory() as tmp:
            e = GameEngine(load_config("game"), save_dir=tmp)
            e.open_shop()
            tools = next(o for o in e.get_objects() if o["id"] == "shop_tools_choice")
            buy = next(o for o in e.get_objects() if o["id"] == "shop_buy_choice")
            self.assertNotEqual(e.icons.spec(tools).symbol, e.icons.spec(buy).symbol)
            self.assertEqual(IconRenderer.PATTERNS[e.icons.spec(tools).symbol], SYMBOLS["tool"])


if __name__ == "__main__":
    unittest.main()

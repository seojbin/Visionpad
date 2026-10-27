import tempfile
import unittest
from engine.config import load_config
from engine.core.engine import GameEngine


class InventoryNavigationTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.e = GameEngine(load_config('game'), save_dir=folder.name)
        self.e.travel_to('town')
        self.e.toggle_menu('inventory')

    def test_first_page_left_returns_to_region(self):
        self.e.navigate_key('left')
        self.assertEqual(self.e.current_page, 'town')

    def test_last_page_right_returns_to_region(self):
        e = self.e
        e.get_inventory_objects()
        e.inventory_page = e.inventory_page_count - 1
        e.navigate_key('right')
        self.assertEqual(e.current_page, 'town')

    def test_available_pages_still_turn(self):
        e = self.e
        self.assertGreater(e.inventory_page_count, 1)
        e.navigate_key('right')
        self.assertEqual(e.current_page, 'inventory')
        self.assertEqual(e.inventory_page, 1)
        e.navigate_key('left')
        self.assertEqual(e.current_page, 'inventory')
        self.assertEqual(e.inventory_page, 0)

    def test_single_page_both_arrows_return(self):
        e = self.e
        for direction in ('left', 'right'):
            with self.subTest(direction=direction):
                for key, value in e.resources.items():
                    if isinstance(value, dict):
                        for item in value: value[item] = 0
                    elif isinstance(value, (int, float)): e.resources[key] = 0
                e.flower_seeds = 0
                e.open_inventory()
                e.get_inventory_objects()
                self.assertEqual(e.inventory_page_count, 1)
                e.navigate_key(direction)
                self.assertEqual(e.current_page, 'town')

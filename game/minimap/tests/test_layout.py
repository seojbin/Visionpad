import tempfile
import unittest
from engine.config import load_config
from engine.core.engine import GameEngine


class MapLayoutTests(unittest.TestCase):
    def test_home_centred_and_nodes_fit_with_topology_preserved(self):
        with tempfile.TemporaryDirectory() as saves:
            engine = GameEngine(load_config('game'), save_dir=saves)
            engine.set_page('minimap')
            objects = engine.get_objects()
            nodes = {o['id']: o for o in objects if o['type'] == 'node'}
            home = nodes['map_home']
            self.assertEqual((home['x'], home['y']), (30, 20))
            self.assertLess(nodes['map_farm']['x'], home['x'])
            self.assertGreater(nodes['map_town']['x'], home['x'])
            self.assertLess(nodes['map_mine']['y'], home['y'])
            self.assertGreater(nodes['map_fishing']['y'], home['y'])
            for node in nodes.values():
                self.assertTrue(3 <= node['x'] < engine.dotpad.width - 3)
                self.assertTrue(3 <= node['y'] < engine.dotpad.height - 3)
                self.assertTrue(node['action'].startswith('travel:'))
            for route in (o for o in objects if o['type'] == 'route'):
                self.assertTrue(route['x1'] == route['x2'] or route['y1'] == route['y2'])

    def test_frames_have_exact_bounds_and_clear_crossing_paths(self):
        with tempfile.TemporaryDirectory() as saves:
            engine=GameEngine(load_config('game'),save_dir=saves)
            engine.set_page('minimap');engine.render()
            nodes=[o for o in engine.get_objects() if o['type']=='node']
            for node in nodes:
                for dy in range(-3,4):
                    for dx in range(-3,4):
                        expected=int(node['current'] or abs(dx)==3 or abs(dy)==3)
                        self.assertEqual(engine.dotpad.matrix[node['y']+dy][node['x']+dx],expected,(node['id'],dx,dy))

import time
from unittest.mock import patch
import tempfile
import unittest
from engine.config import load_config
from engine.core.engine import GameEngine

class EggTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.e=GameEngine(load_config('game'),save_dir=self.tmp.name)
    def test_two_stage_recipe_and_consumption(self):
        e=self.e;e.pasture_goods['egg']=1;e.resources['crops']['carrot']=1
        e.perform_action('select_recipe:fried_egg',{})
        self.assertEqual(e.current_page,'ingredient_select')
        e.perform_action('toggle_ingredient:egg',{});e.perform_action('toggle_ingredient:carrot',{})
        self.assertEqual(e.current_page,'cooking')
        self.assertEqual(e.get_cooking_gesture()['kind'],'crack')
        self.assertEqual(e.pasture_goods['egg'],1)
        for stage in range(2):
            samples=list(e.cooking_path_samples)
            for x,y in samples:e.pointer_move(x,y)
            with patch("time.monotonic", return_value=time.monotonic()+2): e.visual_tick()
        self.assertEqual(e.resources['foods']['fried_egg'],1)
        self.assertEqual(e.pasture_goods['egg'],0);self.assertEqual(e.resources['crops']['carrot'],0)
    def test_discount_once_not_expiring_and_failure_preserves(self):
        e=self.e;e.resources['foods']['fried_egg']=1;e.use_food('fried_egg');e.tick_buff(100)
        cfg=e.config['research']['seed_return'];raw=cfg['costs'][0]
        self.assertEqual(e.research_price(raw),int(raw*.8))
        e.resources['coin']=0;e.perform_action('research:seed_return',{})
        self.assertEqual(e.active_buff['kind'],'research_discount')
        e.resources['coin']=1000;e.resources['copper']=100;e.perform_action('research:seed_return',{})
        self.assertEqual(e.resources['coin'],1000-int(raw*.8));self.assertNotEqual(e.active_buff['kind'],'research_discount')
    def test_discount_survives_save(self):
        e=self.e;e.resources['foods']['fried_egg']=1;e.use_food('fried_egg');snap=e.snapshot()
        e.active_buff={};e.restore_snapshot(snap);self.assertEqual(e.research_price(100),80)

if __name__=='__main__':unittest.main()

import tempfile
import unittest
from unittest.mock import patch
from engine.config import load_config
from engine.core.engine import GameEngine

class PurchaseEscapeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.e=GameEngine(load_config('game'),save_dir=self.temp.name)
        self.e.resources['coin']=2000
    def buy(self,kind):self.e.buy_shop_item('animal',kind)
    def action(self,action):return self.e.perform_action('animal:'+action,{})
    def test_empty_start_and_unique_purchase(self):
        e=self.e;self.assertFalse(any(a['owned'] for a in e.pasture_animals.values()))
        self.buy('chicken');self.assertEqual(e.resources['coin'],1900);self.buy('chicken')
        self.assertEqual(e.resources['coin'],1900);self.assertTrue(e.pasture_animals['chicken']['owned'])
        self.buy('sheep');self.assertEqual(e.resources['coin'],1650)
    def test_random_movement_facing_pause_and_save(self):
        e=self.e;self.buy('chicken');self.buy('sheep');e.travel_to('pasture')
        a=e.pasture_animals['chicken']
        with patch('game.pasture.feature.time.monotonic') as clock, patch('game.pasture.feature.random.uniform',return_value=4) as random_interval:
            e.pasture_move_at=None;clock.return_value=100;e.get_state();step=a['step']
            clock.return_value=103.9;e.get_state();self.assertEqual(a['step'],step)
            clock.return_value=104;e.get_state();self.assertEqual(a['step'],(step+1)%6)
            self.assertFalse(a['facing_left'])
            clock.return_value=116;data=e.get_state();self.assertTrue(a['facing_left'])
            self.assertTrue(data['pasture']['animals']['chicken']['facing_left'])
            self.assertTrue(all(call.args==(3,5) for call in random_interval.call_args_list))
            e.paused=True;step=a['step'];clock.return_value=200;e.get_state();self.assertEqual(a['step'],step)
            e.paused=False;e.get_state();self.assertEqual(a['step'],step)
            snapshot=e.snapshot();e.restore_snapshot(snapshot)
            self.assertTrue(e.pasture_animals['chicken']['facing_left'])

    def test_insufficient_gold_no_animal(self):
        self.e.resources['coin']=0;self.buy('sheep');self.assertFalse(self.e.pasture_animals['sheep']['owned'])
    def test_escape_formula_all_three_levels(self):
        e=self.e
        for level in range(3):
            for excess,roll,escaped in [(0,0,False),(1,.09,True),(1,.11,False),(2,.19,True)]:
                with self.subTest(level=level,excess=excess,roll=roll):
                    a=e.pasture_animals['chicken'];a.update(owned=True,friendship=level*100,last_feed_day=1,ready=False,remaining=2)
                    e.day=level+1+excess
                    with patch('game.pasture.feature.random.random',return_value=roll):e.registry.run('end_of_day')
                    self.assertEqual(not a['owned'],escaped)
    def test_escape_cleanup_and_repurchase(self):
        e=self.e;self.buy('sheep');a=e.pasture_animals['sheep'];a.update(ready=True,quantity=2,ready_day=2)
        e.pasture_sheared=[0,1];e.day=4
        with patch('game.pasture.feature.random.random',return_value=0):notes=e.registry.run('end_of_day')
        self.assertFalse(a['owned']);self.assertFalse(a['ready']);self.assertEqual(e.pasture_sheared,[])
        self.assertIn('escaped',' '.join(notes));self.buy('sheep');self.assertTrue(a['owned']);self.assertIn(a['remaining'],(2,3,4))
    def test_shop_partition_and_order(self):
        e=self.e;e.open_shop()
        ids=[o['id'] for o in e.get_objects() if o['type'] in ('shop_choice','calendar_button')]
        self.assertEqual(ids,['shop_sell_choice','shop_buy_choice','shop_tools_choice','shop_calendar'])
        e.perform_action('shop_mode:buy',{});kinds={o.get('shop_kind') for o in e.get_objects()}
        self.assertIn('animal_feed',kinds);self.assertTrue(kinds.isdisjoint({'animal','pickaxe','fishing_rod','flower_seed'}))
        e.perform_action('shop_mode:tools',{});kinds={o.get('shop_kind') for o in e.get_objects()}
        self.assertTrue({'animal','pickaxe','fishing_rod','flower_seed'}<=kinds);self.assertNotIn('animal_feed',kinds)
        self.assertEqual(e.lower_panel_state()['label'],'buy')
        e.navigate_key('left');self.assertEqual(e.current_page,'shop_choice')
    def test_collection_button_and_three_ticks(self):
        e=self.e;self.buy('chicken');e.travel_to('pasture');self.action('open:chicken')
        self.assertIn('animal_gather',[o['id'] for o in e.get_objects()])
        self.action('gather');self.assertEqual(e.current_page,'animal_detail')
        e.pasture_animals['chicken'].update(ready=True,quantity=1,ready_day=e.day)
        self.action('gather');self.assertEqual(e.current_page,'egg_collect');self.assertEqual(e.pasture_goods['egg'],0)
        e.pointer_down(30,35);self.assertEqual(e.pasture_goods['egg'],1);self.assertEqual(e.time_used_cells,3)
        e.pointer_up(30,35);self.assertEqual(e.time_used_cells,3)
    def test_sheep_body_opens_shearing_and_partial_save(self):
        e=self.e;self.buy('sheep');e.travel_to('pasture');self.action('open:sheep')
        self.assertIn('animal_shear',[o['id'] for o in e.get_objects()])
        e.pasture_animals['sheep'].update(ready=True,quantity=1,ready_day=e.day)
        e.pointer_down(30,22);e.pointer_up(30,22);self.assertEqual(e.current_page,'shearing')
        e.pointer_move(4,3);saved=list(e.pasture_sheared);snap=e.snapshot();e.restore_snapshot(snap);self.assertEqual(saved,e.pasture_sheared)
        for y in range(3,38,5):
            for x in range(4,57,5):
                if e.current_page=='shearing':e.pointer_move(x,y)
        self.assertEqual(e.pasture_goods['wool'],2);self.assertEqual(e.time_used_cells,3)
    def test_collection_reaches_night(self):
        e=self.e;self.buy('chicken');e.travel_to('pasture');self.action('open:chicken')
        e.pasture_animals['chicken'].update(ready=True,quantity=1,ready_day=e.day);e.time_used_cells=19
        self.action('gather');self.action('collect');self.assertTrue(e.day_ended);self.assertEqual(e.current_page,'home');self.assertEqual(e.pasture_goods['egg'],1)

if __name__=='__main__':unittest.main()

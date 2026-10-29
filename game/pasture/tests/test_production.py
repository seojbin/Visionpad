import tempfile
import unittest
from unittest.mock import patch
from engine.config import load_config
from engine.core.engine import GameEngine

class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.e=GameEngine(load_config('game'),save_dir=self.tmp.name);self.e.resources['coin']=2000
        for k in ('chicken','sheep'):self.e.buy_shop_item('animal',k)
        self.e.travel_to('pasture')
    def day(self):
        e=self.e;e.registry.run('end_of_day');e.day+=1;e.registry.run('start_of_day')
    def test_egg_accumulates_to_three_wool_stays_ready_and_hidden(self):
        e=self.e
        with patch('game.pasture.feature.random.random',return_value=.19),patch('game.pasture.feature.random.randint',return_value=5):
            for a in e.pasture_animals.values():a.update(remaining=1,last_feed_day=100)
            self.day()
            self.assertEqual(e.pasture_animals['chicken']['quantity'],2);self.assertEqual(e.pasture_animals['sheep']['quantity'],5)
            for _ in range(6):self.day()
            self.assertEqual(e.pasture_animals['chicken']['quantity'],3);self.assertEqual(e.pasture_animals['sheep']['quantity'],5)
        for k in ('chicken','sheep'):
            reply=e.perform_action('animal:open:'+k,{})
            self.assertNotIn('quantity',e.get_state()['pasture']['animals'][k])
            self.assertNotIn('ready,',str(reply))
        e.perform_action('animal:open:chicken',{});reply=e.perform_action('animal:collect',{})
        self.assertIn('Collected 3 eggs.',str(reply));self.assertEqual(e.pasture_goods['egg'],3)
    def test_daily_ranges_and_egg_chance_boundary(self):
        e=self.e
        for wait in (1,2):
            with patch('game.pasture.feature.random.choices',return_value=[wait]) as choose:
                e.pasture_animals['chicken'].update(ready=True,quantity=1);e.perform_action('animal:open:chicken',{});e.perform_action('animal:collect',{})
                self.assertEqual(e.pasture_animals['chicken']['remaining'],wait)
                self.assertEqual(choose.call_args.args[0],[1,2]);self.assertEqual(choose.call_args.kwargs['weights'],[80,20])
        for roll,quantity in [(.199,2),(.2,1),(.99,1)]:
            e.pasture_animals['chicken'].update(ready=False,remaining=1,last_feed_day=100)
            with patch('game.pasture.feature.random.random',return_value=roll):self.day()
            self.assertEqual(e.pasture_animals['chicken']['quantity'],quantity)
    def test_feed_sound_only_on_success(self):
        e=self.e;e.perform_action('animal:open:chicken',{})
        self.assertNotIn('feed',str(e.perform_action('animal:feed',{}).get('sound_events',[])))
        e.pasture_goods['animal_feed']=2;reply=e.perform_action('animal:feed',{})
        self.assertIn({'kind':'one_shot','sound':'feed'},reply['sound_events'])
        self.assertNotIn('feed',str(e.perform_action('animal:feed',{}).get('sound_events',[])))
    def test_round_dot_eraser_and_save_migration(self):
        e=self.e;e.pasture_animals['sheep'].update(ready=True,quantity=4);e.perform_action('animal:open:sheep',{});e.perform_action('animal:shear',{})
        e.config['pasture']['shear_radius']=2
        e.pointer_move(20,20);erased=set(e.pasture_sheared)
        self.assertIn(20*60+20,erased);self.assertNotIn(22*60+22,erased)
        self.assertEqual(e.dotpad.matrix[20][20],0);self.assertEqual(e.dotpad.matrix[22][22],1)
        snap=e.snapshot();e.restore_snapshot(snap);self.assertEqual(set(e.pasture_sheared),erased)
        snap['pasture_animals']['sheep'].pop('shear_format');snap['pasture_sheared']=[0]
        e.restore_snapshot(snap);self.assertIn(3*60+4,e.pasture_sheared)
        self.assertEqual(e.pasture_animals['sheep']['shear_format'],'dots_v1')
    def test_prices(self):
        c=self.e.config['pasture']['animals'];self.assertEqual(c['chicken']['price'],70);self.assertEqual(c['sheep']['price'],100)

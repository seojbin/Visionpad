from unittest.mock import patch
import copy
import tempfile
import unittest
from engine.config import load_config
from engine.core.engine import GameEngine

class PastureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.e=GameEngine(load_config('game'),save_dir=self.tmp.name)
        for k,days in [('chicken',2),('sheep',3)]:
            self.e.config['pasture']['animals'][k].update(wait_days=[days],wait_weights=[1])
        self.e.resources['coin']=1000
        self.e.buy_shop_item('animal','chicken');self.e.buy_shop_item('animal','sheep')
        self.e.travel_to('pasture')
        self.random=patch('game.pasture.feature.random.random',return_value=1);self.random.start();self.addCleanup(self.random.stop)
    def act(self,action):return self.e.perform_action('animal:'+action,{})
    def pet(self):
        with patch('game.pasture.feature.time.monotonic') as clock:
            for i in range(33):
                clock.return_value=100+i*.1
                self.e.pointer_move(28+i%2,22)
    def day(self):
        self.e.registry.run('end_of_day'); self.e.day+=1; self.e.registry.run('start_of_day')
    def test_navigation_and_map(self):
        e=self.e;self.assertEqual(e.current_location,'pasture')
        e.travel_to('farm');self.assertIn('travel:pasture',[o.get('action') for o in e.get_layout_objects()])
        e.set_page('minimap');nodes=[o for o in e.get_objects() if o['type']=='node']
        self.assertTrue(any(o.get('location')=='pasture' for o in nodes))
        self.assertTrue(all(3<=o['x']<=56 and 3<=o['y']<=36 for o in nodes))
    def test_production_without_feed_and_keeps_ready(self):
        self.day();self.assertFalse(self.e.pasture_animals['chicken']['ready'])
        self.day();self.assertTrue(self.e.pasture_animals['chicken']['ready']);self.assertFalse(self.e.pasture_animals['sheep']['ready'])
        self.day();self.assertTrue(self.e.pasture_animals['sheep']['ready'])
        for _ in range(5):self.day()
        self.assertTrue(self.e.pasture_animals['chicken']['ready'])
    def test_feed_deferred_and_once(self):
        e=self.e;e.pasture_goods['animal_feed']=3;self.act('open:chicken');self.day()
        self.act('feed');a=e.pasture_animals['chicken'];self.assertEqual(a['remaining'],1);self.assertTrue(a['next_boost'])
        self.act('feed');self.assertEqual(e.pasture_goods['animal_feed'],2)
        self.day();self.act('gather');self.act('collect');self.assertEqual(a['remaining'],2);self.assertFalse(a['next_boost'])
    def test_feed_shortens_current_cycle(self):
        self.act('open:sheep');self.e.pasture_goods['animal_feed']=1;self.act('feed')
        self.assertEqual(self.e.pasture_animals['sheep']['remaining'],2)
    def test_pet_and_affection_production(self):
        self.act('open:chicken');self.pet();self.pet();a=self.e.pasture_animals['chicken'];self.assertEqual(a['friendship'],10)
        a['friendship']=200;self.day();self.day();self.assertEqual(a['quantity'],1)
        self.act('gather');self.act('collect');self.assertEqual(self.e.pasture_goods['egg'],1);self.assertEqual(a['friendship'],230)
    def test_neglect_boundaries(self):
        a=self.e.pasture_animals['chicken'];a['friendship']=200
        for _ in range(4):self.day()
        self.assertEqual(a['friendship'],200)
        self.day();self.assertEqual(a['friendship'],150)
    def test_egg_pointer_collection_once(self):
        self.day();self.day();self.act('open:chicken');self.act('gather');e=self.e
        e.pointer_down(30,35);e.pointer_up(30,35)
        self.assertEqual(e.pasture_goods['egg'],1)
        e.pointer_down(30,35);e.pointer_up(30,35);self.assertEqual(e.pasture_goods['egg'],1)
    def test_shear_hover_complete_once(self):
        for _ in range(3):self.day()
        self.act('open:sheep');self.act('shear');e=self.e
        self.assertEqual(e.current_page,'shearing')
        e.pointer_move(4,3);self.assertGreater(len(e.pasture_sheared),1)
        for y in range(3,38,5):
            for x in range(4,57,5):e.pointer_move(x,y)
        self.assertTrue(2<=e.pasture_goods['wool']<=5);self.assertEqual(e.current_page,'animal_detail')
    def test_save_restore_and_legacy(self):
        e=self.e;self.act('open:chicken');self.pet();e.pasture_goods['egg']=3
        snap=e.snapshot(); e.pasture_goods['egg']=0;e.restore_snapshot(snap)
        self.assertEqual(e.pasture_goods['egg'],3);self.assertEqual(e.pasture_animals['chicken']['friendship'],10)
        old={k:v for k,v in snap.items() if not k.startswith('pasture_')};old['day']=20
        e.restore_snapshot(old);self.assertEqual(e.pasture_animals['chicken']['last_feed_day'],20)
    def test_feed_purchase_and_product_sale(self):
        e=self.e;e.resources['coin']=200
        e.buy_shop_item('animal_feed','animal_feed')
        self.assertEqual(e.pasture_goods['animal_feed'],1);self.assertEqual(e.resources['coin'],170)
        e.pasture_goods['egg']=1;e.sell_shop_item('animal_product','egg')
        self.assertEqual(e.pasture_goods['egg'],0);self.assertEqual(e.resources['coin'],240)

    def test_hidden_pet_requires_motion_inside_and_awards_once(self):
        self.act('open:chicken');e=self.e;a=e.pasture_animals['chicken']
        self.assertNotIn('animal:pet',[o.get('action') for o in e.get_objects()])
        self.assertEqual([o['action'] for o in e.get_objects() if o['type']=='animal_care'],['animal:feed','animal:gather'])
        with patch('game.pasture.feature.time.monotonic') as clock:
            for i in range(40):
                clock.return_value=i*.1;e.pointer_move(28,22)
        self.assertEqual(a['friendship'],0)
        with patch('game.pasture.feature.time.monotonic') as clock:
            for i in range(40):
                clock.return_value=10+i*.1;e.pointer_move(5+i%2,6)
        self.assertEqual(a['friendship'],0)
        self.pet();self.assertEqual(a['friendship'],10)
        self.pet();self.assertEqual(a['friendship'],10)
        self.assertNotIn('progress',str(e.get_state()['pasture']))
        e.day+=1;self.act('open:chicken');self.pet();self.assertEqual(a['friendship'],20)

    def test_daily_pet_main_call_once_per_animal_and_day(self):
        e=self.e
        for kind in ('chicken','sheep'):
            self.act('open:'+kind)
            with patch('game.pasture.feature.time.monotonic') as clock:
                events=[]
                for i in range(81):
                    clock.return_value=100+i*.1
                    result=e.pointer_move(28+i%2,22)
                    events.extend(result.get('sound_events',[]))
                self.assertEqual(events,[{'kind':'one_shot','sound':kind+'_main'}])
            self.assertEqual(e.pasture_animals[kind]['friendship'],10)
            self.act('open:'+kind)
            with patch('game.pasture.feature.time.monotonic') as clock:
                events=[]
                for i in range(41):
                    clock.return_value=200+i*.1
                    events.extend(e.pointer_move(28+i%2,22).get('sound_events',[]))
                self.assertEqual(events,[])
        e.day+=1;self.act('open:chicken')
        with patch('game.pasture.feature.time.monotonic') as clock:
            events=[]
            for i in range(41):
                clock.return_value=300+i*.1
                events.extend(e.pointer_move(28+i%2,22).get('sound_events',[]))
            self.assertEqual(events,[{'kind':'one_shot','sound':'chicken_main'}])

    def test_pet_does_not_count_pause_or_long_gaps(self):
        self.act('open:sheep');e=self.e;a=e.pasture_animals['sheep']
        e.paused=True;self.pet();self.assertEqual(a['friendship'],0)
        e.paused=False
        with patch('game.pasture.feature.time.monotonic') as clock:
            for i in range(10):
                clock.return_value=200+i*2;e.pointer_move(28+i%2,22)
        self.assertEqual(a['friendship'],0)
        self.pet();self.assertEqual(a['friendship'],10)

    def test_short_state_hides_numeric_affection(self):
        data=self.e.get_state()['pasture'];self.assertNotIn('friendship',str(data));self.assertNotIn('remaining',str(data))

if __name__=='__main__':unittest.main()

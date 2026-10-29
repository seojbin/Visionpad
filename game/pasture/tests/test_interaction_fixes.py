import tempfile
import unittest
from unittest.mock import patch
from engine.config import load_config
from engine.core.engine import GameEngine

class InteractionFixes(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.e=GameEngine(load_config('game'),save_dir=self.tmp.name)
        self.e.resources['coin']=2000
        for k in ('chicken','sheep'):self.e.buy_shop_item('animal',k)
    def test_shared_feed_migration_and_both_animals(self):
        e=self.e;snap=e.snapshot();snap['pasture_goods']={'egg':2,'wool':1,'chicken_feed':2,'sheep_feed':3}
        e.restore_snapshot(snap);self.assertEqual(e.pasture_goods,{'egg':2,'wool':1,'animal_feed':5})
        e.restore_snapshot(e.snapshot());self.assertEqual(e.pasture_goods['animal_feed'],5)
        e.travel_to('pasture')
        for k in ('chicken','sheep'):
            e.perform_action('animal:open:'+k,{});e.perform_action('animal:feed',{})
        self.assertEqual(e.pasture_goods['animal_feed'],3)
        e.open_shop();e.perform_action('shop_mode:buy',{})
        rows=[o for o in e.get_objects() if o.get('shop_kind')=='animal_feed']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['label'],'Animal feed')
    def test_egg_direct_click_and_raised_texture(self):
        e=self.e;e.travel_to('pasture');e.perform_action('animal:open:chicken',{})
        e.pasture_animals['chicken'].update(ready=True,quantity=1,ready_day=e.day);e.render()
        self.assertEqual(e.find_object(30,35)['action'],'animal:collect')
        region=[e.dotpad.matrix[y][x] for y in range(33,38) for x in range(26,35)]
        self.assertGreater(sum(region),len(region)//2);self.assertIn(0,region)
        self.assertEqual(e.dotpad.matrix[35][24],0)
        e.pointer_down(30,35);self.assertEqual(e.pasture_goods['egg'],1);self.assertEqual(e.time_used_cells,3)
        e.pointer_up(30,35);self.assertEqual(e.pasture_goods['egg'],1)
    def test_lower_counters_voice_hitboxes_actions(self):
        e=self.e
        for oid,mode in [('shop_scene_sell','sell'),('shop_scene_buy','buy'),('shop_scene_tools','tools')]:
            e.open_shop();obj=next(o for o in e.get_objects() if o['id']==oid)
            self.assertEqual(e.find_object(obj['x'],obj['y'])['id'],oid)
            self.assertIn({'sell':'Sell','buy':'General goods','tools':'Tools'}[mode],e.get_object_tts(obj))
            e.pointer_down(obj['x'],obj['y']);e.pointer_up(obj['x'],obj['y'])
            self.assertEqual(e.current_page,'shop_'+mode)
    def test_icon_padding_and_shop_animals(self):
        e=self.e;e.travel_to('pasture')
        def check(obj):
            e.dotpad.clear();e.icons.draw(obj);cx,cy=obj['x'],obj['y']
            for dx in range(-4,5):
                for dy in (-3,3):self.assertEqual(e.dotpad.matrix[cy+dy][cx+dx],0)
            for dy in range(-3,4):
                for dx in (-4,4):self.assertEqual(e.dotpad.matrix[cy+dy][cx+dx],0)
            return [[e.dotpad.matrix[cy+dy][cx+dx] for dx in range(-3,4)] for dy in range(-2,3)]
        icons={o['animal']:check(o) for o in e.get_objects() if o['type']=='animal_icon'}
        e.open_shop();e.perform_action('shop_mode:tools',{})
        for o in e.get_objects():
            if o.get('shop_kind')=='animal':self.assertEqual(check(o),icons[o['item_id']])
        e.travel_to('pasture');e.perform_action('animal:open:sheep',{})
        for o in e.get_objects():
            if o['type']=='animal_care':check(o)
        feed=next(o for o in e.get_objects() if o['id']=='animal_feed')
        self.assertEqual(e.icons.spec(feed).pattern,e.icons.PATTERNS['tool'])
    def test_escape_arrival_survives_save_until_repurchase(self):
        e=self.e;e.day=8
        with patch('game.pasture.feature.random.random',return_value=0):e.registry.run('end_of_day')
        e.restore_snapshot(e.snapshot());reply=e.travel_to('pasture')
        self.assertIn('Chicken and Sheep escaped.',str(reply))
        e.buy_shop_item('animal','chicken');e.travel_to('farm');reply=e.travel_to('pasture')
        self.assertIn('Sheep escaped.',str(reply));self.assertNotIn('Chicken and Sheep escaped.',str(reply))
    def test_detail_breathing_one_dot(self):
        e=self.e;e.travel_to('pasture');e.perform_action('animal:open:sheep',{})
        with patch('game.pasture.feature.time.monotonic') as clock:
            clock.return_value=300;s0=e.get_state();m0=[r[:] for r in e.dotpad.matrix]
            clock.return_value=301.6;s1=e.get_state();m1=e.dotpad.matrix
        self.assertEqual(s0['pasture']['breath_offset']-s1['pasture']['breath_offset'],1)
        for y in range(13,30):self.assertEqual(m0[y][14:46],m1[y-1][14:46])

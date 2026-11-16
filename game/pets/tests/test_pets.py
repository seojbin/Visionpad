import tempfile
import unittest
from unittest.mock import patch
from engine.core.engine import GameEngine
from engine.config import load_config

class PetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.e=GameEngine(load_config('game'),save_dir=self.tmp.name)
        self.p=self.e.registry.features['pets'];self.r=self.e.registry.features['roulette'];self.e.resources['coin']=10000
    def use(self,key):
        self.e.roulette_goods[key]+=1
        result=self.e.perform_action('prize:'+key,{})
        if self.e.current_page=='pet_names':return self.e.perform_action(next(o['action'] for o in self.e.get_objects() if o.get('action','').startswith('pet:name:')), {})
        return result
    def test_adoption_pitch_limit_and_save(self):
        for _ in range(12):self.use('dog_voucher')
        self.assertEqual(len(self.e.pets),12);self.assertEqual(len({a['pitch'] for a in self.e.pets}),6)
        self.use('cat_voucher');self.assertEqual(self.e.roulette_goods['cat_voucher'],1)
        snap=self.e.snapshot();other=GameEngine(load_config('game'),save_dir=self.tmp.name);other.restore_snapshot(snap)
        self.assertEqual(other.pets,self.e.pets)
    def test_daily_care_sickness_and_release(self):
        self.use('cat_voucher');self.e.perform_action('pet:open:1',{})
        self.e.pasture_goods['animal_feed']=3;self.e.day+=1
        self.e.perform_action('pet:feed',{});self.e.perform_action('pet:feed',{})
        self.assertEqual(self.e.pasture_goods['animal_feed'],2)
        self.e.day+=4;self.p.advance();self.assertTrue(self.e.pets[0]['sick'])
        self.e.roulette_goods['medicine']=1;self.e.perform_action('pet:medicine',{});self.assertFalse(self.e.pets[0]['sick'])
        self.e.perform_action('pet:release',{});self.assertEqual(len(self.e.pets),1)
        self.e.perform_action('pet:release_confirm',{});self.assertEqual(self.e.pets,[])
    def test_home_menu_and_plant_selection(self):
        self.assertEqual(sum(o.get('action')=='pet:care' for o in self.e.get_objects()),1)
        f=self.e.registry.features['flowers'];f.add_seed('orchid',1)
        self.e.perform_action('flower:open',{});self.e.perform_action('flower:choose',{})
        self.assertEqual(len([o for o in self.e.get_objects() if o.get('seed_id')]),3)
        self.e.perform_action('flower:plant:orchid',{});self.assertEqual(self.e.houseplant['species'],'orchid');self.assertEqual(f.seed_count('orchid'),0)
    def test_gifts_and_buff_do_not_overwrite_food(self):
        self.use('cat_voucher');a=self.e.pets[0];a['affection']=200
        with patch('game.pets.feature.random.random',return_value=0):self.p.advance()
        self.assertIsNotNone(a['gift']);self.assertEqual(self.p.harvest_bonus(),1)
        self.e.perform_action('pet:open:1',{});g=dict(a['gift']);self.e.perform_action('pet:gift',{});self.e.perform_action('pet:gift',{})
        self.assertEqual(self.e.resources[g['resource']][g['item']],1)
    def test_named_adoption_slots_and_active_selection(self):
        self.e.roulette_goods['cat_voucher']=1
        self.e.perform_action('prize:cat_voucher',{})
        self.assertEqual(len(self.e.pets),0)
        names=[o for o in self.e.get_objects() if o.get('action','').startswith('pet:name:')]
        self.assertEqual(len(names),12)
        self.e.perform_action('pet:name:2',{})
        self.assertEqual(self.e.pets[0]['name'],'Cat Cleo');self.assertEqual(self.e.roulette_goods['cat_voucher'],0)
        self.use('dog_voucher');self.e.perform_action('pet:open:1',{})
        self.assertEqual(self.e.pet_active,1)
        self.e.perform_action('pet:list',{})
        self.assertEqual(len([o for o in self.e.get_objects() if o['type'] in ('pet_icon','pet_button')]),2)
        before=self.e.snapshot();self.e.restore_snapshot(before);self.assertEqual(self.e.pet_active,1)
    def test_four_actions_give_medicine_guard_and_direct_gift(self):
        self.use('cat_voucher');a=self.p.selected()
        actions=[o['action'] for o in self.e.get_objects() if o['type']=='pet_button']
        self.assertEqual(actions,['pet:give','pet:gift','pet:list','pet:release'])
        self.e.perform_action('pet:give',{})
        self.assertNotIn('pet:medicine',[o['action'] for o in self.e.get_objects()])
        self.e.roulette_goods['medicine']=1;self.e.perform_action('pet:medicine',{});self.assertEqual(self.e.roulette_goods['medicine'],1)
        self.e.roulette_goods['special_feed']=1
        result=self.e.perform_action('pet:treat',{})
        self.assertIn('feed',[e.get('sound') for e in result['sound_events']])
        a['gift']=dict(resource='seeds',item='tomato',count=1,label='Tomato seeds')
        obj=next(o for o in self.e.get_objects() if o['id']=='pet_gift');before=self.e.resources['seeds']['tomato']
        self.e.perform_action(obj['action'],obj)
        self.assertIsNone(a['gift']);self.assertEqual(self.e.resources['seeds']['tomato'],before+1)
        self.e.perform_action('pet:release',{});self.assertEqual(len(self.e.pets),1)
        self.e.perform_action('pet:detail',{});self.assertEqual(len(self.e.pets),1)
    def test_motion_bounds_and_muzzle_shapes(self):
        self.use('dog_voucher');a=self.p.selected()
        with patch('game.pets.feature.time.monotonic') as clock:
            for t in range(0,100,6):
                clock.return_value=t+10000
                x,y=self.p.position(a);self.assertTrue(41<=x<=43 and 33<=y<=34)
                dx,dy=self.p.position(a,True);self.assertTrue(27<=dx<=31 and 25<=dy<=26)
                self.assertNotEqual(self.p.pose(a),'petting')
        from game.pets.patterns import DETAIL_PATTERNS
        for species,poses in DETAIL_PATTERNS.items():
            for pose,rows in poses.items():self.assertTrue(len(rows)==24 and all(len(r)==36 for r in rows))
        self.assertEqual(DETAIL_PATTERNS['dog']['sitting'][7][-3:],'000')
    def test_pointer_selects_gift_and_shop_shortcut(self):
        self.use('cat_voucher');a=self.p.selected();a['gift']=dict(resource='seeds',item='tomato',count=1,label='Tomato seeds')
        before=self.e.resources['seeds']['tomato']
        self.e.pointer_down(54,32);self.e.pointer_up(54,32)
        self.assertEqual(self.e.resources['seeds']['tomato'],before+1)
        self.e.open_shop();gold=self.e.resource('coin')
        self.e.pointer_down(44,19);self.e.pointer_up(44,19)
        self.assertEqual(self.e.resource('coin'),gold-200)

    def test_duplicate_name_rejected_without_spending_voucher(self):
        self.use('cat_voucher')
        self.e.roulette_goods['cat_voucher']=1
        self.e.perform_action('prize:cat_voucher',{})
        self.assertNotIn('pet:name:0',[o.get('action') for o in self.e.get_objects()])
        self.e.perform_action('pet:name:0',{})
        self.assertEqual(len(self.e.pets),1)
        self.assertEqual(self.e.roulette_goods['cat_voucher'],1)
    def test_motion_preserves_pose_and_direction_and_night_sleeps(self):
        self.use('cat_voucher');a=self.p.selected();before=dict(self.p.motion(a))
        with patch('game.pets.feature.time.monotonic',return_value=10**10):
            self.p.motion(a)
        self.assertEqual(self.p.pose(a),before['pose'])
        self.assertEqual(self.p.motion(a)['left'],before['left'])
        self.e.time_used_cells=16
        self.assertEqual(self.p.pose(a),'sleeping')
    def test_care_retains_scene_and_has_only_owned_pet_slots(self):
        self.e.perform_action('pet:care',{})
        objs=self.e.get_objects()
        self.assertEqual([o['action'] for o in objs if o['type']=='pet_button'],['pet:home','flower:open','pet:active'])
        self.assertTrue(any(o['id']=='home_scene_bed' for o in objs))
        self.assertFalse(any(o['id']=='home_pet_house' for o in objs))
        self.assertFalse(any(o['type']=='pet_icon' for o in self.p.objects()))

    def test_switch_cancel_returns_to_same_pet(self):
        self.use('cat_voucher');selected=self.e.pet_selected
        self.e.perform_action('pet:list',{})
        self.assertEqual(self.e.current_page,'pets')
        self.e.perform_action('pet:detail',{})
        self.assertEqual(self.e.current_page,'pet_detail')
        self.assertEqual(self.e.pet_selected,selected)

import unittest
import game.pets.tests.test_pets as helpers
from unittest.mock import patch

class RouletteTests(unittest.TestCase):
    setUp=helpers.PetTests.setUp
    use=helpers.PetTests.use
    def test_all_reward_categories_and_prices(self):
        self.assertEqual(sum(self.r.cfg()['weights'].values()),100)
        self.assertEqual(self.r.cfg()['weights']['crop_seed'],33)
        for category in self.r.cfg()['weights']:
            before=self.e.resources['coin']
            item={'crop_seed':'tomato','flower_seed':'morning_glory','pet_voucher':'dog_voucher','gold_tool':'gold_pickaxe'}.get(category,category)
            self.e.roulette_queue[0]={'category':category,'item':item}
            self.e.buy_shop_item('roulette','draw')
            self.assertEqual(self.e.resources['coin'],before-200)
            self.assertEqual(self.e.roulette_last_result['category'],category)
        self.e.resources['coin']=199;last=self.e.roulette_last_result.copy();self.e.buy_shop_item('roulette','draw')
        self.assertEqual(self.e.resources['coin'],199);self.assertEqual(self.e.roulette_last_result,last)
    def test_direct_goods_removed_and_voucher_sale(self):
        rows=self.e.registry.collect('shop.buy_items');self.assertFalse(any(r[0] in ('fertilizer','flower_seed') for r in rows))
        self.e.roulette_goods['dog_voucher']=1;before=self.e.resources['coin'];self.e.sell_shop_item('pet_voucher','dog_voucher')
        self.assertEqual(self.e.resources['coin'],before+300)
    def test_kit_nutrient_and_no_discount_draw(self):
        self.e.resources['pickaxe']=1;self.e._pickaxe_hits=15;self.use('gold_pickaxe')
        self.assertTrue(self.e.gold_tools['pickaxe']);self.assertEqual(self.e._pickaxe_hits,0)
        self.use('gold_pickaxe');self.assertEqual(self.e.roulette_goods['gold_pickaxe'],1)
        self.use('plant_nutrient');self.assertEqual(self.e.roulette_goods['plant_nutrient'],1)
        self.e.houseplant.update(stage='flower',bloom_cycles=8,dry_days=2)
        self.e.perform_action('prize:plant_nutrient',{})
        self.assertEqual(self.e.houseplant['bloom_cycles'],0)
        with patch('game.flowers.feature.random.random',return_value=0):self.e.registry.features['flowers'].advance()
        self.assertEqual(self.e.houseplant['stage'],'flower')
        self.e.active_buff={'kind':'purchase_discount','multiplier':.5,'remaining_purchases':3}
        before=self.e.resources['coin'];self.e.buy_shop_item('roulette','draw')
        self.assertEqual(self.e.resources['coin'],before-200);self.assertEqual(self.e.active_buff['remaining_purchases'],3)
    def test_five_rolls_restore_with_slot_and_do_not_leak(self):
        import copy
        before=self.e.snapshot();queue=copy.deepcopy(self.e.roulette_queue)
        self.assertEqual(len(queue),5)
        result=self.e.buy_shop_item('roulette','draw')
        first=copy.deepcopy(self.e.roulette_last_result);following=copy.deepcopy(self.e.roulette_queue)
        self.assertEqual(first['item'],queue[0]['item']);self.assertEqual(following[:4],queue[1:])
        self.assertEqual(result['tts_delay_ms'],1000);self.assertEqual(result['tts_after_sound'],'roulette')
        self.assertNotIn('roulette_queue',result['state'])
        self.e.restore_snapshot(before);self.e.buy_shop_item('roulette','draw')
        self.assertEqual(self.e.roulette_last_result,first);self.assertEqual(self.e.roulette_queue,following)
        self.e.resources['coin']=0;before=copy.deepcopy(self.e.roulette_queue);self.e.buy_shop_item('roulette','draw')
        self.assertEqual(self.e.roulette_queue,before)
    def test_shop_first_entry_and_scene_shortcut(self):
        shop=self.e.registry.features['shop']
        self.assertEqual(shop.purchase_rows(False)[0][0],'roulette')
        self.e.open_shop()
        obj=next(o for o in self.e.get_objects() if o['id']=='shop_scene_roulette')
        self.assertEqual(obj['action'],'buy:roulette:draw')
        gold=self.e.resources['coin'];self.e.perform_action(obj['action'],obj)
        self.assertEqual(self.e.resources['coin'],gold-200)

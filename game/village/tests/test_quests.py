import copy
import tempfile
import unittest
from unittest.mock import patch
from engine.config import load_config
from engine.core.engine import GameEngine
from game.village.quests import RowanQuests, QUESTS

class QuestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.e = GameEngine(load_config('game'), save_dir=self.tmp.name)
        self.e.travel_to('town')
        self.e.resources['seeds']['carrot'] = 1
        self.q = RowanQuests(self.e.registry.features['village'])

    def test_full_sequence_and_gifts_once(self):
        e = self.e
        e.rowan_stage = 'done'
        before = dict(e.resources['crops'])
        e.talk_rowan()
        for key in ('potato','carrot'): self.assertEqual(e.resources['crops'][key],before[key]+1)
        e.talk_rowan(); e.talk_rowan()
        for key in ('potato','carrot'): self.assertEqual(e.resources['crops'][key],before[key]+1)
        gold, feed = e.resources['coin'], e.pasture_goods['animal_feed']
        for index,(name,token,*_) in enumerate(QUESTS):
            if index: e.talk_rowan()
            self.assertEqual(e.rowan_stage, name+'_requested')
            e.talk_rowan()
            self.assertEqual(e.current_page,'rowan_submit')
            self.assertNotIn('town_rowan',[o['id'] for o in e.get_objects()])
            if token == 'fish:low': token = 'fish:bass'
            item=self.q.catalog()[token]; item['bucket'][item['key']]=1
            e.render()
            self.assertEqual(len([o for o in e.get_objects() if o['action']=='rowan_submit:'+token]),1)
            reply=e.submit_rowan_crop(token)
            self.assertEqual(reply['speech_channel'],'quest')
            self.assertEqual(e.current_page,'town')
            self.assertEqual(item['bucket'][item['key']],0)
            snap=e.snapshot();e.submit_rowan_crop(token);self.assertEqual(e.snapshot(),snap)
            if name=='cooking':self.assertEqual(e.active_buff['kind'],'time_slow')
        self.assertEqual(e.rowan_stage,'all_done')
        self.assertEqual(e.resources['coin'],gold+200)
        self.assertEqual(e.pasture_goods['animal_feed'],feed+30)

    def test_daily_rollover_reward_save_and_no_prize_message(self):
        e=self.e;e.rowan_stage='all_done'
        with patch('game.village.quests.random.choice',return_value='crop:carrot'): e.talk_rowan()
        first=copy.deepcopy(e.rowan_daily)
        e.restore_snapshot(e.snapshot());e.talk_rowan();self.assertEqual(e.rowan_daily,first)
        e.resources['crops']['carrot']=1
        e.start_food_effect('rowan_special_red',e.get_recipe_config('rowan_special_red'))
        gold=e.resources['coin']
        with patch('game.village.quests.random.choices',return_value=['none']): reply=e.submit_rowan_crop('crop:carrot')
        self.assertEqual(e.resources['coin']-gold,int(e.config['seeds']['carrot']['crop_price']*1.5))
        self.assertNotIn('extra',reply['tts']);self.assertEqual(e.active_buff['remaining_sales'],3)
        e.talk_rowan();self.assertEqual(e.current_page,'town')
        e.day+=1
        with patch('game.village.quests.random.choice',return_value='mineral:iron'):e.talk_rowan()
        self.assertEqual(e.rowan_daily['item'],'mineral:iron');self.assertFalse(e.rowan_daily['completed'])
        e.day+=1
        with patch('game.village.quests.random.choice',return_value='fish:sardine'):e.registry.run('start_of_day')
        self.assertEqual(e.rowan_daily['item'],'fish:sardine')
        # Old screen cannot submit yesterday's item.
        e.resources['iron']=1;e.submit_rowan_crop('mineral:iron');self.assertEqual(e.resources['iron'],1)

    def test_catalog_grades_and_prizes(self):
        e=self.e;c=self.q.catalog()
        self.assertNotIn('mineral:diamond',c)
        self.assertFalse(any('rowan' in key for key in c))
        for key,grade in [('crop:carrot','low'),('fish:bass','low'),('fish:carp','medium'),('animal_product:egg','low'),('animal_product:wool','medium'),('food:vegetable_fritters','medium'),('food:fish_stew_low','high'),('food:fried_egg','high'),('mineral:iron','high')]:
            self.assertEqual(c[key]['grade'],grade)
        for grade,weights in [('low',[50,25,15,7,2,1]),('medium',[30,25,21,17,5,2]),('high',[20,25,21,20,10,4])]:
            with patch('game.village.quests.random.choices',return_value=['none']) as choose:
                self.assertIsNone(self.q.prize(grade));self.assertEqual(choose.call_args.kwargs['weights'],weights)
        for prize in ('low','medium','high'):
            item=next(v for v in c.values() if v['grade']==prize);before=item['bucket'].get(item['key'],0)
            with patch('game.village.quests.random.choices',return_value=[prize]),patch('game.village.quests.random.choice',return_value=item):self.q.prize('high')
            self.assertEqual(item['bucket'][item['key']],before+1)
        for suffix in ('red','yellow','fish'):
            key='rowan_special_'+suffix
            with patch('game.village.quests.random.choices',return_value=['soup']),patch('game.village.quests.random.choice',return_value=key):self.q.prize('high')
            self.assertEqual(e.resources['foods'][key],1)
        before=e.resources['diamond']
        with patch('game.village.quests.random.choices',return_value=['diamond']): self.q.prize('high')
        self.assertEqual(e.resources['diamond'],before+1)

    def test_special_effect_scope_purchase_failure_and_save(self):
        e=self.e;e.resources['coin']=10000
        for kind,item in [('seed','carrot'),('flower_seed','morning_glory'),('animal_feed','animal_feed')]:
            e.start_food_effect('rowan_special_yellow',e.get_recipe_config('rowan_special_yellow'))
            rows=e.registry.collect('shop.buy_items');base=next(v[4] for v in rows if v[0]==kind and v[1]==item)
            expected=e.purchase_price(base) if kind=='flower_seed' else e.market_price(base,kind,'buy')
            before=e.resources['coin'];reply=e.buy_shop_item(kind,item)
            self.assertEqual(before-e.resources['coin'],expected)
            self.assertEqual(e.active_buff['remaining_purchases'],2)
            self.assertEqual(reply['state']['active_buff']['remaining_purchases'],2)
        e.restore_snapshot(e.snapshot());self.assertEqual(e.active_buff['remaining_purchases'],2)
        e.resources['coin']=0;e.buy_shop_item('seed','carrot');self.assertEqual(e.active_buff['remaining_purchases'],2)
        e.resources['coin']=10000;e.buy_shop_item('seed','carrot');e.buy_shop_item('seed','carrot');self.assertIsNone(e.active_buff['kind'])
        e.start_food_effect('rowan_special_fish',e.get_recipe_config('rowan_special_fish'))
        self.assertEqual(e.loot_amount(3,activity='mining'),6);self.assertEqual(e.loot_amount(1,activity='fishing'),2)
        self.assertEqual(e.loot_amount(3),3);self.assertEqual(e.loot_amount(3,activity='harvest'),3)
        e.tick_buff(10);self.assertEqual(e.loot_amount(3,activity='mining'),3)
        e.start_food_effect('rowan_special_red',e.get_recipe_config('rowan_special_red'))
        for _ in range(3):self.assertEqual(e.sale_price(11),22);e.consume_sale()
        self.assertEqual(e.sale_price(11),11)

    def test_old_save_starts_cooking_and_new_quest_roundtrip(self):
        e=self.e;e.rowan_stage='done';state=e.snapshot();state.pop('rowan_daily');state['research_levels'].pop('animal_shelter')
        e.restore_snapshot(state);e.talk_rowan();self.assertEqual(e.rowan_stage,'cooking_requested')
        e.restore_snapshot(e.snapshot());e.talk_rowan();self.assertEqual(e.rowan_stage,'cooking_requested')
        self.assertEqual(e.current_page,'rowan_submit')

    def test_revised_tutorial_targets_and_saved_progress(self):
        e=self.e
        e.rowan_stage='copper_requested';e.resources['stone']=1;e.resources['copper']=1
        e.restore_snapshot(e.snapshot());e.talk_rowan()
        self.assertIn('rowan_submit:mineral:stone',[o['action'] for o in e.get_objects()])
        gold=e.resources['coin'];e.submit_rowan_crop('mineral:copper')
        self.assertEqual(e.resources['copper'],1);self.assertEqual(e.resources['coin'],gold)
        e.submit_rowan_crop('mineral:stone');self.assertEqual(e.resources['stone'],0)
        self.assertEqual(e.resources['coin'],gold+100)
        for fish in ('sardine','bass','mackerel'):
            e.rowan_stage='sardine_requested'
            for key in e.fishing_config()['fish']:e.resources['fish'][key]=1
            e.restore_snapshot(e.snapshot());reply=e.talk_rowan()
            actions=[o['action'] for o in e.get_objects() if o['type']=='ingredient']
            self.assertEqual(set(actions),{'rowan_submit:fish:'+k for k in ('sardine','bass','mackerel')})
            self.assertNotIn('low',reply['tts'].lower())
            gold=e.resources['coin'];e.submit_rowan_crop('fish:carp')
            self.assertEqual(e.resources['fish']['carp'],1);self.assertEqual(e.resources['coin'],gold)
            before=dict(e.resources['fish']);e.submit_rowan_crop('fish:'+fish)
            self.assertEqual(e.resources['coin'],gold+100)
            for key,count in before.items():self.assertEqual(e.resources['fish'][key],count-int(key==fish))
            self.assertEqual(e.rowan_stage,'sardine_complete')
        # Daily requests still require their exact item, not the tutorial group.
        e.rowan_stage='all_done';e.rowan_daily={'day':e.day,'item':'fish:sardine','completed':False}
        e.talk_rowan();gold=e.resources['coin'];e.submit_rowan_crop('fish:bass')
        self.assertEqual(e.resources['coin'],gold);self.assertFalse(e.rowan_daily['completed'])

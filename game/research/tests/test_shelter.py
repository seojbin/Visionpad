import tempfile
import unittest
from unittest.mock import patch
from engine.config import load_config
from engine.core.engine import GameEngine

class ShelterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.e=GameEngine(load_config('game'),save_dir=self.tmp.name)
    def test_prices_levels_description_and_discount(self):
        e=self.e;e.resources['coin']=1000;e.pasture_goods['wool']=6
        e.perform_action('open_research',{})
        obj=next(o for o in e.get_objects() if o.get('research_kind')=='animal_shelter')
        self.assertEqual(e.get_object_tts(obj),'Animal shelter, 150 Gold, 2 Wool.')
        self.assertEqual(e.get_object_tts(obj,detail=True),'Animal shelter. Level 1. Requires 150 gold, Wool 2 required. Increased yield.')
        self.assertIn('Increased yield',e.get_object_tts(obj,detail=True))
        self.assertEqual([(i['item'],i['required']) for i in obj['display_quantities']],[('coin',150),('wool',2)])
        e.perform_action('research:animal_shelter',{})
        self.assertEqual((e.resources['coin'],e.pasture_goods['wool'],e.research_levels['animal_shelter']),(850,4,1))
        e.start_food_effect('fried_egg',e.get_recipe_config('fried_egg'))
        obj=next(o for o in e.get_objects() if o.get('research_kind')=='animal_shelter')
        self.assertEqual(e.get_object_tts(obj),'Animal shelter, 200 Gold, 4 Wool.')
        self.assertEqual(e.get_object_tts(obj,detail=True),'Animal shelter. Level 2. Requires 200 gold, Wool 4 required. Increased yield.')
        e.perform_action('research:animal_shelter',{})
        self.assertEqual((e.resources['coin'],e.pasture_goods['wool'],e.research_levels['animal_shelter']),(650,0,2))
        obj=next(o for o in e.get_objects() if o.get('research_kind')=='animal_shelter')
        self.assertEqual(e.get_object_tts(obj),'Animal shelter')
        self.assertEqual(e.get_object_tts(obj,detail=True),'Animal shelter. Level 2. Maximum level. Increased yield.')
        before=e.resources['coin'];e.perform_action('research:animal_shelter',{});self.assertEqual(e.resources['coin'],before)
        e.restore_snapshot(e.snapshot());self.assertEqual(e.research_levels['animal_shelter'],2)
    def test_independent_rolls_per_original_unit(self):
        e=self.e;e.resources['coin']=1000
        for kind in ('chicken','sheep'):e.buy_shop_item('animal',kind)
        for kind,base,draws,expected in [('chicken',2,[.29,.30],3),('sheep',4,[0,.3,.2,.99],6)]:
            e.research_levels['animal_shelter']=2
            e.pasture_animals[kind].update(ready=True,quantity=base)
            e.travel_to('pasture');e.perform_action('animal:open:'+kind,{})
            with patch('game.pasture.feature.random.random',side_effect=draws) as roll:
                response=e.registry.features['pasture'].collect()
            product='egg' if kind=='chicken' else 'wool'
            self.assertEqual(e.pasture_goods[product],expected);self.assertEqual(roll.call_count,base)
            self.assertIn(str(expected),response['tts'])
        e.pasture_animals['chicken'].update(ready=True,quantity=2);e.pasture_selected='chicken';e.research_levels['animal_shelter']=1
        with patch('game.pasture.feature.random.random',side_effect=[.149,.15]) as roll:e.registry.features['pasture'].collect()
        self.assertEqual(e.pasture_goods['egg'],6);self.assertEqual(roll.call_count,2)

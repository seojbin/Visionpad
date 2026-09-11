import json, unittest
from unittest.mock import patch
from test_mine import module, ROOT
class FoodEffects(unittest.TestCase):
 def setUp(self):
  self.e=module.GameEngine(json.loads((ROOT/'game_config.json').read_text()))
 def eat(self,key):
  self.e.resources['foods'][key]=1
  return self.e.use_food(key)
 def test_effects_and_private_numbers(self):
  for key,kind,mul,ticks in [('tomato_carrot_stew','harvest_multiplier',1.5,6),('potato_tomato_soup','pickaxe_protection',.5,10),('vegetable_fritters','time_slow',.5,10)]:
   out=self.eat(key)
   self.assertEqual(self.e.active_buff['kind'],kind);self.assertEqual(self.e.active_buff['remaining_ticks'],ticks)
   self.assertEqual(self.e.buff_multiplier_for(kind),mul)
   for text in [out['tts'],out['state']['buff_text']]+[o.get('tts','') for o in self.e.get_recipe_select_objects()+self.e.get_inventory_objects()]:
    self.assertNotIn('퍼센트',text);self.assertNotIn('%',text);self.assertNotIn('절반',text)
 def test_replacement_refresh_expiry(self):
  self.eat('tomato_carrot_stew');self.e.tick_buff(2);self.eat('tomato_carrot_stew')
  self.assertEqual(self.e.active_buff['remaining_ticks'],6)
  self.eat('potato_tomato_soup');self.assertEqual(self.e.buff_multiplier_for('harvest_multiplier'),1)
  self.e.tick_buff(10);self.assertEqual(self.e.buff_text(),'버프 없음')
 def test_half_time_fraction_and_expiry_boundary(self):
  self.eat('vegetable_fritters')
  self.assertEqual(self.e.consume_time('harvest')['cost'],1.5)
  self.assertEqual(self.e.active_buff['remaining_ticks'],8.5)
  self.e.render();self.assertEqual(self.e.get_state()['time']['used_cells'],1.5)
  self.assertEqual(sum(self.e.timepad.dots[0]),3)
  self.e.active_buff['remaining_ticks']=.5
  self.assertEqual(self.e.consume_time('harvest')['cost'],2.5)
  self.assertEqual(self.e.buff_text(),'버프 없음')
  self.assertEqual(self.e.consume_time('travel')['cost'],0)
 def test_protection_halves_capped_probability(self):
  self.e.travel_to('mine');self.e.resources['pickaxe']=1;self.e._pickaxe_hits=28
  self.eat('potato_tomato_soup');rock=self.e.mine_rocks[0]
  with patch.object(module.random,'random',return_value=.6):self.e.hit_mine_rock(rock['id'])
  self.assertEqual(self.e.resources['pickaxe'],1)
  with patch.object(module.random,'random',return_value=.49):self.e.hit_mine_rock(rock['id'])
  self.assertEqual(self.e.resources['pickaxe'],0)
 def test_harvest_yield_and_narration(self):
  self.eat('tomato_carrot_stew')
  pid=next(iter(self.e.farm_plots));self.e.farm_plots[pid]['seed_id']='tomato'
  self.e.harvest_plot_id=pid;self.e.harvest_targets=[{'id':0}];self.e.harvest_collected_ids={0}
  before=self.e.resources['crops']['tomato']
  out=self.e.finish_harvest_minigame()
  self.assertEqual(self.e.resources['crops']['tomato']-before,3)
  self.assertNotIn('퍼센트',out['tts'])
if __name__=='__main__':unittest.main()

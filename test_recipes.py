import copy,json,math,unittest
from unittest.mock import patch
from test_mine import module,ROOT
class RecipeTests(unittest.TestCase):
 def setUp(self):
  self.c=json.loads((ROOT/'game_config.json').read_text());self.e=module.GameEngine(self.c)
 def test_seed_chances_and_no_spoken_probability(self):
  for level,expected in [(1,.3),(2,.6)]:
   self.e.research_levels['seed_return']=level
   for seed in self.c['seeds']:self.assertEqual(self.e.get_effective_seed_return_chance(seed),expected)
   for obj in self.e.get_research_objects()+self.e.get_seed_select_objects():
    self.assertNotIn('퍼센트',obj.get('tts',''));self.assertNotIn('%',obj.get('tts',''))
  self.assertNotIn('harvest_yield',self.e.research_levels)
  self.assertNotIn('harvest_yield',self.c['research'])
 def test_seed_research_copper_atomic_and_two_levels(self):
  self.e.resources.update(coin=200,copper=2)
  self.assertEqual(self.e.buy_research('seed_return')['sfx'],'error');self.assertEqual(self.e.resources['coin'],200)
  self.e.resources['copper']=9
  for level in [1,2]:self.e.buy_research('seed_return');self.assertEqual(self.e.research_levels['seed_return'],level)
  self.assertEqual(self.e.resources['copper'],0);self.assertEqual(self.e.resources['coin'],140)
  self.assertEqual(self.e.buy_research('seed_return')['sfx'],'error')
 def test_new_recipe_replaces_old_and_first_stage_unchanged(self):
  self.assertNotIn('garden_stew',self.c['recipes']);self.assertNotIn('garden_stew',self.e.resources['foods'])
  r=self.c['recipes']['vegetable_fritters'];self.assertEqual(r['ingredients'],{'potato':1,'carrot':1})
  self.assertEqual(r['gesture_steps'][0]['path'],[[12,12],[22,28],[32,12],[42,28],[48,12]])
  self.assertEqual(self.e.get_food_sell_price('vegetable_fritters'),30)
 def test_flower_has_eight_petals_and_fits_pad(self):
  self.e.selected_recipe_id='vegetable_fritters';self.e.cooking_stage_index=1
  r=self.c['recipes']['vegetable_fritters']['gesture_steps'][1];p=r['path'];self.assertEqual(p[0],p[-1])
  radii=[math.hypot(x-29.5,y-19.5) for x,y in p[:-1]]
  maxima=sum(v>radii[(i-1)%len(radii)] and v>radii[(i+1)%len(radii)] for i,v in enumerate(radii))
  self.assertEqual(maxima,8)
  fitted=self.e.get_cooking_gesture()['path'];self.assertTrue(all(4<=x<=55 and 4<=y<=35 for x,y in fitted))
  self.assertEqual(fitted[0],fitted[-1])
 def test_icons_are_distinct_and_shared(self):
  icons=[]
  for obj in self.e.get_research_objects():
   if obj['type']!='research':continue
   self.e.dotpad.clear();self.e.draw_research(obj);icons.append(self.c['research']['seed_return' if obj['research_kind']=='seed_return' else 'field_expansion' if obj['research_kind']=='field_expand' else 'mineral_luck']['icon'])
   x,y=obj['x'],obj['y'];actual=[''.join(str(v) for v in self.e.dotpad.dots[row][x-3:x+4]) for row in range(y-3,y+4)]
   self.assertEqual(actual,icons[-1])
  # Verify all research icons, including mapping field_expand -> field_expansion.
  self.assertEqual(len({tuple(rows) for rows in icons}),3)
  food_icons=[]
  for key in self.c['recipes']:
   def raster(draw,obj):
    self.e.dotpad.clear();draw(obj)
    return tuple(tuple(self.e.dotpad.dots[y][27:34]) for y in range(18,23))
   base={'x':30,'y':20,'width':12,'height':9}
   recipe=raster(self.e.draw_recipe,{**base,'recipe_id':key})
   stock=raster(self.e.draw_resource,{**base,'resource_kind':'food','recipe_id':key})
   shop=raster(self.e.draw_shop_item,{**base,'shop_kind':'food','item_id':key})
   self.assertEqual(recipe,stock);self.assertEqual(stock,shop);food_icons.append(recipe)
  self.assertEqual(len(set(food_icons)),3)
 def test_fritters_full_two_stage_cooking(self):
  clock=[100.];self.e.selected_recipe_id='vegetable_fritters';self.e.selected_ingredients={'potato','carrot'}
  before=copy.deepcopy(self.e.resources['crops'])
  with patch.object(module.time,'monotonic',side_effect=lambda:clock[0]):
   self.e.open_cooking_minigame()
   for stage in [0,1]:
    self.assertEqual(self.e.cooking_stage_index,stage)
    samples=list(self.e.cooking_path_samples);self.e.pointer_down(*samples[0])
    for pt in samples[1:]:
     self.e.pointer_drag(*pt)
     if self.e.pending_visual_completion:break
    self.e.pointer_up(*samples[-1]);clock[0]+=1;self.e.visual_tick()
    if stage==0:self.assertEqual(self.e.resources['crops'],before)
  self.assertEqual(self.e.resources['foods']['vegetable_fritters'],1)
  self.assertEqual(self.e.resources['crops']['potato'],before['potato']-1)
  self.assertEqual(self.e.resources['crops']['carrot'],before['carrot']-1)
  self.assertEqual(self.e.resources['crops']['tomato'],before['tomato'])
if __name__=='__main__':unittest.main()

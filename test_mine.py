"""Isolated engine checks; the fake pad models the 60x40 raster, not USB hardware."""
import importlib.util, json, sys, types, unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parent
class Pad:
    def __init__(self,width,height): self.width=width; self.height=height; self.clear()
    def clear(self): self.dots=[[0]*self.width for _ in range(self.height)]
    def to_list(self): return self.dots
    def set_dot(self,x,y,*args):
        x,y=int(round(x)),int(round(y))
        if 0<=x<self.width and 0<=y<self.height:self.dots[y][x]=1
    def draw_line(self,x1,y1,x2,y2):
        n=max(1,int(max(abs(x2-x1),abs(y2-y1))))
        for i in range(n+1):self.set_dot(x1+(x2-x1)*i/n,y1+(y2-y1)*i/n)
    def draw_box(self,x,y,w,h):
        x,y=int(x)-w//2,int(y)-h//2
        self.draw_line(x,y,x+w-1,y);self.draw_line(x,y+h-1,x+w-1,y+h-1)
        self.draw_line(x,y,x,y+h-1);self.draw_line(x+w-1,y,x+w-1,y+h-1)
    def __getattr__(self,name):return lambda *a,**kw:None
# Keep this stub scoped to the test module import.
prior=sys.modules.get('dotpad');sys.modules['dotpad']=types.SimpleNamespace(DotPad=Pad)
spec=importlib.util.spec_from_file_location('mine_engine', ROOT/'game_engine.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if prior is None:del sys.modules['dotpad']
else:sys.modules['dotpad']=prior
class MineTests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads((ROOT/'game_config.json').read_text());self.e=module.GameEngine(self.cfg)
    def enter(self):self.e.travel_to('mine')
    def test_existing_tunings_retained(self):
        self.assertEqual(self.e.disappear_delay_seconds,.2);self.assertEqual(self.e.resume_marker_delay_seconds,.4)
        self.assertEqual(self.e.client_settings['audio']['bgm_gain']['basic'],.9)
    def test_layout_100_days(self):
        for day in range(100):
            self.e.day=day;self.e.regenerate_mine();rocks=self.e.mine_rocks;self.assertEqual(len(rocks),7)
            for a in rocks:
                self.assertEqual(a['width']*a['height'],100)
                self.assertTrue(0<=a['left'] and a['left']+10<=60 and 0<=a['top'] and a['top']+10<=40)
                self.assertFalse(a['left']<12 and a['top']+10>30)
            for i,a in enumerate(rocks):
                for b in rocks[i+1:]:
                    self.assertTrue(a['left']+15<=b['left'] or b['left']+15<=a['left'] or a['top']+15<=b['top'] or b['top']+15<=a['top'])
    def test_filled_rock_and_exact_hit(self):
        self.enter();r=self.e.mine_rocks[0];obj=self.e.get_mine_objects()[0]
        self.assertTrue(all(self.e.dotpad.dots[y][x] for y in range(r['top'],r['top']+10) for x in range(r['left'],r['left']+10)))
        self.assertFalse(self.e.object_contains(obj,r['left']+10,r['top']))
    def test_pickaxe_prices_capacity_trade(self):
        self.assertEqual(self.e.get_pickaxe_price(),60)
        self.assertEqual([self.e.get_mineral_price(k) for k in ['stone','copper','iron','diamond']],[15,21,27,243])
        self.e.resources['coin']=1000
        self.e.buy_shop_item('pickaxe','pickaxe');coins=self.e.resources['coin']
        self.assertEqual(self.e.buy_shop_item('pickaxe','pickaxe')['sfx'],'error');self.assertEqual(self.e.resources['coin'],coins)
        for k in ['stone','copper','iron']:
            before=self.e.resources['coin'];self.e.buy_shop_item('mineral',k);self.assertEqual(self.e.resources['coin'],before-self.e.get_mineral_price(k)*2)
            self.e.sell_shop_item('mineral',k);self.assertEqual(self.e.resources['coin'],before-self.e.get_mineral_price(k))
        self.assertEqual(self.e.buy_shop_item('mineral','diamond')['sfx'],'error')
    def test_three_touches_and_no_tool(self):
        self.enter();r=self.e.mine_rocks[0]
        self.assertIn('곡괭이',self.e.hit_mine_rock(r['id'])['tts']);self.assertEqual(r['hits'],0)
        self.e.resources['pickaxe']=1
        for i in range(2):self.assertEqual(self.e.hit_mine_rock(r['id'])['sound_events'][0]['sound'],'pickaxe')
        with patch.object(module.random,'choices',return_value=['copper']),patch.object(module.random,'random',return_value=.9):out=self.e.hit_mine_rock(r['id'])
        self.assertEqual(self.e.resources['copper'],1);self.assertEqual(out['sound_events'][0]['kind'],'mining_loot');self.assertEqual(len(self.e.mine_rocks),6)
        self.assertEqual(self.e.hit_mine_rock(r['id'])['sound_events'],[])
    def test_drag_does_not_hit_and_reentry_does_not_reset(self):
        self.enter();self.e.resources['pickaxe']=1;obj=self.e.get_mine_objects()[0]
        self.e.pointer_down(obj['x'],obj['y']);self.e.pointer_down(obj['x'],obj['y'])
        self.e.pointer_drag(obj['x'],obj['y']);self.e.pointer_up(obj['x'],obj['y']);self.assertEqual(self.e.mine_rocks[0]['hits'],1)
        saved=[dict(r) for r in self.e.mine_rocks];self.e.travel_to('town');self.enter();self.assertEqual(self.e.mine_rocks,saved)
    def test_new_day_refresh_and_private_fields(self):
        self.enter();self.e.mine_rocks.pop();self.e._pickaxe_hits=8;self.e.resources['pickaxe']=1
        self.e.finish_sleep();self.assertEqual(len(self.e.mine_rocks),7);self.assertEqual(self.e._pickaxe_hits,8)
        state=json.dumps(self.e.get_state(),ensure_ascii=False)
        for secret in ['_pickaxe_hits','pickaxe_break','safe_hits','loot_weights']:self.assertNotIn(secret,state)
        self.assertNotIn('8',self.e.travel_to('mine')['tts'])
    def test_pickaxe_break_boundaries(self):
        self.enter();self.e.resources['pickaxe']=1;r=self.e.mine_rocks[0]
        self.e._pickaxe_hits=8
        with patch.object(module.random,'random',return_value=0):self.e.hit_mine_rock(r['id'])
        self.assertEqual(self.e.resources['pickaxe'],1)
        r['hits']=0
        with patch.object(module.random,'random',return_value=.049):out=self.e.hit_mine_rock(r['id'])
        self.assertEqual(self.e.resources['pickaxe'],0);self.assertIn('다시 구매',out['tts'])
        self.e.resources['coin']=60;self.e.buy_shop_item('pickaxe','pickaxe');self.assertEqual(self.e._pickaxe_hits,0)
    def test_luck_weights_and_bonus(self):
        self.enter();self.e.resources['pickaxe']=1;self.e.research_levels['mineral_luck']=2;r=self.e.mine_rocks[0];r['hits']=2
        with patch.object(module.random,'choices',return_value=['diamond']) as choose,patch.object(module.random,'random',return_value=.29):out=self.e.hit_mine_rock(r['id'])
        self.assertEqual(choose.call_args.kwargs['weights'],[3,15,34,48]);self.assertEqual(self.e.resources['diamond'],2)
        self.assertEqual(out['sound_events'][0]['sound'],'shine');self.assertIn('보너스',out['sound_events'][0]['tts'])
    def test_research_materials_atomic_and_max(self):
        self.e.resources['coin']=1000
        before=self.e.resources['coin'];self.assertEqual(self.e.buy_research('field_expand')['sfx'],'error');self.assertEqual(self.e.resources['coin'],before)
        self.e.resources.update(stone=15,copper=9,iron=9)
        for kind in ['field_expand','harvest_yield','mineral_luck']:
            for _ in range(2):self.e.buy_research(kind)
        self.assertEqual(self.e.resources['stone'],0);self.assertEqual(self.e.resources['copper'],0);self.assertEqual(self.e.resources['iron'],0)
        self.assertEqual(self.e.get_harvest_base_yield('tomato'),4)
        self.e.get_research_objects() # No invalid cost index at max level.
        before=self.e.resources['coin'];self.e.buy_research('harvest_yield');self.assertEqual(self.e.resources['coin'],before)
    def test_all_shop_and_inventory_items_accessible(self):
        self.e.resources.update(coin=1000,stone=2,copper=2,iron=2,diamond=2,pickaxe=1)
        self.e.resources['foods']={k:1 for k in self.cfg['recipes']}
        buys=self.e.get_shop_buy_objects();self.assertEqual(sum(o['type']=='shop_item' for o in buys),8)
        sells=self.e.get_shop_sell_objects();self.assertEqual(sum(o['type']=='shop_item' for o in sells),10)
        found=[]
        for page in range(3):self.e.inventory_page=page;found.extend(o['label'] for o in self.e.get_inventory_objects())
        for label in ['곡괭이','돌','구리','철','다이아몬드']:self.assertIn(label,found)
    def test_arrow_step(self):
        self.e.travel_to('town');arrow=next(o for o in self.e.get_town_objects() if o['id']=='town_mine')
        out=self.e.perform_action(arrow['action'],arrow);self.assertIn({'kind':'one_shot','sound':'step'},out['sound_events']);self.assertEqual(self.e.current_page,'mine')
    def test_hover_does_not_repeat_on_strikes(self):
        self.enter();self.e.resources['pickaxe']=1;obj=self.e.get_mine_objects()[0];x,y=obj['x'],obj['y']
        self.assertTrue(self.e.pointer_move(x,y)['tts'])
        for _ in range(2):
            self.assertIsNone(self.e.pointer_down(x,y)['tts'])
            self.assertIsNone(self.e.pointer_drag(x,y)['tts'])
            self.assertIsNone(self.e.pointer_up(x,y)['tts'])
            self.assertIsNone(self.e.pointer_move(x,y)['tts'])
        other=self.e.get_mine_objects()[1]
        self.assertTrue(self.e.pointer_move(other['x'],other['y'])['tts'])
    def test_fatigue_only_on_break_and_night_keeps_loot(self):
        self.enter();self.e.resources['pickaxe']=1;r=self.e.mine_rocks[0]
        self.e.hit_mine_rock(r['id']);self.e.hit_mine_rock(r['id']);self.assertEqual(self.e.time_used_cells,0)
        with patch.object(module.random,'choices',return_value=['stone']),patch.object(module.random,'random',return_value=.99):self.e.hit_mine_rock(r['id'])
        self.assertEqual(self.e.time_used_cells,2)
        self.e.time_used_cells=self.e.time_total_cells-2;r=self.e.mine_rocks[0];r['hits']=2
        before=self.e.resources['stone']
        with patch.object(module.random,'choices',return_value=['stone']),patch.object(module.random,'random',return_value=.99):out=self.e.hit_mine_rock(r['id'])
        self.assertTrue(self.e.day_ended);self.assertEqual(self.e.current_location,'home')
        self.assertEqual(self.e.resources['stone'],before+1);self.assertIn('집에 도착',out['sound_events'][0]['tts'])
    def test_minimap_plus_only_on_current_node(self):
        for location in ['home','farm','town','mine']:
            self.e.travel_to(location);self.e.open_minimap()
            for node in self.e.get_minimap_objects():
                if node.get('type')!='node':continue
                x,y=node['x'],node['y']
                self.e.dotpad.clear();self.e.draw_node(node)
                self.assertEqual(self.e.dotpad.dots[y][x],int(node.get('current',False)))
                if node.get('current'):
                    for dx,dy in [(-2,0),(2,0),(0,-2),(0,2)]:self.assertEqual(self.e.dotpad.dots[y+dy][x+dx],1)
if __name__=='__main__':unittest.main()

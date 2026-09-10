"""Run: python -m unittest -v test_game.py"""
import unittest,json,copy
from pathlib import Path
from game_engine import GameEngine
from dotpad import DotPad
CONFIG=json.loads(Path(__file__).with_name('game_config.json').read_text())
class GameTests(unittest.TestCase):
    def setUp(self): self.e=GameEngine(copy.deepcopy(CONFIG))
    def spray(self,mode='water'):
        e=self.e;e.start_care_minigame('plot_1',mode)
        targets=list(e.care_targets)
        e.pointer_down(targets[0]['x'],targets[0]['y'])
        for t in targets[1:]: e.pointer_drag(t['x'],t['y'])
        return e.pointer_up(targets[-1]['x'],targets[-1]['y'])
    def test_initial_cooking_stock(self):
        self.assertEqual(self.e.resources['crops'], dict(tomato=3, carrot=3, potato=3))
        for rid in CONFIG['recipes']: self.assertTrue(self.e.can_craft_recipe(rid))
    def test_fertilizer_immediate_and_no_double_bonus(self):
        e=self.e;e.travel_to('farm');e.plant_seed('plot_1','tomato');self.spray()
        r=self.spray('fertilizer')
        self.assertEqual(e.farm_plots['plot_1']['growth'],1)
        self.assertIn('1일 단축',r['tts']);self.assertNotIn('활동',r['tts'])
        e.next_day();self.assertEqual(e.farm_plots['plot_1']['growth'],2)
        e.travel_to('farm');self.spray();e.fertilize_plot('plot_1')
        self.assertTrue(e.farm_plots['plot_1']['mature'])
    def test_activity_tts_removed_display_retained(self):
        e=self.e;e.travel_to('farm');r=e.plant_seed('plot_1','carrot')
        self.assertNotIn('틱 남음',r['tts'])
        self.assertEqual(r['state']['time']['used_cells'],2)
        self.assertNotIn('활동',e.resource_summary_text())
    def test_arrows_rotation_symmetry(self):
        for size in [2,3,4]:
            pads={}
            for d in ['right','left','up','down']:
                p=DotPad(21,21);p.draw_arrow(10,10,d,size)
                pads[d]={(x-10,y-10) for y,row in enumerate(p.matrix) for x,v in enumerate(row) if v}
            self.assertEqual(pads['left'],{(-x,y) for x,y in pads['right']})
            self.assertEqual(pads['up'],{(y,-x) for x,y in pads['right']})
            self.assertEqual(pads['right'],{(x,-y) for x,y in pads['right']})
    def test_free_travel_preserves_buff_and_growth(self):
        e=self.e;e.config['time']['action_costs']['travel']=10
        e.active_buff.update(remaining_ticks=6,multiplier=1.25)
        for place in ['farm','town','home']*8:e.travel_to(place)
        self.assertEqual(e.time_used_cells,0);self.assertEqual(e.active_buff['remaining_ticks'],6)
    def test_daily_farming_loop(self):
        e=self.e;e.travel_to('farm');e.open_plot_detail('plot_1');e.plant_seed('plot_1','carrot')
        self.assertEqual(e.time_used_cells,2)
        self.spray();self.assertTrue(e.farm_plots['plot_1']['watered'])
        self.assertEqual(e.farm_plots['plot_1']['growth'],0)
        e.next_day();self.assertEqual(e.farm_plots['plot_1']['growth'],1)
        e.travel_to('farm');e.open_plot_detail('plot_1');self.spray();e.next_day()
        self.assertTrue(e.farm_plots['plot_1']['mature'])
        e.travel_to('farm');e.open_plot_detail('plot_1');e.start_harvest_minigame('plot_1')
        ts=list(e.harvest_targets);e.pointer_down(ts[0]['x'],ts[0]['y'])
        for t in ts[1:-1]:e.pointer_drag(t['x'],t['y'])
        r=e.pointer_up(ts[-1]['x'],ts[-1]['y'])
        self.assertIn('100퍼센트',r['tts']);self.assertEqual(e.resources['crops']['carrot'],6)
        self.assertEqual(e.time_used_cells,3)
    def test_failed_care_no_cost_and_fertilizer_after_water(self):
        e=self.e;e.travel_to('farm');e.plant_seed('plot_1','tomato');e.open_plot_detail('plot_1')
        self.assertIn('먼저 물',e.start_care_minigame('plot_1','fertilizer')['tts'])
        e.start_care_minigame('plot_1','water');e.pointer_down(0,0);e.pointer_up(0,0)
        self.assertEqual(e.time_used_cells,2)
        self.spray();count=e.resources['fertilizer'];self.spray('fertilizer')
        self.assertEqual(e.resources['fertilizer'],count-1);e.next_day()
        self.assertEqual(e.farm_plots['plot_1']['growth'],2)
    def test_night_has_result_and_sleep_only(self):
        e=self.e;e.travel_to('farm');e.time_used_cells=19
        r=e.plant_seed('plot_1','carrot')
        self.assertTrue(e.day_ended);self.assertEqual(e.current_location,'home')
        self.assertIn('심었습니다',r['tts']);self.assertIn('밤',r['tts'])
        self.assertEqual([o['id'] for o in e.get_objects()],['home_bed'])
        e.travel_to('town');self.assertEqual(e.current_location,'home')
    def test_shop_and_research(self):
        e=self.e;e.travel_to('town');e.open_shop();e.open_shop_mode('buy')
        e.buy_shop_item('seed','carrot');self.assertEqual(e.resources['coin'],52)
        e.return_to_scene();self.assertEqual(e.current_page,'town')
        e.resources['crops']['carrot']=2;e.open_shop_mode('sell');e.sell_shop_item('crop','carrot')
        self.assertEqual(e.resources['coin'],62);e.return_to_scene();self.assertEqual(e.current_page,'town')
        e.travel_to('home');e.buy_research('field_expand');self.assertEqual(e.unlocked_plot_count,3)
    def test_cooking_and_food(self):
        e=self.e;rid='tomato_carrot_stew'
        e.resources['crops'].update(tomato=0,carrot=0);self.assertFalse(e.can_craft_recipe(rid));e.resources['crops'].update(tomato=1,carrot=1)
        self.assertTrue(e.can_craft_recipe(rid));self.assertEqual(e.get_food_sell_price(rid),27)
        e.open_recipes();e.select_recipe(rid)
        for seed in ['tomato','carrot']:e.toggle_ingredient(seed)
        e.open_cooking_minigame()
        for _ in range(len(e.get_cooking_steps())):
            path=list(e.cooking_path_samples)
            e.pointer_down(*path[0])
            for point in path[1:]:e.pointer_drag(*point)
            e.pointer_up(*path[-1])
        self.assertEqual(e.resources['foods'][rid],1)
        self.assertEqual(e.resources['crops']['tomato'],0);self.assertEqual(e.time_used_cells,3)
        e.open_inventory();e.use_food(rid);self.assertEqual(e.active_buff['remaining_ticks'],6)
        e.travel_to('farm');self.assertEqual(e.active_buff['remaining_ticks'],6)
    def test_pause_does_not_finish_care(self):
        e=self.e;e.travel_to('farm');e.plant_seed('plot_1','carrot');e.start_care_minigame('plot_1','water')
        t=e.care_targets[0];e.pointer_down(t['x'],t['y']);e.handle_command('pause')
        e.pointer_up(t['x'],t['y']);self.assertFalse(e.farm_plots['plot_1']['watered'])
    def test_all_pages_render(self):
        e=self.e
        for page in CONFIG['pages']:
            e.current_page=page;e.render();state=e.get_state()
            self.assertEqual(len(state['dots']),40);self.assertTrue(all(len(row)==60 for row in state['dots']))
    def test_correct_only_for_new_targets(self):
        e=self.e;e.travel_to('farm');e.plant_seed('plot_1','carrot');e.start_care_minigame('plot_1','water')
        t=e.care_targets[0];r=e.pointer_down(t['x'],t['y'])
        self.assertEqual(r['sound_events'][0]['kind'],'correct')
        self.assertGreater(r['sound_events'][0]['count'],0)
        r=e.pointer_drag(t['x'],t['y']);self.assertEqual(r['sound_events'],[])
        e.handle_command('pause');r=e.pointer_drag(30,20);self.assertEqual(r['sound_events'],[])
    def test_release_retains_scoring_audio(self):
        e=self.e;e.travel_to('farm');e.plant_seed('plot_1','carrot');e.start_care_minigame('plot_1','water')
        e.care_targets=[{'id':'target','x':30,'y':20}]
        e.pointer_down(0,0);r=e.pointer_up(30,20)
        self.assertEqual(r['sound_events'],[{'kind':'correct','count':1}])
        self.assertTrue(e.farm_plots['plot_1']['watered'])
    def test_cut_then_stir_sound_and_no_early_consumption(self):
        e=self.e;rid='tomato_carrot_stew';e.resources['crops'].update(tomato=1,carrot=1)
        e.select_recipe(rid)
        for seed in ['tomato','carrot']:e.toggle_ingredient(seed)
        e.open_cooking_minigame()
        self.assertEqual(e.pointer_down(0,0)['sound_events'],[])
        path=list(e.cooking_path_samples);r=e.pointer_down(*path[0])
        self.assertEqual(r['sound_events'],[{'kind':'work_start','sound':'cut'}])
        self.assertEqual(e.pointer_drag(*path[0])['sound_events'],[])
        for point in path[1:]:e.pointer_drag(*point)
        e.pointer_up(*path[-1]);self.assertEqual(e.get_cooking_kind(),'stir')
        self.assertEqual(e.resources['crops']['tomato'],1);self.assertEqual(e.time_used_cells,0)
        self.assertEqual(e.resources['foods'][rid],0)
        point=e.cooking_path_samples[0];r=e.pointer_down(*point)
        self.assertEqual(r['sound_events'],[{'kind':'work_start','sound':'cook'}])
        e.pointer_up(*point);self.assertEqual(e.cooking_stage_index,1)
        self.assertEqual(e.resources['crops']['carrot'],1)
    def test_all_recipes_complete_two_gestures(self):
        for rid,recipe in CONFIG['recipes'].items():
            e=GameEngine(copy.deepcopy(CONFIG));e.resources['crops'].update(recipe['ingredients'])
            e.select_recipe(rid)
            for seed in recipe['ingredients']:e.toggle_ingredient(seed)
            e.open_cooking_minigame()
            for kind in ['cut','stir']:
                self.assertEqual(e.get_cooking_kind(),kind)
                path=list(e.cooking_path_samples);e.pointer_down(*path[0])
                for point in path[1:]:e.pointer_drag(*point)
                e.pointer_up(*path[-1])
            self.assertEqual(e.resources['foods'][rid],1);self.assertEqual(e.time_used_cells,3)
if __name__=='__main__':unittest.main()

"""Seafood: fish as cooking ingredients, graded seafood dishes, and the food effects they grant.

Owns no engine attributes. Paired with cooking (still core): cooking calls the exposed seafood
functions while a seafood recipe is selected, and seafood writes cooking's selected_ingredients
and active_buff. The food-effect modifiers (boost_rare_weights, loot_amount, sale_price,
consume_sale) are used by mining, fishing, harvest, cooking and the village market.
"""
import math
import random

from visionpad.core.registry import Feature


class Seafood(Feature):
    name = "seafood"

    def register(self, reg):
        reg.save_fields(migrate=self.migrate)
        for name in ("selected_fish", "seafood_ready", "seafood_ingredient_objects", "toggle_fish", "finish_seafood",
                     "boost_rare_weights", "loot_amount", "sale_price", "consume_sale"):
            reg.expose(name, getattr(self, name))

    @staticmethod
    def migrate(state, fresh):
        # Retired high-grade fried fish becomes the supported medium variant.
        foods = state['resources'].setdefault('foods', {})
        retired = foods.pop('fried_fish_high', 0)
        if retired: foods['fried_fish_medium'] = foods.get('fried_fish_medium', 0) + retired
        buff = state.get('active_buff', {})
        if buff.get('source') == 'fried_fish_high': buff['source'] = 'fried_fish_medium'
        recipe = fresh.get_recipe_config(buff.get('source'))
        if recipe.get('seafood'):
            for field, key in [('multiplier','buff_multiplier'), ('rare_weight_multiplier','rare_weight_multiplier'), ('double_chance','double_chance')]:
                if key in recipe: buff[field] = recipe[key]
            if 'sale_uses' in recipe: buff['remaining_sales'] = min(buff.get('remaining_sales',0),recipe['sale_uses'])
            buff['remaining_ticks'] = min(buff.get('remaining_ticks',0),recipe.get('buff_ticks',0))

    def selected_fish(self):
        return next((k[5:] for k in self.engine.selected_ingredients if k.startswith('fish:')),None)

    def fish_allowed(self, recipe, fish_id):
        fish = self.engine.fishing_config()['fish'].get(fish_id)
        return bool(fish and fish_id in recipe.get('allowed_fish', [])
                    and fish['grade'] in recipe.get('quality_effects', {})
                    and (not recipe.get('fish_grade') or recipe['fish_grade']==fish['grade']))

    def seafood_ready(self, recipe, selected=False):
        e = self.engine
        if any(e.resources['crops'].get(k,0)<n for k,n in recipe.get('ingredients',{}).items()):return False
        candidates=[self.selected_fish()] if selected else e.fishing_config()['fish']
        return any(self.fish_allowed(recipe,k) and e.resources['fish'].get(k,0)>=recipe.get('fish_required',1) for k in candidates)

    def seafood_ingredient_objects(self, objects):
        e = self.engine
        recipe=e.get_recipe_config(e.selected_recipe_id)
        if not recipe.get('seafood'):return objects
        for key,fish in e.fishing_config()['fish'].items():
            count=e.resources['fish'].get(key,0)
            if not self.fish_allowed(recipe,key) or count < recipe.get('fish_required',1):continue
            selected=self.selected_fish()==key
            objects.insert(len(objects)-1,{'id':'ingredient_'+key,'type':'ingredient','ingredient_id':key,'item_kind':'fish',
                'x':8,'y':6,'width':12,'height':9,'hit_width':12,'hit_height':9,'label':fish['label'],
                'count':count,'required_count':recipe.get('fish_required',1),'selected':selected,
                'tts':f"{fish['label']}. Stock {count}. {'Selected.' if selected else 'Choose one fish.'}",
                'action':'toggle_ingredient:fish:'+key})
        return objects

    def toggle_fish(self, key):
        e = self.engine
        fish_id=key[5:];recipe=e.get_recipe_config(e.selected_recipe_id)
        if not recipe.get('seafood') or not self.fish_allowed(recipe,fish_id) or e.resources['fish'].get(fish_id,0)<recipe.get('fish_required',1):
            return e.response(tts='Fish unavailable.')
        was_selected=key in e.selected_ingredients
        e.selected_ingredients={k for k in e.selected_ingredients if not k.startswith('fish:')}
        if not was_selected:e.selected_ingredients.add(key)
        if set(recipe['ingredients']).issubset(e.selected_ingredients) and self.selected_fish():
            e.pointer_pressed=False
            return e.open_cooking_minigame()
        e.clear_hover();e.render()
        return e.response(tts='Fish deselected.' if was_selected else 'Fish selected.')

    def finish_seafood(self, recipe):
        e = self.engine
        if not self.seafood_ready(recipe,selected=True):
            e.clear_cooking();e.current_page=e.current_location='home';e.render()
            return e.response(tts='Not enough ingredients.')
        fish=self.selected_fish();grade=e.fishing_config()['fish'][fish]['grade']
        rid=e.selected_recipe_id+'_'+grade
        for key,count in recipe['ingredients'].items():e.add_resource('crops', -count, item=key)
        e.add_resource('fish', -recipe.get('fish_required',1), item=fish)
        amount=self.loot_amount(1)
        e.resources['foods'][rid]=e.resources['foods'].get(rid,0)+amount
        e.registry.run('activity', 'cooking', e.get_recipe_config(rid)['label'], amount)
        text=f"{e.get_recipe_config(rid)['label']} {amount} made."+(' Bonus.' if amount>1 else '')
        e.clear_cooking();e.clear_hover();e.current_page=e.current_location='home'
        result=e.consume_time('cook');e.render()
        return e.night_response(text) if result['night'] else e.response(tts=text,sfx='cooking_success')

    def boost_rare_weights(self, weights, rare_keys):
        buff = self.engine.active_buff
        result=dict(weights)
        if buff.get('kind')=='rare_find' and buff.get('remaining_ticks',0)>0:
            multiplier=buff.get('rare_weight_multiplier',1)
            for key in rare_keys:result[key]=result.get(key,0)*multiplier
        return result

    def loot_amount(self, amount):
        buff = self.engine.active_buff
        if buff.get('kind')=='double_loot' and buff.get('remaining_ticks',0)>0:
            if random.random()<buff.get('double_chance',0):return amount*2
        return amount

    def sale_price(self, price):
        buff = self.engine.active_buff
        if buff.get('kind')=='sale_boost' and buff.get('remaining_sales',0)>0:
            return math.floor(price*buff.get('multiplier',1))
        return price

    def consume_sale(self):
        e = self.engine
        if e.active_buff.get('kind')=='sale_boost' and e.active_buff.get('remaining_sales',0)>0:
            e.active_buff['remaining_sales']-=1
            if not e.active_buff['remaining_sales']:
                e.active_buff={'kind':None,'source':None,'multiplier':1,'remaining_ticks':0}

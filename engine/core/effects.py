"""Food effects: the one active food buff and the modifiers every activity applies with it.

active_buff is shared state: cooking and seafood start effects, time spends them, and mining,
fishing, harvest, the shop and the village market read them. Everything here does exactly what
the code did before the split.
"""
import math
import random


class FoodEffects:
    NO_EFFECT = {"kind": None, "source": None, "multiplier": 1.0, "remaining_ticks": 0}

    def recipe_effect_text(self, recipe):
        if recipe.get('buff_kind') == 'research_discount': return 'Research discount, next research'
        if recipe.get('buff_kind') == 'sale_boost':
            return f"{recipe.get('buff_label', 'Better sales')}, {recipe.get('sale_uses', 3)} sales"
        return f"{recipe.get('buff_label', 'Food effect')}, {float(recipe.get('buff_ticks', 0)):g} hours"

    def start_food_effect(self, recipe_id, recipe):
        self.active_buff = {
            "kind": recipe.get("buff_kind", "harvest_multiplier"),
            "source": recipe_id,
            "multiplier": float(recipe.get("buff_multiplier", 1.0)),
            "remaining_ticks": float(recipe.get("buff_ticks", 0)),
            "remaining_sales": int(recipe.get("sale_uses", 0)),
            "rare_weight_multiplier": float(recipe.get("rare_weight_multiplier", 1)),
            "double_chance": float(recipe.get("double_chance", 0))
        }

    def buff_multiplier_for(self, kind):
        if self.active_buff.get("kind") == kind and float(self.active_buff.get("remaining_ticks", 0)) > 0:
            return float(self.active_buff.get("multiplier", 1.0))
        return 1.0

    def buff_text(self):
        if self.active_buff.get('kind')=='sale_boost' and self.active_buff.get('remaining_sales',0)>0:
            return f"Better sales, {self.active_buff['remaining_sales']} sales left"
        if self.active_buff.get('kind') == 'research_discount': return 'Research discount, next research'
        remaining = float(self.active_buff.get("remaining_ticks", 0))
        if remaining <= 0:
            return "No food effect"
        recipe = self.get_recipe_config(self.active_buff.get("source")) or {}
        return f"{recipe.get('buff_label', 'Food effect')}, {remaining:g} hours left"

    def tick_buff(self, cost):
        if self.active_buff.get("kind") in ("sale_boost", "research_discount"): return
        remaining = float(self.active_buff.get("remaining_ticks", 0))
        remaining = max(0, remaining - max(0, float(cost)))
        self.active_buff["remaining_ticks"] = remaining
        if remaining == 0:
            self.active_buff = dict(self.NO_EFFECT)

    def boost_rare_weights(self, weights, rare_keys):
        result=dict(weights)
        if self.active_buff.get('kind')=='rare_find' and self.active_buff.get('remaining_ticks',0)>0:
            multiplier=self.active_buff.get('rare_weight_multiplier',1)
            for key in rare_keys:result[key]=result.get(key,0)*multiplier
        return result

    def loot_amount(self, amount):
        if self.active_buff.get('kind')=='double_loot' and self.active_buff.get('remaining_ticks',0)>0:
            if random.random()<self.active_buff.get('double_chance',0):return amount*2
        return amount

    def sale_price(self, price):
        if self.active_buff.get('kind')=='sale_boost' and self.active_buff.get('remaining_sales',0)>0:
            return math.floor(price*self.active_buff.get('multiplier',1))
        return price

    def consume_sale(self):
        if self.active_buff.get('kind')=='sale_boost' and self.active_buff.get('remaining_sales',0)>0:
            self.active_buff['remaining_sales']-=1
            if not self.active_buff['remaining_sales']:
                self.active_buff={'kind':None,'source':None,'multiplier':1,'remaining_ticks':0}

    def research_price(self, price):
        return int(price * self.active_buff.get('multiplier', 1)) if self.active_buff.get('kind') == 'research_discount' else int(price)

    def consume_research_discount(self):
        if self.active_buff.get('kind') == 'research_discount': self.active_buff = dict(self.NO_EFFECT)

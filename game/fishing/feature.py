"""Fishing at the lake: a hidden daily target, distance zones, rarity rolls, rod wear, fish and rod prices.

Engine attributes (save format): fishing_target, fishing_last_catch, fishing_attempts, rod_casts,
rod_catches. Resource keys created and owned: resources["fishing_rod"], resources["fish"].
Shared state written: resources["coin"]; spends time. Distances and rarity tables stay server-side.
"""
import math
import random

from engine.core import order
from engine.core.registry import Feature


class Fishing(Feature):
    name = "fishing"

    def register(self, reg):
        reg.owns("fishing_target", "fishing_last_catch", "fishing_attempts", "rod_casts", "rod_catches")
        reg.page("fishing", objects=self.page_objects, scene=self.draw_lake, press=self.cast, single_press=True,
                 arrival=self.arrival, detail=self.detail)
        reg.state("fishing", self.public_state)
        reg.contribute("inventory.items", self.inventory_items, order=order.InventoryItems.FISHING)
        reg.shop_item("fishing_rod", self.buy_rod)
        reg.shop_item("fish", sell=self.sell_fish)
        reg.contribute("shop.buy_items", lambda: [("fishing_rod", "fishing_rod", "Fishing rod", self.engine.resources.get("fishing_rod",0), self.rod_price())],
                       order=order.ShopBuyItems.FISHING)
        reg.contribute("shop.sell_items", self.shop_sell_rows, order=order.ShopSellItems.FISHING)
        reg.on("reset", self.reset, order=order.Reset.FISHING)
        reg.on("start_of_day", self.new_day, order=order.StartOfDay.FISHING)
        reg.save_fields(defaults=("fishing_target", "fishing_last_catch", "fishing_attempts", "rod_casts", "rod_catches"),
                        migrate=self.migrate)
        reg.expose("fishing_config", self.config)
        reg.expose("cast_fishing", self.cast)
        reg.expose("get_fish_price", self.fish_price)

    def config(self):
        return self.engine.config['fishing']

    def reset(self):
        e = self.engine
        e.resources['fishing_rod'] = min(1, max(0, int(e.config.get('resources', {}).get('fishing_rod', 0))))
        e.resources['fish'] = dict(e.config.get('resources', {}).get('fish', {}))
        e.fishing_last_catch = None
        e.fishing_attempts = 0
        e.rod_casts = 0
        e.rod_catches = 0
        self.new_target()

    def new_day(self):
        self.new_target()
        self.engine.fishing_last_catch = None

    @staticmethod
    def migrate(state, fresh):
        # Pre-fishing saves get an empty rod and fish bag without replacing existing progress.
        state['resources'].setdefault('fishing_rod', 0)
        state['resources'].setdefault('fish', {})

    def arrival(self):
        return "Fishing lake." if self.engine.resources.get("fishing_rod") else "Fishing lake. Buy a fishing rod"

    def detail(self):
        if self.engine.resources.get("fishing_rod"):
            return "Fishing lake. Follow the water sound. Tap to fish."
        return "Fishing lake. Buy a fishing rod to catch fish."

    def inventory_items(self):
        e = self.engine
        entries = [{"id":"fishing_rod", "label":"Fishing rod", "count":e.resources.get("fishing_rod",0), "kind":"tool", "action":""}]
        for key, fish in self.config()['fish'].items():
            entries.append({"id":key, "label":fish['label'], "count":e.resources['fish'].get(key,0), "kind":"fish", "action":""})
        return entries

    def shop_sell_rows(self):
        e = self.engine
        return [("fish", key, fish['label'], e.resources['fish'].get(key,0), self.fish_price(key))
                for key, fish in self.config()['fish'].items() if e.resources['fish'].get(key,0)>0]

    def sell_fish(self, item_id):
        e = self.engine
        if item_id not in self.config()['fish']:
            return None
        if e.resources['fish'].get(item_id,0) < 1:
            return e.response(tts="No fish to sell.")
        fish = self.config()['fish'][item_id]
        price, label = self.fish_price(item_id), fish['label']
        e.add_resource('fish', -1, item=item_id)
        return price, label

    def rod_price(self):
        return int(self.config().get('rod_price',100))

    def fish_price(self, fish_id):
        fish=self.config()['fish'][fish_id]
        cfg=self.config()
        if fish['grade'] in cfg.get('fish_sell_prices', {}):
            return int(cfg['fish_sell_prices'][fish['grade']])
        return self.engine.get_mineral_price(cfg.get('fish_price_base_mineral','copper'))+int(cfg.get('fish_price_grade_bonus',{}).get(fish['grade'],0))

    def lake_geometry(self):
        pad = self.engine.dotpad
        return {'x': (pad.width-1)/2, 'y': (pad.height-1)/2,
                'rx': (pad.width-5)/2, 'ry': (pad.height-5)/2}

    def inside_lake(self, x, y):
        g = self.lake_geometry()
        return ((x-g['x'])/g['rx'])**2 + ((y-g['y'])/g['ry'])**2 < 1

    def new_target(self):
        g = self.lake_geometry()
        angle, radius = random.uniform(0, math.tau), math.sqrt(random.random())*.7
        self.engine.fishing_target = [g['x']+math.cos(angle)*g['rx']*radius,
                                      g['y']+math.sin(angle)*g['ry']*radius]

    def page_objects(self):
        e = self.engine
        exit_left = e.back_arrow('fishing_exit_left', 'Village', 'travel:town')
        exit_left.update(direction='left', x=3, y=e.dotpad.height-5)
        exit_right = e.back_arrow('fishing_exit_right', 'Village', 'travel:town')
        exit_right.update(direction='right', x=e.dotpad.width-4, y=5)
        return [exit_left, exit_right]

    def draw_lake(self):
        g = self.lake_geometry()
        for i in range(720):
            angle = math.tau*i/720
            self.engine.dotpad.set_dot(round(g['x']+g['rx']*math.cos(angle)),
                                       round(g['y']+g['ry']*math.sin(angle)))

    def public_state(self):
        e = self.engine
        active = e.current_page == 'fishing' and not (e.paused or e.day_ended or e.sleep_until is not None)
        return {'active': active, 'lake': self.lake_geometry(),
                'target': list(e.fishing_target) if active else None,
                'attempts': e.fishing_attempts,
                'last_catch': dict(e.fishing_last_catch) if e.fishing_last_catch else None}

    def zone(self, x, y):
        e = self.engine
        d = math.hypot(x-e.fishing_target[0], y-e.fishing_target[1])
        cfg = self.config()
        middle_radius = math.sqrt(e.dotpad.width*e.dotpad.height*cfg.get('middle_area_fraction',1/6)/math.pi)
        return 'near' if d <= cfg['near_radius'] else 'middle' if d <= middle_radius else 'far'

    def cast(self, x, y):
        e = self.engine
        if e.current_page != 'fishing' or e.paused or e.sleep_until is not None:
            return e.response()
        if e.day_ended:
            return e.night_only_response()
        if not e.resources.get('fishing_rod'):
            return e.response(tts='Fishing rod required. Buy at the shop.', sfx='error')
        if not self.inside_lake(x, y):
            return e.response(tts='Cast inside the lake.', sfx='error')
        zone = self.zone(x, y)
        cfg = self.config()
        weights = e.boost_rare_weights(cfg['zone_weights'][zone], ('high',))
        grade = random.choices(list(weights), weights=list(weights.values()), k=1)[0]
        e.fishing_attempts += 1
        events = []
        if grade == 'miss':
            e.registry.run('activity', 'fishing_miss')
            e.fishing_last_catch = {'id': None, 'label': 'No catch', 'attempt': e.fishing_attempts}
            text = 'No catch. Try another spot.'
        else:
            candidates = [key for key, fish in cfg['fish'].items() if fish['grade'] == grade]
            fish_id = random.choice(candidates)
            label = cfg['fish'][fish_id]['label']
            amount = e.loot_amount(1, activity="fishing")
            e.resources['fish'][fish_id] = e.resources['fish'].get(fish_id, 0)+amount
            e.registry.run('activity', 'fishing', label, amount)
            e.fishing_last_catch = {'id': fish_id, 'label': label, 'attempt': e.fishing_attempts}
            text = f'{label} {amount} caught.' + (' Bonus.' if amount>1 else '')
            events.append({'kind':'one_shot_group','sounds':['splash','shine'] if grade=='high' else ['splash']})
        e.rod_casts += 1
        if grade != 'miss':
            e.rod_catches += 1
            chance = min(1, max(0,e.rod_catches-cfg.get('rod_safe_catches',4))*cfg.get('rod_break_increment',.1))
            if chance>0 and random.random()<chance:
                e.resources['fishing_rod']=0
                e.rod_casts=0
                e.rod_catches=0
                text += ' Fishing rod broken. Buy another at the shop.'
                events.append(e.item_destroyed_event('fishing_rod'))
        self.new_target()
        result = e.consume_time('fish')
        e.render()
        if result['night']: return e.night_response(prefix=text, sound_events=events)
        return e.response(tts=text, sound_events=events, sfx='fishing_miss' if grade == 'miss' else None)

    def buy_rod(self, item_id):
        if item_id != "fishing_rod":
            return None
        e = self.engine
        if e.resources.get('fishing_rod', 0):
            return e.response(tts='Only one fishing rod allowed.', sfx='error')
        price = e.market_price(self.rod_price(), "fishing_rod", "buy")
        if e.resources['coin'] < price:
            return e.response(tts=f'Not enough gold. Need {price} gold for Fishing rod.', sfx='error')
        e.add_resource('coin', -price)
        e.resources['fishing_rod'] = 1
        e.rod_casts = 0
        e.rod_catches = 0
        e.clear_hover()
        e.render()
        return e.response(tts=f"Fishing rod bought. Gold left: {e.resources['coin']} gold", sound_events=[{'kind':'one_shot','sound':'coin'}])

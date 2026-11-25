"""Shop: the shop counter page, paged buy and sell lists, market prices and payment.

Engine attributes (save format): shop_page. shop_page_count is a derived cache set in the
engine's __init__ (excluded from saves) and updated here.
Declares slots shop.buy_items and shop.sell_items; features add rows and handle their own item
kinds with reg.shop_item().
"""
import math

from engine.core import order
from engine.core.registry import Feature


class Shop(Feature):
    name = "shop"

    def register(self, reg):
        reg.owns("shop_page")
        reg.slot("shop.buy_items", "Buy rows: (kind, item_id, label, owned_count, base_price). Prices pass through "
                                   "the weekly market unless the kind is registered with market_price=False.")
        reg.slot("shop.sell_items", "Sell rows: (kind, item_id, label, owned_count, base_price), owned items only.")
        reg.page("shop_choice", objects=self.choice_objects, scene=self.draw_scene, icon_grid=True,
                 detail=lambda: "Shop. Sell, General goods, Tools, Calendar.",
                 panel=lambda: (0, 1, "shop"))
        reg.page("shop_buy", objects=lambda: self.build_objects(self.purchase_rows(False), "buy"),
                 icon_grid=True, panel=lambda: (self.engine.shop_page, self.engine.shop_page_count, "buy"))
        reg.page("shop_tools", name="Tools", objects=lambda: self.build_objects(self.purchase_rows(True), "buy"),
                 icon_grid=True, panel=lambda: (self.engine.shop_page, self.engine.shop_page_count, "buy"))
        reg.page("shop_sell", objects=lambda: self.build_objects(self.engine.registry.collect("shop.sell_items"), "sell"),
                 icon_grid=True, panel=lambda: (self.engine.shop_page, self.engine.shop_page_count, "sell"))
        reg.action("open_shop", lambda arg, obj: self.open())
        reg.action("return_shop_choice", lambda arg, obj: self.return_to_choice())
        reg.action("shop_mode:", lambda arg, obj: self.open_mode(arg))
        reg.action("shop_page:", self.turn_page)
        reg.action("buy:", lambda arg, obj: self.buy(*arg.split(":", 1)))
        reg.action("sell:", lambda arg, obj: self.sell(*arg.split(":", 1)))
        reg.icon("shop_npc", layout_order=0)
        reg.icon("shop_choice", symbol=lambda obj: obj.get('choice'))
        reg.icon("shop_item", pattern=self.item_pattern, symbol=lambda obj: self.engine.icons.category(obj.get('shop_kind')))
        reg.object_tts("shop_item", self.item_tts)
        reg.object_tts("shop_hitbox", lambda obj: str(obj.get("label") or "Object").strip())
        reg.hover_sfx("shop_npc", "hover_shop")
        reg.hover_sfx("shop_choice", "hover_shop")
        reg.hover_sfx("shop_item", "hover_shop_item")
        reg.on("reset", self.reset, order=order.Reset.SHOP)
        reg.expose("open_shop", self.open)
        reg.expose("buy_shop_item", self.buy)
        reg.expose("sell_shop_item", self.sell)

    def item_pattern(self,obj):
        # Prize draw: a 7x5 starburst (open lines, unlike the closed coin) that leaves one lowered pin
        # inside the 11x9 icon frame; the old 7x7 wheel touched the frame top and bottom.
        if obj.get('shop_kind')=='roulette':return ('1001001','0101010','1111111','0101010','1001001')
        if obj.get('shop_kind')=='animal':
            pattern=self.engine.registry.icon_patterns.get('animal_icon')
            if pattern:return pattern({'animal':obj['item_id']})
        return ()

    def reset(self):
        e = self.engine
        e.shop_page = 0
        e.shop_page_count = 1

    @staticmethod
    def item_tts(obj):
        """shop_item.count is the player's quantity; price is the current market rate."""
        label = str(obj.get("label") or "Object").strip()
        price = obj.get("price")
        owned = obj.get("count")
        info = []
        if price is not None:
            info.append(f"{price} gold")
        if owned is not None:
            info.append(f"owned {owned}")
        return f"{label}, {', '.join(info)}." if info else label

    def turn_page(self, arg, obj):
        e = self.engine
        if e.current_page not in ("shop_buy", "shop_tools", "shop_sell"):
            return e.response()
        e.shop_page += int(arg)
        e.clear_hover()
        e.render()
        return e.response(tts="Next page" if ("shop_page:" + arg).endswith(":1") else "Previous page")

    def buy(self, kind, item_id):
        buyer = self.engine.registry.shop_buyers.get(kind)
        if buyer:
            e = self.engine
            before = e.resource('coin')
            result = buyer(item_id)
            if result is not None:
                if e.resource('coin') < before and kind != 'roulette':
                    e.consume_purchase()
                    # Buyers build a response before the successful-use counter changes.
                    e.render()
                    result["state"] = e.get_state()
                return result
        return self.engine.response(tts="Item unavailable.", sfx="error")

    def sell(self, kind, item_id):
        e = self.engine
        seller = e.registry.shop_sellers.get(kind)
        outcome = seller(item_id) if seller else None
        if outcome is None:
            return e.response(tts="Cannot sell this item.", sfx="error")
        if isinstance(outcome, dict):
            return outcome
        price, label = outcome
        price = e.market_price(price, kind, "sell")
        e.add_resource("coin", price)
        e.consume_sale()
        e.clear_hover()
        e.render()
        return e.response(tts=f"{label} sold. Gold left: {e.resources['coin']} gold", sfx="shop_sell", sound_events=[{"kind": "one_shot", "sound": "coin"}] if price > 0 else [])


    def choice_objects(self):
        e = self.engine
        base = [
            {
                "id": "shop_sell_choice", "type": "shop_choice", "choice": "sell",
                "x": 15, "y": 6, "width": 12, "height": 10, "hit_width": 10, "hit_height": 8,
                "label": "Sell", "tts": "Sell.", "action": "shop_mode:sell"
            },
            {
                "id": "shop_buy_choice", "type": "shop_choice", "choice": "buy",
                "x": 30, "y": 6, "width": 12, "height": 10, "hit_width": 10, "hit_height": 8,
                "label": "General goods", "tts": "General goods.", "action": "shop_mode:buy"
            },
            {"id":"shop_tools_choice", "type":"shop_choice", "choice":"tools", "x":38,"y":6,
             "width":12,"height":10,"hit_width":10,"hit_height":8,
             "label":"Tools", "tts":"Tools.", "action":"shop_mode:tools"},
            {
                "id": "shop_calendar", "type": "calendar_button",
                "x": 45, "y": 6, "width": 12, "height": 10, "hit_width": 10, "hit_height": 8,
                "label": "Calendar", "tts": "Calendar. Weekly offers.", "action": "open_calendar"
            }
        ]
        return base + self.choice_spatial_objects() + [self.engine.back_arrow("shop_choice_back", "Back to village", "return_scene")]

    def choice_spatial_objects(self):
        e = self.engine
        return [
            dict(id='shop_scene_roulette',type='shop_hitbox',skip_grid=True,x=44,y=19,width=9,height=9,hit_width=9,hit_height=9,label='Prize draw',tts='Prize draw. 200 gold.',action='buy:roulette:draw'),
            dict(id='shop_scene_calendar', type='shop_hitbox', skip_grid=True,
                 x=11, y=20, width=9, height=9, hit_width=11, hit_height=11,
                 label='Calendar', tts='Calendar. Weekly offers.', action='open_calendar'),
            dict(id='shop_scene_keeper', type='shop_hitbox', skip_grid=True,
                 x=30, y=19, width=9, height=8, hit_width=11, hit_height=9,
                 label='Shopkeeper', tts='Shopkeeper. Select Sell, General goods, Tools, or Calendar.', action='open_calendar'),
            dict(id='shop_scene_sell', type='shop_hitbox', skip_grid=True,
                 x=16, y=30, width=12, height=11, hit_width=12, hit_height=11,
                 label='Sell', tts='Sell.', action='shop_mode:sell'),
            dict(id='shop_scene_buy', type='shop_hitbox', skip_grid=True,
                 x=30, y=30, width=12, height=11, hit_width=12, hit_height=11,
                 label='General goods', tts='General goods.', action='shop_mode:buy'),
            dict(id='shop_scene_tools', type='shop_hitbox', skip_grid=True,
                 x=44,y=30,width=12,height=11,hit_width=12,hit_height=11,
                 label='Tools',tts='Tools.',action='shop_mode:tools'),
            dict(id='shop_scene_exit', type='shop_hitbox', skip_grid=True,
                 x=2, y=26, width=5, height=7, hit_width=7, hit_height=9,
                 label='Back to village', tts='Back to village.', action='return_scene'),
        ]

    # Shop interior drawn to the tactile design rules (README.md): raised outlines with lowered
    # interiors, at least one lowered pin between neighbours, and one raised symbol per counter.
    CALENDAR = ('011000110',
                '111111111',
                '100000001',
                '101010101',
                '100000001',
                '101010101',
                '100000001',
                '111111111')
    # Head joined to the shoulders by a neck pin, so the shopkeeper is felt as one figure.
    KEEPER = ('000111000',
              '001000100',
              '001000100',
              '000111000',
              '000010000',
              '011111110',
              '100000001',
              '111111111')
    WHEEL = ('000111000',
             '011000110',
             '010000010',
             '100010001',
             '100111001',
             '100010001',
             '010000010',
             '011000110',
             '000111000')
    # (centre x, width, symbol): Sell shows a coin, General goods a bag, Tools a tool.
    # Every counter is 12 pins wide (10 inside) so the 7-pin bag keeps one lowered pin on each side.
    COUNTERS = ((16, 12, 'coin'), (30, 12, 'bag'), (44, 12, 'tool'))

    def draw_scene(self):
        e = self.engine
        pad = e.dotpad
        e.draw_room(doors=('left',))
        e.draw_solid_pattern(11, 20, self.CALENDAR)
        e.draw_solid_pattern(30, 19, self.KEEPER)
        e.draw_solid_pattern(44, 19, self.WHEEL)
        # Three separate counters (outline boxes, rows 25-35) matching the lower hit regions.
        for cx, width, symbol in self.COUNTERS:
            left = cx - width // 2
            pad.draw_box(left + (width - 1) / 2, 30, width - 1, 10)
            e.draw_icon_pattern(cx, 30, e.icons.PATTERNS[symbol])

    def open(self):
        e = self.engine
        e.registry.run("close_dialogue")
        if e.current_location != "town":
            e.current_location = "town"
        e.set_page("shop_choice")
        e.clear_hover()
        e.render()
        return e.response(tts="Shop.", sfx="shop_open", sound_events=[{"kind": "one_shot", "sound": "door"}])

    def return_to_choice(self):
        e = self.engine
        e.set_page("shop_choice")
        e.shop_page = 0
        e.clear_hover()
        e.render()
        return e.response(tts="Shop.", sfx="open_page")

    def open_mode(self, mode):
        e = self.engine
        e.shop_page = 0
        if mode == "sell":
            e.set_page("shop_sell")
            text = "Sell."
        elif mode == "tools":
            e.set_page("shop_tools")
            text = "Tools."
        else:
            e.set_page("shop_buy")
            text = "General goods."
        e.clear_hover()
        e.render()
        return e.response(tts=text, sfx="open_page")

    def purchase_rows(self, tools):
        kinds={'pickaxe','fishing_rod','animal','flower_seed'}
        rows=[row for row in self.engine.registry.collect('shop.buy_items') if (row[0] in kinds)==tools]
        return sorted(rows,key=lambda row:row[0]!='roulette')

    def build_objects(self, entries, mode):
        e = self.engine
        page_size = 12
        pages = max(1, math.ceil(len(entries) / page_size))
        e.shop_page_count = pages
        e.shop_page = max(0, min(e.shop_page, pages - 1))
        objects = []
        for i, (kind, item_id, label, count, price) in enumerate(entries[e.shop_page * page_size:(e.shop_page + 1) * page_size]):
            price = price if kind == "roulette" else e.purchase_price(price) if kind in e.registry.fixed_price_kinds and mode == "buy" else price if kind in e.registry.fixed_price_kinds else e.market_price(price, kind, mode)
            x, y = (9, 23, 37, 51)[i % 4], (5, 15, 25)[i // 4]
            text = f"{label}, {price} gold. stock {count} " if mode == "buy" else f"{label}, stock {count}. Sell {price} gold"
            owned_text = e.registry.shop_owned_texts.get(kind)
            if owned_text and owned_text(count):
                text = owned_text(count)
            objects.append({"id": f"shop_{mode}_{kind}_{item_id}", "type": "shop_item", "shop_kind": kind, "item_id": item_id,
                            "x": x, "y": y, "width": 10, "height": 6, "hit_width": 10, "hit_height": 6,
                            "count": int(count), "price": int(price), "label": label, "tts": text, "action": f"{mode}:{kind}:{item_id}"})
        objects.append(e.back_arrow(f"shop_{mode}_back", "Back to shop", "return_shop_choice"))
        for delta, x, direction, label in [(-1, 30, "left", "Previous page"), (1, 51, "right", "Next page")]:
            if 0 <= e.shop_page + delta < pages:
                objects.append({"id": f"shop_page_{direction}", "type": "arrow", "x": x, "y": 35, "direction": direction,
                                "size": 2, "hit_width": 11, "hit_height": 7, "label": label, "action": f"shop_page:{delta}"})
        if not entries:
            objects.append({"id": "shop_empty", "type": "box", "x": 30, "y": 16, "width": 20, "height": 8,
                            "label": "Nothing to sell", "tts": "Nothing to sell.", "action": ""})
        return objects

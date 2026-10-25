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
                 detail=lambda: "Shop. Sell, Buy, Calendar, or Ask Rowan for advice.",
                 panel=lambda: (0, 1, "shop"))
        reg.page("shop_buy", objects=lambda: self.build_objects(self.engine.registry.collect("shop.buy_items"), "buy"),
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
        reg.icon("shop_item", symbol=lambda obj: self.engine.icons.category(obj.get('shop_kind')))
        reg.object_tts("shop_item", self.item_tts)
        reg.object_tts("shop_hitbox", lambda obj: str(obj.get("label") or "Object").strip())
        reg.hover_sfx("shop_npc", "hover_shop")
        reg.hover_sfx("shop_choice", "hover_shop")
        reg.hover_sfx("shop_item", "hover_shop_item")
        reg.on("reset", self.reset, order=order.Reset.SHOP)
        reg.expose("open_shop", self.open)
        reg.expose("buy_shop_item", self.buy)
        reg.expose("sell_shop_item", self.sell)

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
        if e.current_page not in ("shop_buy", "shop_sell"):
            return e.response()
        e.shop_page += int(arg)
        e.clear_hover()
        e.render()
        return e.response(tts="Next page" if ("shop_page:" + arg).endswith(":1") else "Previous page")

    def buy(self, kind, item_id):
        buyer = self.engine.registry.shop_buyers.get(kind)
        if buyer:
            result = buyer(item_id)
            if result is not None: return result
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
                "label": "Buy", "tts": "Buy.", "action": "shop_mode:buy"
            },
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
            dict(id='shop_scene_calendar', type='shop_hitbox', skip_grid=True,
                 x=11, y=20, width=9, height=9, hit_width=11, hit_height=11,
                 label='Calendar', tts='Calendar. Weekly offers.', action='open_calendar'),
            dict(id='shop_scene_keeper', type='shop_hitbox', skip_grid=True,
                 x=30, y=19, width=9, height=8, hit_width=11, hit_height=9,
                 label='Shopkeeper', tts='Shopkeeper. Select Sell, Buy, or Calendar.', action='open_calendar'),
            dict(id='shop_scene_sell', type='shop_hitbox', skip_grid=True,
                 x=20, y=30, width=13, height=9, hit_width=15, hit_height=11,
                 label='Sell counter', tts='Sell.', action='shop_mode:sell'),
            dict(id='shop_scene_buy', type='shop_hitbox', skip_grid=True,
                 x=40, y=30, width=13, height=9, hit_width=15, hit_height=11,
                 label='Buy counter', tts='Buy.', action='shop_mode:buy'),
            dict(id='shop_scene_exit', type='shop_hitbox', skip_grid=True,
                 x=2, y=26, width=5, height=7, hit_width=7, hit_height=9,
                 label='Back to village', tts='Back to village.', action='return_scene'),
        ]

    def draw_scene(self):
        e = self.engine
        pad = e.dotpad
        pad.draw_line(0, 12, pad.width - 1, 12)
        pad.draw_line(0, 13, pad.width - 1, 13)

        pad.draw_line(4, 39, 55, 39)
        for y in range(13, 40):
            if not (24 <= y <= 28):
                pad.set_dot(4, y)
            pad.set_dot(55, y)
        for dx in (3, 4, 5):
            pad.set_dot(dx, 23)
            pad.set_dot(dx, 29)
        e.draw_icon_pattern(1, 26, (
            '001',
            '011',
            '111',
            '011',
            '001',
        ))

        draw_solid_pattern = e.draw_solid_pattern

        draw_solid_pattern(11, 20, (
            '.1100011.',
            '111111111',
            '101010101',
            '111111111',
            '101010101',
            '111111111',
            '101010101',
            '111111111',
        ))

        draw_solid_pattern(30, 19, (
            '..11111..',
            '.1111111.',
            '..10101..',
            '..11111..',
            '.1111111.',
            '111111111',
            '111010111',
            '111111111',
        ))

        for y in range(25, 36):
            for x in range(13, 48):
                pad.set_dot(x, y, 1)
        for x in range(14, 47):
            pad.set_dot(x, 26, 0)
        for y in range(26, 35):
            pad.set_dot(30, y, 0)

        draw_solid_pattern(21, 30, (
            '11000011',
            '10111101',
            '11000111',
            '11110011',
            '10111011',
            '11000111',
        ))

        draw_solid_pattern(39, 30, (
            '10000111',
            '10110011',
            '10000111',
            '10110011',
            '10000111',
            '11111111',
        ))

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
        else:
            e.set_page("shop_buy")
            text = "Buy."
        e.clear_hover()
        e.render()
        return e.response(tts=text, sfx="open_page")

    def build_objects(self, entries, mode):
        e = self.engine
        page_size = 12
        pages = max(1, math.ceil(len(entries) / page_size))
        e.shop_page_count = pages
        e.shop_page = max(0, min(e.shop_page, pages - 1))
        objects = []
        for i, (kind, item_id, label, count, price) in enumerate(entries[e.shop_page * page_size:(e.shop_page + 1) * page_size]):
            price = price if kind in e.registry.fixed_price_kinds else e.market_price(price, kind, mode)
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

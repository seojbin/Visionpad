"""Mining: daily rocks at the mine, pickaxe wear, mineral loot and mineral prices.

Engine attributes (save format): mine_rocks, _pickaxe_hits.
Shared state written: resources (minerals, pickaxe, coin), hover_object_id; spends time.
Provides engine.get_mineral_price() (shop, seafood). Uses engine.market_price() (village),
buff_multiplier_for() (cooking, core), boost_rare_weights() and loot_amount() (seafood).
"""
import math
import random

from visionpad.core import order
from visionpad.core.registry import Feature


class Mining(Feature):
    name = "mining"

    def register(self, reg):
        reg.owns("mine_rocks", "_pickaxe_hits")
        reg.page("mine", objects=self.page_objects, single_press=True, guidance=self.guidance,
                 arrival=self.arrival, detail=self.detail)
        reg.action("mine_hit:", lambda arg, obj: self.hit_rock(arg))
        reg.renderer("mine_rock", self.draw_rock)
        reg.hit_test("mine_rock", self.rock_contains)
        reg.spectator("rocks", lambda objects: [{k: r[k] for k in ('id', 'left', 'top', 'width', 'height', 'hits')}
                                                for r in self.engine.mine_rocks])
        reg.contribute("inventory.items", self.inventory_items, order=order.InventoryItems.MINING)
        reg.shop_item("pickaxe", lambda item_id: self.buy_item("pickaxe", item_id))
        reg.shop_item("mineral", lambda item_id: self.buy_item("mineral", item_id))
        reg.on("reset", self.reset, order=order.Reset.MINING)
        reg.on("start_of_day", self.regenerate, order=order.StartOfDay.MINING)
        reg.expose("get_mineral_price", self.mineral_price)
        reg.expose("hit_mine_rock", self.hit_rock)

    def reset(self):
        self.engine._pickaxe_hits = 0
        self.regenerate()

    def arrival(self):
        return "Mine." if self.engine.resources["pickaxe"] else "Mine. Buy a pickaxe"

    def detail(self):
        e = self.engine
        return "Mine. Tap rocks to break them." if e.resources.get("pickaxe") else "Mine. Buy a pickaxe to break rocks."

    def guidance(self):
        targets = [{"id": obj["id"], "x": obj["x"], "y": obj["y"]}
                   for obj in self.page_objects() if obj["type"] == "mine_rock"]
        return "mine", targets, 0, len(targets)

    def inventory_items(self):
        e = self.engine
        return [{"id": item_id, "label": label, "count": e.resources[item_id], "kind": item_id, "action": ""}
                for item_id, label in [("pickaxe", "Pickaxe"), ("copper", "Copper"), ("iron", "Iron"), ("diamond", "Diamond")]]

    @staticmethod
    def rock_contains(obj, x, y):
        left, top = obj["x"] - obj["width"] // 2, obj["y"] - obj["height"] // 2
        return left <= x < left + obj["width"] and top <= y < top + obj["height"]

    def page_objects(self):
        e = self.engine
        objects = []
        for rock in e.mine_rocks:
            objects.append({"id": rock["id"], "type": "mine_rock",
                            "x": rock["left"] + rock["width"] // 2,
                            "y": rock["top"] + rock["height"] // 2,
                            "width": rock["width"], "height": rock["height"],
                            "hits": rock.get("hits", 0),
                            "label": "Rock", "tts": "Rock. Tap to break." if e.resources["pickaxe"] else "Pickaxe required.",
                            "action": f"mine_hit:{rock['id']}"})
        exit_left = e.back_arrow("mine_exit_left", "Village", "travel:town")
        exit_left.update(x=3, y=e.dotpad.height-5, direction="left", size=3, hit_width=7, hit_height=9)
        exit_right = e.back_arrow("mine_exit_right", "Village", "travel:town")
        exit_right.update(x=e.dotpad.width-4, y=5, direction="right", size=3, hit_width=7, hit_height=9)
        objects.extend([exit_left, exit_right])
        return objects

    def mineral_price(self, mineral, buying=False):
        e = self.engine
        prices = sorted(float(s.get("crop_price", 1)) for s in e.config.get("seeds", {}).values()) or [1]
        mid = len(prices) // 2
        base = prices[mid] if len(prices) % 2 else (prices[mid - 1] + prices[mid]) / 2
        cfg = e.config.get("mine", {})
        price = int(math.ceil(base * float(cfg.get("mineral_sell_multipliers", {}).get(mineral, 1))))
        price += int(cfg.get("mineral_sell_price_bonus", 3))
        return int(math.ceil(price * float(cfg.get("mineral_buy_multiplier", 2)))) if buying else price

    def regenerate(self):
        e = self.engine
        cfg = e.config.get("mine", {})
        width, height = e.dotpad.width, e.dotpad.height
        rw, rh = int(cfg.get("rock_width", 10)), int(cfg.get("rock_height", 10))
        gap = max(5, int(cfg.get("rock_gap", 5)))
        if rw < 1 or rh < 1 or rw > width or rh > height:
            raise ValueError("Rock size must fit the pad.")
        columns, rows = (width + gap) // (rw + gap), (height + gap) // (rh + gap)
        slack_x = width - (columns * rw + (columns - 1) * gap)
        slack_y = height - (rows * rh + (rows - 1) * gap)
        origin_y = random.randint(0, slack_y)
        candidates = []
        for row in range(rows):
            origin_x = random.randint(0, slack_x)
            top = origin_y + row * (rh + gap)
            for col in range(columns):
                left = origin_x + col * (rw + gap)
                candidates.append((left, top))
        random.shuffle(candidates)
        limit = max(0, min(7, int(cfg.get("daily_rock_limit", 7))))
        e.mine_rocks = [
            {"id": f"mine_rock_{e.day}_{i}", "left": x, "top": y,
             "width": rw, "height": rh, "hits": 0}
            for i, (x, y) in enumerate(candidates[:limit])
        ]

    def draw_rock(self, obj):
        e = self.engine
        width, height = int(obj["width"]), int(obj["height"])
        left, top = obj["x"] - width // 2, obj["y"] - height // 2
        hits = max(0, int(obj.get("hits", 0)))
        hits_to_break = max(1, int(e.config.get("mine", {}).get("hits_to_break", 3)))
        stage = min(2, (2 * hits) // max(1, hits_to_break - 1))
        for row in range(height):
            for col in range(width):
                border = col < 2 or col >= width - 2 or row < 2 or row >= height - 2
                grid_x, grid_y = (col - 2) % 3 == 0, (row - 2) % 3 == 0
                filled = stage == 0 or (stage == 1 and (grid_x or grid_y)) or (grid_x and grid_y)
                if border or filled:
                    e.dotpad.set_dot(left + col, top + row)

    def hit_rock(self, rock_id):
        e = self.engine
        if e.current_page != "mine" or e.paused or e.day_ended:
            return e.response()
        rock = next((r for r in e.mine_rocks if r["id"] == rock_id), None)
        if rock is None:
            return e.response()
        e.hover_object_id = rock_id
        if e.resources.get("pickaxe", 0) < 1:
            return e.response(tts="Pickaxe required. Buy at the shop.", sfx="error")
        cfg = e.config.get("mine", {})
        rock["hits"] += 1
        e._pickaxe_hits += 1
        destroyed = rock["hits"] >= int(cfg.get("hits_to_break", 3))
        text = ""
        events = []
        if destroyed:
            level = e.research_levels.get("mineral_luck", 0)
            research = e.config.get("research", {}).get("mineral_luck", {})
            weights = dict(cfg.get("loot_weights", {"diamond": 1, "iron": 15, "copper": 34, "stone": 50}))
            bonus = float(research.get("diamond_weight_per_level", 1)) * level
            weights["diamond"] += bonus
            weights["stone"] = max(0, weights["stone"] - bonus)
            weights = e.boost_rare_weights(weights, ("iron", "diamond"))
            mineral = random.choices(list(weights), weights=list(weights.values()), k=1)[0]
            doubled = random.random() < min(1, level * float(research.get("double_drop_chance_per_level", .15)))
            amount = e.loot_amount(2 if doubled else 1)
            doubled = amount > 1
            e.add_resource(mineral, amount)
            e.registry.run("activity", "mining", e.MINERAL_LABELS[mineral], amount)
            e.mine_rocks.remove(rock)
            text = f"{e.MINERAL_LABELS[mineral]} {amount} collected." + (". Bonus." if doubled else "")
        else:
            events.append({"kind": "one_shot", "sound": "pickaxe",
                           "progress": rock["hits"] / max(1, int(cfg.get("hits_to_break", 3)))})
        safe_hits = int(cfg.get("pickaxe_safe_hits", 9))
        break_chance = min(1, max(0, e._pickaxe_hits - safe_hits) * float(cfg.get("pickaxe_break_increment", .05)))
        break_chance *= e.buff_multiplier_for("pickaxe_protection")
        item_destroyed = break_chance > 0 and random.random() < break_chance
        if item_destroyed:
            e.resources["pickaxe"] = 0
            e._pickaxe_hits = 0
            text += (". " if text else "") + "Pickaxe broken. Buy another at the shop."
        if destroyed:
            fatigue = e.consume_time("mine")
            if fatigue["night"]:
                text += ". Night. Home now. Select the bed."
        e.render()
        if item_destroyed:
            reward_sound = ("shine" if mineral == "diamond" else "correct") if destroyed else None
            events = [e.item_destroyed_event("pickaxe", reward_sound, text if destroyed else None)]
        elif destroyed:
            events.append({"kind": "mining_loot", "sound": "shine" if mineral == "diamond" else "correct", "tts": text})
        return e.response(tts=None if destroyed else (text or None), sound_events=events)

    def buy_item(self, kind, item_id):
        e = self.engine
        if kind == "pickaxe":
            if e.resources["pickaxe"] >= 1:
                return e.response(tts="Only one pickaxe allowed.", sfx="error")
            price, label = e.get_pickaxe_price(), "Pickaxe"
        elif kind == "mineral" and item_id in ("stone", "copper", "iron"):
            price, label = self.mineral_price(item_id, buying=True), e.MINERAL_LABELS[item_id]
        else:
            return e.response(tts="Item unavailable.", sfx="error")
        price = e.market_price(price, kind, "buy")
        if e.resources["coin"] < price:
            return e.response(tts=f"Not enough gold. Need {price} gold for {label}.", sfx="error")
        e.add_resource("coin", -price)
        if kind == "pickaxe":
            e.resources["pickaxe"] = 1
            e._pickaxe_hits = 0
        else:
            e.add_resource(item_id, 1)
        e.clear_hover()
        e.render()
        return e.response(tts=f"{label} bought. Gold left: {e.resources['coin']} gold", sound_events=[{"kind": "one_shot", "sound": "coin"}])

    def draw_item(self, x, y, kind):
        """Unused before the split as well (AUDIT.md section 2.4); kept for parity."""
        e = self.engine
        x, y = int(x), int(y)
        if kind == "pickaxe":
            e.dotpad.draw_line(x - 3, y - 2, x + 3, y - 2)
            e.dotpad.draw_line(x, y - 2, x, y + 2)
        elif kind == "diamond":
            for a, b in [((-3, 0), (0, -2)), ((0, -2), (3, 0)), ((3, 0), (0, 2)), ((0, 2), (-3, 0))]:
                e.dotpad.draw_line(x+a[0], y+a[1], x+b[0], y+b[1])
        else:
            for row in range({"stone": 1, "copper": 2, "iron": 3}.get(kind, 1)):
                e.dotpad.draw_line(x-2, y-1+row, x+2, y-1+row)

"""F2 inventory: owned items on pages of twelve, food first; food can be used from here.

Engine attributes (save format): inventory_page, inventory_page_count.
Declares slot inventory.items. Until farming, cooking, mining and fishing are
extracted, their entries are contributed here at their order.InventoryItems
positions; each moves to its feature when that feature is extracted.
"""
from visionpad.core import order
from visionpad.core.registry import Feature


class Inventory(Feature):
    name = "inventory"

    def register(self, reg):
        reg.owns("inventory_page", "inventory_page_count")
        reg.slot("inventory.items", "Inventory entries: dicts with id, label, count, kind and optional "
                                    "action, seed_id, recipe_id, extra_tts. Gold is always shown; other "
                                    "entries only when count > 0.")
        reg.contribute("inventory.items", self.core_resource_items, order=order.InventoryItems.CORE_RESOURCES)
        reg.contribute("inventory.items", self.farming_items, order=order.InventoryItems.FARMING)
        reg.contribute("inventory.items", self.cooking_items, order=order.InventoryItems.COOKING)
        reg.contribute("inventory.items", self.fishing_items, order=order.InventoryItems.FISHING)
        reg.page("inventory", objects=self.page_objects, icon_grid=True,
                 menu_text=lambda: f'Inventory. {self.engine.resources["coin"]} gold.',
                 on_menu_open=self.first_page, navigate=self.navigate)
        reg.action("inventory_page:", self.turn_page)
        reg.state("inventory", lambda: {"page": self.engine.inventory_page + 1, "pages": self.engine.inventory_page_count})
        reg.on("reset", self.reset, order=order.Reset.INVENTORY)
        reg.expose("open_inventory", self.open)
        reg.expose("get_inventory_objects", self.page_objects)

    def reset(self):
        e = self.engine
        e.inventory_page = 0
        e.inventory_page_count = 1

    def first_page(self):
        self.engine.inventory_page = 0

    # ---- entries for core and not-yet-extracted features ----

    def core_resource_items(self):
        e = self.engine
        return [
            {"id": "coin", "label": "Gold", "count": int(e.resources.get("coin", 0)), "kind": "coin", "action": ""},
            {"id": "fertilizer", "label": "Fertilizer", "count": int(e.resources.get("fertilizer", 0)), "kind": "fertilizer", "action": ""},
            {"id": "wood", "label": "Wood", "count": int(e.resources.get("wood", 0)), "kind": "material", "action": ""},
            {"id": "stone", "label": "Stone", "count": int(e.resources.get("stone", 0)), "kind": "stone", "action": ""}
        ]

    def farming_items(self):
        e = self.engine
        entries = []
        for seed_id, seed_config in e.config.get("seeds", {}).items():
            entries.append({"id": f"seed_{seed_id}", "label": f"{seed_config.get('label', seed_id)} seeds", "count": int(e.resources["seeds"].get(seed_id, 0)), "kind": "seed", "seed_id": seed_id, "action": ""})
        for seed_id, seed_config in e.config.get("seeds", {}).items():
            entries.append({"id": f"crop_{seed_id}", "label": f"{seed_config.get('label', seed_id)} crops", "count": int(e.resources["crops"].get(seed_id, 0)), "kind": "crop", "seed_id": seed_id, "action": ""})
        return entries

    def cooking_items(self):
        e = self.engine
        entries = []
        for recipe_id, recipe in e.config.get("recipes", {}).items():
            count = int(e.resources["foods"].get(recipe_id, 0))
            if count <= 0 and e.inventory_hide_zero_items:
                continue
            entries.append({
                "id": f"food_{recipe_id}", "label": recipe.get("label", recipe_id),
                "count": count, "kind": "food", "recipe_id": recipe_id, "action": f"use_food:{recipe_id}",
                "extra_tts": f"Use: {e.recipe_effect_text(recipe)}"
            })
        return entries

    def fishing_items(self):
        e = self.engine
        entries = [{"id":"fishing_rod", "label":"Fishing rod", "count":e.resources.get("fishing_rod",0), "kind":"tool", "action":""}]
        for key, fish in e.fishing_config()['fish'].items():
            entries.append({"id":key, "label":fish['label'], "count":e.resources['fish'].get(key,0), "kind":"fish", "action":""})
        return entries

    # ---- page ----

    def page_objects(self):
        e = self.engine
        entries = e.registry.collect("inventory.items")
        entries = [entry for entry in entries if entry['kind']=='coin' or entry['count']>0]
        page_size = min(12, max(2, e.inventory_items_per_page))
        gold = next(item for item in entries if item['kind']=='coin')
        foods = [item for item in entries if item['kind']=='food']
        others = [item for item in entries if item['kind'] not in ('coin','food')]
        pages = [[gold]+foods[:page_size-1]]
        overflow=foods[page_size-1:]
        pages += [overflow[i:i+page_size] for i in range(0,len(overflow),page_size)]
        pages += [others[i:i+page_size] for i in range(0,len(others),page_size)]
        e.inventory_page_count=len(pages)
        e.inventory_page=max(0,min(e.inventory_page,e.inventory_page_count-1))
        entries=pages[e.inventory_page]
        positions = [
            (9, 5), (23, 5), (37, 5), (51, 5),
            (9, 15), (23, 15), (37, 15), (51, 15),
            (9, 25), (23, 25), (37, 25), (51, 25)
        ]
        objects = []
        for index, entry in enumerate(entries[:len(positions)]):
            x, y = positions[index]
            extra = entry.get("extra_tts", "")
            tts = f"{entry['label']} {entry['count']}."
            if extra:
                tts += f". {extra}"
            objects.append({
                "id": f"inventory_{entry['id']}", "type": "resource",
                "count": entry["count"], "resource_kind": entry["kind"], "recipe_id": entry.get("recipe_id"), "seed_id": entry.get("seed_id"), "x": x, "y": y,
                "width": 10, "height": 8 if entry["kind"] == "food" else 6, "hit_width": 13, "hit_height": 9,
                "label": entry["label"], "tts": tts, "action": entry.get("action", "")
            })
        for delta, x, label, direction in [(-1, 9, "Previous page", "left"), (1, 51, "Next page", "right")]:
            if 0 <= e.inventory_page + delta < e.inventory_page_count:
                objects.append({"id": f"inventory_page_{direction}", "type": "arrow",
                                "x": x, "y": 35, "direction": direction, "size": 2,
                                "hit_width": 11, "hit_height": 7,
                                "label": label, "tts": label,
                                "action": f"inventory_page:{delta}"})
        return objects

    def turn_page(self, arg, obj):
        e = self.engine
        if e.current_page != "inventory":
            return e.response()
        delta = int(arg)
        self.page_objects()
        e.inventory_page = max(0, min(e.inventory_page + delta, e.inventory_page_count - 1))
        e.clear_hover()
        e.render()
        return e.response(tts="Next page" if delta > 0 else "Previous page", sfx="open_page")

    def navigate(self, direction):
        """Left/Right turn pages; past the first or last page it says so."""
        e = self.engine
        if e.paused: return e.response(tts='Resume first.')
        self.page_objects()
        delta = -1 if direction=='left' else 1
        if not 0 <= e.inventory_page+delta < e.inventory_page_count:
            return e.response(tts='First page.' if delta<0 else 'Last page.')
        return e._perform_action(f'inventory_page:{delta}', {})

    def open(self):
        """Open the inventory directly (tools and tests; players use F2)."""
        e = self.engine
        if e.day_ended:
            return e.night_only_response()
        e.inventory_page = 0
        e.set_page("inventory")
        e.seed_select_plot_id = None
        e.clear_care()
        e.clear_harvest()
        e.clear_cooking()
        e.clear_hover()
        e.render()
        return e.response(tts="Inventory.", sfx="open_page")

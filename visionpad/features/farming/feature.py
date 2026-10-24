"""Farming: plots, planting, watering and fertilizing (drag tools and the care minigame), daily growth.

Engine attributes (save format): farm_plots, seed_select_plot_id, detail_plot_id, care_mode,
care_targets, care_dragging, care_collected_ids, care_visible_until.
Shared state written: resources seeds/fertilizer/coin/crops, current_page/current_location,
last_pointer, pending_visual_completion, drag_tool and drag_target_ids (core input state while a
tool is held); spends time. Paired with harvest (harvest resets plots, farming clears harvest).
"""
import copy

from visionpad.core import order
from visionpad.core.registry import Feature
from visionpad.features.farming.care import CareMinigame
from visionpad.features.farming.drawing import FarmDrawing
from visionpad.features.farming.market import FarmMarket

CARE_PAGES = ("water_minigame", "fertilizer_minigame")


class Farming(CareMinigame, FarmMarket, FarmDrawing, Feature):
    name = "farming"

    def register(self, reg):
        reg.owns("farm_plots", "seed_select_plot_id", "detail_plot_id", "care_mode", "care_targets",
                 "care_dragging", "care_collected_ids", "care_visible_until")
        reg.page("farm", objects=self.farm_objects, detail=lambda: "Farm. Choose a plot to manage your crops.")
        reg.page("plot_detail", objects=self.plot_detail_objects, scene=self.draw_detail_scene,
                 icon_grid=True, icon_only=("care_button",), layout=self.detail_layout,
                 detail=lambda: "Plot details. Plant, water, or fertilize.")
        reg.page("seed_select", objects=self.seed_select_objects, icon_grid=True,
                 detail=lambda: "Seeds. Choose seeds to plant.")
        for page in CARE_PAGES:
            reg.page(page, objects=self.care_objects, live=True, guidance=self.care_guidance,
                     pointer_move=self.care_move, pointer_down=self.care_move, pointer_drag=self.care_move,
                     pointer_up=self.engine.minigame_release)
        reg.action("open_plot_detail:", lambda arg, obj: self.open_plot_detail(arg))
        reg.action("start_care:", self.start_care_action)
        reg.action("open_seed_select:", lambda arg, obj: self.open_seed_select(arg))
        reg.action("plant:", self.plant_action)
        reg.action("drag_tool:", self.pick_tool)
        reg.drag_tool("water", lambda x, y: self.drop_tool(x, y, self.water_plot))
        reg.drag_tool("fertilizer", lambda x, y: self.drop_tool(x, y, self.fertilize_plot))
        reg.renderer("plot", self.draw_plot)
        reg.renderer("plot_detail_field", self.draw_detail_field)
        reg.renderer("growth_gauge", self.draw_detail_gauge)
        reg.renderer("care_field", lambda obj: self.engine.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 46), obj.get("height", 30)))
        reg.renderer("care_target", self.draw_care_target)
        reg.icon("seed")
        reg.icon("care_button", symbol=lambda obj: {'plant':'seed','fertilizer':'tool'}.get(obj.get('care_kind'),obj.get('care_kind')))
        reg.icon("watering_can", symbol=lambda obj: 'water')
        reg.icon("fertilizer", symbol=lambda obj: 'tool')
        reg.object_tts("plot", self.plot_tts)
        reg.object_tts("plot_detail_field", self.plot_tts)
        reg.object_tts("seed", self.seed_tts)
        for object_type, sound in (("plot", "hover_plot"), ("watering_can", "hover_water_tool"),
                                   ("fertilizer", "hover_fertilizer"), ("seed", "hover_seed"),
                                   ("plot_detail_field", "hover_plot"), ("growth_gauge", "hover_plot"),
                                   ("care_button", "hover_tool"), ("care_field", "hover_plot"), ("care_target", "hover_tool")):
            reg.hover_sfx(object_type, sound)
        reg.visual_completion("care", self.finish_care)
        reg.state("farm_plots", lambda: {plot_id: dict(state) for plot_id, state in self.engine.farm_plots.items()})
        reg.state("seed_select_plot_id", lambda: self.engine.seed_select_plot_id)
        reg.state("plot_detail_id", lambda: self.engine.detail_plot_id)
        reg.state("care", self.care_state)
        reg.spectator("plots", self.spectator_plots)
        reg.spectator("care_targets", self.spectator_care_targets)
        reg.contribute("inventory.items", self.inventory_items, order=order.InventoryItems.FARMING)
        reg.contribute("shop.buy_items", self.shop_buy_rows, order=order.ShopBuyItems.FARMING)
        reg.contribute("shop.sell_items", self.shop_sell_rows, order=order.ShopSellItems.FARMING)
        reg.shop_item("seed", lambda item_id: self.buy_item("seed", item_id))
        reg.shop_item("fertilizer", lambda item_id: self.buy_item("fertilizer", item_id))
        reg.shop_item("crop", sell=self.sell_crop)
        reg.on("reset", self.reset, order=order.Reset.FARMING)
        reg.on("end_of_day", self.grow, order=order.EndOfDay.FARMING)
        reg.on("leave_activity", self.clear_care, order=order.LeaveActivity.FARMING)
        reg.on("release_drag", self.release)
        reg.save_fields(transient={"care_dragging": False}, clock_maps=("care_visible_until",))
        for name, function in (("new_plot_state", self.new_plot_state), ("get_unlocked_plot_defs", self.unlocked_plot_defs),
                               ("get_effective_seed_return_chance", self.seed_return_chance),
                               ("get_fertilizer_price", self.fertilizer_price), ("clear_care", self.clear_care),
                               ("open_plot_detail", self.open_plot_detail), ("plant_seed", self.plant_seed),
                               ("start_care_minigame", self.start_care), ("finish_care_minigame", self.finish_care)):
            reg.expose(name, function)

    def reset(self):
        e = self.engine
        e.farm_plots = {}
        for plot in e.config.get("farm", {}).get("plots", []):
            e.farm_plots[plot["id"]] = self.new_plot_state()
        e.seed_select_plot_id = None
        e.detail_plot_id = None
        e.care_mode = None
        e.care_targets = []
        e.care_dragging = False
        e.care_collected_ids = set()
        e.care_visible_until = {}

    def grow(self):
        """Overnight growth of watered crops; returns the morning note for newly ripe crops."""
        e = self.engine
        matured = []
        for state in e.farm_plots.values():
            if state["seed_id"] is not None and not state["mature"] and state["watered"]:
                gain = 1
                seed_config = e.get_seed_config(state["seed_id"])
                needed = int(seed_config.get("growth_days", 3))
                state["growth"] = min(needed, state["growth"] + gain)
                if state["growth"] >= needed:
                    state["mature"] = True
                    matured.append(e.get_seed_label(state["seed_id"]))

            state["watered"] = False
            state["fertilized"] = False
        if matured:
            names = ", ".join(dict.fromkeys(matured))
            return f"{names} ready to harvest."
        return None

    def detail_layout(self, objects):
        for obj in objects:
            if obj['type'] == 'growth_gauge':
                obj.update(x=30, y=16, hit_width=42, hit_height=5)
            elif obj['type'] == 'plot_detail_field':
                obj.update(x=30, y=30, hit_width=44, hit_height=18)

    def draw_detail_scene(self):
        pad = self.engine.dotpad
        pad.draw_line(0, 12, pad.width - 1, 12)
        pad.draw_line(0, 13, pad.width - 1, 13)

    def plot_tts(self, obj):
        e = self.engine
        kind = obj.get("type")
        label = str(obj.get("label") or "Object").strip()
        plot_id = (e.detail_plot_id if kind == "plot_detail_field"
                   else obj.get("id"))
        state = e.farm_plots.get(plot_id) or {}
        plot_label = (self.plot_label(plot_id) if kind == "plot_detail_field"
                      and plot_id else label)
        seed_id = state.get("seed_id")
        return f"{plot_label}, {e.get_seed_label(seed_id)}." if seed_id else f"{plot_label}, empty."

    def seed_tts(self, obj):
        e = self.engine
        label = str(obj.get("label") or "Object").strip()
        count = obj.get("count")
        if count is None:
            count = e.resources.get("seeds", {}).get(obj.get("seed_id"))
        if count is not None:
            return f"{label}, {count}."
        if obj.get("price") is not None:
            return f"{label}, {obj['price']} gold."
        return label

    def spectator_plots(self, objects):
        e = self.engine
        plots = []
        for definition in self.unlocked_plot_defs():
            state = e.farm_plots[definition['id']]
            seed = e.config.get('seeds', {}).get(state.get('seed_id'), {})
            plots.append(dict(id=definition['id'], **copy.deepcopy(state),
                              growth_days=seed.get('growth_days', 1)))
        return plots

    # ---- drag tools ----

    def plant_action(self, arg, obj):
        plot_id, seed_id = arg.split(":", 1)
        return self.plant_seed(plot_id, seed_id)

    def pick_tool(self, tool, obj):
        e = self.engine
        e.drag_tool = tool
        e.drag_target_ids.clear()
        if e.drag_tool == "water":
            return e.response(tts="Watering can. Drag to a plot.", sfx="tool_pickup")
        if e.drag_tool == "fertilizer":
            count = int(e.resources.get("fertilizer", 0))
            if count <= 0:
                e.drag_tool = None
                return e.response(tts="No fertilizer.", sfx="error")
            return e.response(tts=f"Fertilizer. Stock: {count}. Drag to a watered plot.", sfx="tool_pickup")
        return e.response(tts=e.get_object_tts(obj))  # unknown tool: same fallback as an unknown action

    def drop_tool(self, x, y, apply):
        e = self.engine
        plot = self.plot_at(x, y)
        if plot is None:
            return e.response()
        plot_id = plot["id"]
        if plot_id in e.drag_target_ids:
            return e.response()
        e.drag_target_ids.add(plot_id)
        return apply(plot_id)

    # ---- plots, planting, care minigame ----

    def new_plot_state(self):
        return {
            "seed_id": None,
            "watered": False,
            "fertilized": False,
            "growth": 0,
            "mature": False
        }

    def plot_label(self, plot_id):
        e = self.engine
        for plot in e.config.get("farm", {}).get("plots", []):
            if plot["id"] == plot_id:
                return plot.get("label", plot_id)
        return plot_id

    def unlocked_plot_defs(self):
        e = self.engine
        return e.config.get("farm", {}).get("plots", [])[:e.unlocked_plot_count]

    def farm_objects(self):
        e = self.engine
        farm = e.config.get("farm", {})
        objects = []
        grid_positions = [
            (11, 10), (30, 10), (49, 10),
            (11, 27), (30, 27), (49, 27),
        ]

        for idx, plot in enumerate(self.unlocked_plot_defs()):
            obj = dict(plot)
            obj["type"] = "plot"
            if idx < len(grid_positions):
                px, py = grid_positions[idx]
                obj.update(x=px, y=py, width=16, height=14, hit_width=16, hit_height=14)
            state = e.farm_plots[plot["id"]]
            seed_id = state["seed_id"]

            if seed_id is None:
                obj["tts"] = f"{plot['label']}. Empty. Select to manage."
                obj["action"] = f"open_plot_detail:{plot['id']}"
            else:
                seed_label = e.get_seed_label(seed_id)
                needed = int(e.get_seed_config(seed_id).get("growth_days", 3))
                if state["mature"]:
                    obj["tts"] = f"{plot['label']}. {seed_label}. Ready to harvest."
                else:
                    water_text = "Watered" if state["watered"] else "Needs water"
                    fertilizer_text = "Fertilized" if state["fertilized"] else "Not fertilized"
                    obj["tts"] = (
                        f"{plot['label']}. {seed_label} is growing. "
                        f"Growth {state['growth']} of {needed} days. {water_text}. {fertilizer_text}. "
                        "Select to manage."
                    )
                obj["action"] = f"open_plot_detail:{plot['id']}"
            objects.append(obj)

        for obj in farm.get("objects", []):
            objects.append(dict(obj))
        return objects

    def plot_detail_objects(self):
        e = self.engine
        plot_id = e.detail_plot_id
        state = e.farm_plots.get(plot_id) if plot_id else None
        if state is None:
            return [e.back_arrow("plot_detail_back", "Back to farm", "return_scene")]

        plot_label = self.plot_label(plot_id)
        seed_id = state.get("seed_id")
        if seed_id is None:
            return [
                {
                    "id": "plot_detail_empty", "type": "plot_detail_field",
                    "x": 30, "y": 17, "width": 44, "height": 18,
                    "hit_width": 48, "hit_height": 18,
                    "label": f"{plot_label} details",
                    "tts": f"{plot_label}. Empty plot.",
                    "action": ""
                },
                {
                    "id": "plot_detail_plant", "type": "care_button", "care_kind": "plant",
                    "x": 30, "y": 31, "width": 18, "height": 6,
                    "hit_width": 22, "hit_height": 10,
                    "label": "Plant seeds",
                    "tts": "Plant. Choose seeds.",
                    "action": f"open_seed_select:{plot_id}"
                },
                e.back_arrow("plot_detail_back", "Back to farm", "return_scene")
            ]

        seed_label = e.get_seed_label(seed_id)
        needed = int(e.get_seed_config(seed_id).get("growth_days", 3))
        water_text = "Watered" if state["watered"] else "Needs water"
        if state["fertilized"]:
            fertilizer_text = "Fertilized"
        elif int(e.resources.get("fertilizer", 0)) <= 0:
            fertilizer_text = "No fertilizer. Buy at the shop."
        else:
            fertilizer_text = f"Not fertilized. Stock: {e.resources.get('fertilizer', 0)} in stock"

        field_tts = (
            f"{plot_label}. {seed_label}. "
            f"Growth {state['growth']} of {needed} days. {water_text}. {fertilizer_text}"
        )
        if state["mature"]:
            field_tts = f"{plot_label}. {seed_label}. Ready to harvest."

        objects = [{
            "id": "plot_detail_field", "type": "plot_detail_field",
            "x": 30, "y": 17, "width": 44, "height": 18,
            "hit_width": 48, "hit_height": 18,
            "label": f"{plot_label} details", "tts": field_tts, "action": ""
        }, {
            "id": "plot_detail_growth_gauge", "type": "growth_gauge",
            "x": 30, "y": 4, "width": 42, "height": 5,
            "hit_width": 44, "hit_height": 6,
            "label": "Growth",
            "tts": f"Growth. {seed_label}. {needed if state['mature'] else state['growth']} of {needed} days",
            "action": ""
        }]

        if state["mature"]:
            objects.append({
                "id": "plot_detail_harvest", "type": "care_button", "care_kind": "harvest",
                "x": 30, "y": 31, "width": 18, "height": 6,
                "hit_width": 22, "hit_height": 10,
                "label": "Harvest",
                "tts": f"Harvest. {seed_label}. Ready to harvest.",
                "action": f"start_harvest:{plot_id}"
            })
        else:
            water_action = "" if state["watered"] else f"start_care:water:{plot_id}"
            water_tts = (
                "Already watered."
                if state["watered"]
                else "Water. Drag over targets."
            )
            objects.append({
                "id": "plot_detail_water", "type": "care_button", "care_kind": "water",
                "x": 23, "y": 31, "width": 18, "height": 6,
                "hit_width": 21, "hit_height": 10,
                "label": "Water", "tts": water_tts, "action": water_action
            })

            fertilizer_count = int(e.resources.get("fertilizer", 0))
            fertilizer_action = ""
            if not state["fertilized"] and fertilizer_count > 0:
                fertilizer_action = f"start_care:fertilizer:{plot_id}"
            if state["fertilized"]:
                fertilizer_tts = "Already fertilized."
            elif fertilizer_count <= 0:
                fertilizer_tts = "No fertilizer. Buy at the shop."
            else:
                fertilizer_tts = f"Fertilizer. Stock: {fertilizer_count}."
            objects.append({
                "id": "plot_detail_fertilizer", "type": "care_button", "care_kind": "fertilizer",
                "x": 46, "y": 31, "width": 18, "height": 6,
                "hit_width": 21, "hit_height": 10,
                "label": "Fertilize", "tts": fertilizer_tts, "action": fertilizer_action
            })

        objects.append(e.back_arrow("plot_detail_back", "Back to farm", "return_scene"))
        return objects

    def seed_select_objects(self):
        e = self.engine
        objects = []
        positions = [(12, 18), (30, 18), (48, 18)]
        available = []
        for seed_id, seed_config in e.config.get("seeds", {}).items():
            count = int(e.resources["seeds"].get(seed_id, 0))
            if count > 0:
                available.append((seed_id, seed_config, count))

        for index, (seed_id, seed_config, count) in enumerate(available[:len(positions)]):
            x, y = positions[index]
            yield_count = e.get_harvest_base_yield(seed_id)
            growth_days = int(seed_config.get("growth_days", 3))
            objects.append({
                "id": f"seed_{seed_id}", "type": "seed", "seed_id": seed_id,
                "x": x, "y": y, "width": 12, "height": 10,
                "hit_width": 15, "hit_height": 13,
                "label": f"{seed_config.get('label', seed_id)} seeds", "count": count,
                "tts": f"{seed_config.get('label', seed_id)} seeds {count}. Growth {growth_days} days, Harvest {yield_count}, Seed recovery level {e.research_levels.get('seed_return', 0)}",
                "action": f"plant:{e.seed_select_plot_id}:{seed_id}"
            })

        objects.append(e.back_arrow("seed_back", "Back to farm", "return_scene"))
        return objects

    def plot_at(self, x, y):
        e = self.engine
        for obj in e.get_objects():
            if obj.get("type") == "plot" and e.object_contains(obj, x, y):
                return obj
        return None

    def status_text(self, plot_id):
        e = self.engine
        state = e.farm_plots.get(plot_id)
        if state is None:
            return "Plot unavailable."
        label = self.plot_label(plot_id)
        if not state.get("seed_id"):
            return f"{label}. Empty. Plant seeds."
        seed = e.get_seed_label(state["seed_id"])
        if state["mature"]:
            return f"{label}, {seed}. Ready to harvest"
        needed = int(e.get_seed_config(state["seed_id"]).get("growth_days", 3))
        water = "Watered" if state["watered"] else "Needs water"
        fertilizer = "Fertilized" if state["fertilized"] else "Not fertilized"
        return f"{label}, {seed}. Growth {state['growth']} of {needed} days. {water}. {fertilizer}"

    def open_plot_detail(self, plot_id):
        e = self.engine
        unlocked = {p["id"] for p in self.unlocked_plot_defs()}
        state = e.farm_plots.get(plot_id)
        if state is None or plot_id not in unlocked:
            return e.response(tts="Plot unavailable.", sfx="error")
        e.detail_plot_id = plot_id
        e.current_location = "farm"
        e.set_page("plot_detail")
        self.clear_care(keep_detail=True)
        e.clear_harvest()
        e.clear_hover()
        e.render()
        return e.response(tts=f"{self.plot_label(plot_id)}.", sfx="open_page")

    def open_seed_select(self, plot_id):
        e = self.engine
        if e.day_ended:
            return e.night_only_response()
        state = e.farm_plots.get(plot_id)
        unlocked = [p["id"] for p in self.unlocked_plot_defs()]
        if state is None or plot_id not in unlocked:
            return e.response(tts="Plot unavailable.", sfx="error")
        if state["seed_id"] is not None:
            return e.response(tts="Plot occupied.")
        if not any(int(count) > 0 for count in e.resources["seeds"].values()):
            return e.response(tts="No seeds. Buy at the shop.", sfx="error")
        e.seed_select_plot_id = plot_id
        e.set_page("seed_select")
        e.clear_hover()
        e.render()
        return e.response(tts="Seeds.", sfx="open_page")

    def plant_seed(self, plot_id, seed_id):
        e = self.engine
        state = e.farm_plots.get(plot_id)
        seed_config = e.get_seed_config(seed_id)
        if state is None or not seed_config:
            return e.response(tts="Cannot plant here.", sfx="error")
        if state["seed_id"] is not None:
            return e.response(tts="Plot occupied.", sfx="error")
        count = int(e.resources["seeds"].get(seed_id, 0))
        if count <= 0:
            return e.response(tts="No seeds of this type.", sfx="error")
        e.resources["seeds"][seed_id] = count - 1
        e.farm_plots[plot_id] = self.new_plot_state()
        e.farm_plots[plot_id]["seed_id"] = seed_id
        e.detail_plot_id = plot_id
        e.set_page("plot_detail")
        e.current_location = "farm"
        e.seed_select_plot_id = None
        e.clear_hover()
        result = e.consume_time("plant")
        if result["night"]:
            return e.night_response(f"{e.get_seed_label(seed_id)} planted.")
        e.render()
        return e.response(tts=f"{e.get_seed_label(seed_id)} planted. Water, then sleep.", sfx="plant")

    def water_plot(self, plot_id):
        e = self.engine
        state = e.farm_plots.get(plot_id)
        if state is None:
            return e.response()
        label = self.plot_label(plot_id)
        if state["seed_id"] is None:
            return e.response(tts=f"{label} is empty. Plant seeds first.", sfx="error")
        if state["mature"]:
            return e.response(tts=f"{label} is ready to harvest.", sfx="error")
        if state["watered"]:
            return e.response(tts=f"{label} Already watered.", sfx="error")
        state["watered"] = True
        result = e.consume_time("water")
        if result["night"]:
            return e.night_response(f"{label} watered")
        e.render()
        return e.response(tts=f"{label} watered. {e.get_seed_label(state['seed_id'])} will grow after sleep.", sfx="water")

    def apply_fertilizer_bonus(self, state):
        e = self.engine
        needed = int(e.get_seed_config(state["seed_id"]).get("growth_days", 3))
        bonus = max(0, int(e.config.get("fertilizer", {}).get("growth_day_bonus", 1)))
        before = state["growth"]
        state["growth"] = min(needed, before + bonus)
        state["fertilized"] = True
        state["mature"] = state["growth"] >= needed
        saved = state["growth"] - before
        remaining = max(0, needed - state["growth"])
        status = "Ready to harvest" if state["mature"] else f"Water, then sleep {remaining} more days to harvest."
        return f"Harvest {saved} days sooner. {status}"

    def fertilize_plot(self, plot_id):
        e = self.engine
        state = e.farm_plots.get(plot_id)
        if state is None:
            return e.response()
        label = self.plot_label(plot_id)
        if state["seed_id"] is None:
            return e.response(tts=f"{label} is empty. Plant first.", sfx="error")
        if state["mature"]:
            return e.response(tts=f"{label} is ready to harvest.", sfx="error")
        if not state["watered"]:
            return e.response(tts=f"{label} needs water first.", sfx="error")
        if state["fertilized"]:
            return e.response(tts=f"{label} is already fertilized.", sfx="error")
        count = int(e.resources.get("fertilizer", 0))
        if count <= 0:
            return e.response(tts="No fertilizer. Buy at the shop.", sfx="error")
        e.resources["fertilizer"] = count - 1
        fertilizer_text = self.apply_fertilizer_bonus(state)
        result = e.consume_time("fertilize")
        if result["night"]:
            return e.night_response(f"{label} fertilized.")
        e.render()
        return e.response(tts=f"{label} fertilized. {fertilizer_text}.  fertilizer {e.resources.get('fertilizer', 0)} remaining", sfx="fertilize")

    def seed_return_chance(self, seed_id):
        e = self.engine
        cfg = e.config.get("research", {}).get("seed_return", {})
        level = int(e.research_levels.get("seed_return", 0))
        chances = cfg.get("return_chances", [0.3, 0.6])
        chance = chances[min(level - 1, len(chances) - 1)] if level > 0 else e.get_seed_config(seed_id).get("seed_return_chance", 0.0)
        return min(1.0, max(0.0, float(chance)))

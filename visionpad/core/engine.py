import copy
import math
import random
import time

from pathlib import Path
from visionpad.core.registry import Registry
from visionpad.core.state import SharedState
from visionpad.display.dotpad import DotPad
from visionpad.display.icons import IconGrid, IconLayout, IconRenderer
from visionpad.display.keypad import KeypadUI
from visionpad.features import load_features
from visionpad.paths import SAVES_DIR
from visionpad.services.saves import SaveMixin
from visionpad.spectator.state import spectator_snapshot


class GameEngine(KeypadUI, SaveMixin, SharedState):

    def __init__(self, config, save_dir=None):
        config = self.prepare_display_config(config)
        self.config = config
        self.sleep_blackout_seconds = max(0, float(config.get("interaction", {}).get("sleep", {}).get("blackout_ms", 2000))) / 1000
        interaction = config.get("interaction", {})
        feedback = interaction.get("feedback", {})
        cooking = interaction.get("cooking", {})
        inventory = interaction.get("inventory", {})
        self.disappear_delay_seconds = max(0, float(feedback.get("disappear_delay_ms", 1000))) / 1000
        self.resume_marker_delay_seconds = max(0, float(cooking.get("resume_marker_delay_ms", 2000))) / 1000
        self.stir_scale = max(0.1, float(cooking.get("stir_scale", 1.6)))
        # The physical layout has twelve slots and reserves its bottom row for arrows.
        self.inventory_items_per_page = max(1, min(12, int(inventory.get("items_per_page", 12))))
        self.inventory_hide_zero_items = bool(inventory.get("hide_zero_items", True))
        self.client_settings = {
            "visual_refresh_interval_ms": max(50, int(feedback.get("visual_refresh_interval_ms", 100))),
            "audio": interaction.get("audio", {})
        }

        dot_config = config["dotpad"]
        self.dotpad = DotPad(
            width=dot_config["width"],
            height=dot_config["height"]
        )

        time_bar = config.get("time", {}).get("bar", {})
        self.timepad = DotPad(
            width=int(time_bar.get("panel_width", 40)),
            height=int(time_bar.get("panel_height", 4))
        )

        self.save_dir = Path(save_dir) if save_dir is not None else SAVES_DIR
        self.icon_layout = IconLayout(IconGrid())
        self.icons = IconRenderer(self)
        self.shop_page_count = 1  # Derived UI cache; excluded from save snapshots.
        self.registry = Registry.build(self, load_features())
        self._static_fields = set(vars(self))
        self.reset()
        self.registry.check_owned(self)

    def __getattr__(self, name):
        # Methods that moved into features but are still called on the engine (tests, tools).
        registry = self.__dict__.get("registry")
        if registry is not None and name in registry.api:
            return registry.api[name]
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    @staticmethod
    def prepare_display_config(config):
        # Keep saved rules intact; normalize presentation in a private copy.
        config = copy.deepcopy(config)
        # One editable definition per dish; inventory variants preserve effect strength.
        for recipe_id, recipe in list(config.get('recipes', {}).items()):
            if recipe.get('seafood') and not recipe.get('hidden_recipe'):
                for grade, effect in recipe.get('quality_effects', {}).items():
                    variant = copy.deepcopy(recipe)
                    variant.update(effect)
                    variant.update(hidden_recipe=True, fish_grade=grade, base_recipe=recipe_id)
                    adjective = {'low': 'Simple', 'medium': 'Ordinary', 'high': 'Luxurious'}[grade]
                    variant['label'] = f"{adjective} {recipe['label']}"
                    config['recipes'][recipe_id+'_'+grade] = variant
        names = {"home": "Home", "farm": "Farm", "town": "Village", "mine": "Mine", "fishing": "Fishing lake", "npc_dialogue": "Conversation",
                 "minimap": "Map", "inventory": "Inventory", "research": "Research",
                 "plot_detail": "Plot", "seed_select": "Seeds", "water_minigame": "Watering",
                 "fertilizer_minigame": "Fertilizing", "harvest": "Harvest",
                 "recipe_select": "Recipes", "ingredient_select": "Ingredients", "cooking": "Cooking",
                 "shop_choice": "Shop", "shop_buy": "Buy", "shop_sell": "Sell"}
        for key, label in names.items():
            page = config.setdefault("pages", {}).get(key)
            if isinstance(page, dict):
                page["label"] = label
            elif isinstance(page, str):
                config["pages"][key] = label
        for key, seed in config.get("seeds", {}).items():
            seed["label"] = {"tomato": "Tomato", "carrot": "Carrot", "potato": "Potato"}.get(key, key.replace("_", " ").title())
        for key, recipe in config.get("recipes", {}).items():
            if recipe.get("seafood"): continue
            recipe["label"] = {"tomato_carrot_stew": "Tomato carrot stew", "potato_tomato_soup": "Potato tomato soup",
                               "vegetable_fritters": "Vegetable fritters", "rowan_soup": "Rowan's soup"}.get(key, key.replace("_", " ").title())
            recipe["buff_label"] = {"harvest_multiplier": "Harvest boost", "pickaxe_protection": "Pickaxe protection",
                                    "time_slow": "Time saving"}.get(recipe.get("buff_kind"), "Food effect")
            for stage in recipe.get("gesture_steps", []):
                stage["label"] = ("Trace eight petals" if key == "vegetable_fritters" else "Stir") if stage.get("kind") == "stir" else "Chop"
        for i, plot in enumerate(config.get("farm", {}).get("plots", [])):
            plot["label"] = f"Plot {i + 1}"
        for scene in ("home", "farm", "town"):
            for obj in config.get(scene, {}).get("objects", []):
                action = obj.get("action", "")
                obj["label"] = names.get(action.split(":")[-1], {"bed": "Bed", "chest": "Research", "stove": "Kitchen", "shop_npc": "Shop"}.get(obj.get("type"), obj.get("id", "Object")))
                obj["tts"] = obj["label"]
        return config

    def compact_objects(self, objects):
        """Use shared slots for icons; preserve spatial minigame/map geometry."""
        if self.current_page == "shop_choice":
            objects = list(objects) + [self.back_arrow("shop_choice_back", "Back to village", "return_scene")]
        objects = self.icon_layout.arrange(self.current_page, objects,
                                           self.dotpad.width, self.dotpad.height,
                                           types=self.icons.types, layout_order=self.registry.icon_layout_order,
                                           grid_pages=self.registry.icon_grid_pages())
        if self.current_page == 'plot_detail':
            for obj in objects:
                if obj['type'] == 'growth_gauge':
                    obj.update(x=30, y=16, hit_width=42, hit_height=5)
                elif obj['type'] == 'plot_detail_field':
                    obj.update(x=30, y=30, hit_width=44, hit_height=18)
        return objects
        
    def reset(self):
        self._menu_stack = []
        self._load_return = None
        self._save_slots = []
        self.sleep_until = None
        self.pending_visual_completion = None
        self.shop_page = 0
        self.shop_page_count = 1
        self.day = int(self.config.get("game", {}).get("start_day", 1))
        self.current_location = "home"
        self.current_page = "home"
        self.paused = False
        self.day_ended = False

        resource_config = self.config.get("resources", {})
        self.resources = {
            "coin": int(resource_config.get("coin", 0)),
            "wood": int(resource_config.get("wood", 0)),
            "stone": int(resource_config.get("stone", 0)),
            "fertilizer": int(resource_config.get("fertilizer", 0)),
            "seeds": dict(resource_config.get("seeds", {})),
            "crops": dict(resource_config.get("crops", {})),
            "foods": dict(resource_config.get("foods", {}))
        }

        for mineral in ("copper", "iron", "diamond"):
            self.resources[mineral] = int(resource_config.get(mineral, 0))
        self.resources["pickaxe"] = min(1, max(0, int(resource_config.get("pickaxe", 0))))

        for seed_id in self.config.get("seeds", {}):
            self.resources["seeds"].setdefault(seed_id, 0)
            self.resources["crops"].setdefault(seed_id, 0)

        for recipe_id in self.config.get("recipes", {}):
            self.resources["foods"].setdefault(recipe_id, 0)

        self.farm_plots = {}
        for plot in self.config.get("farm", {}).get("plots", []):
            self.farm_plots[plot["id"]] = self.new_plot_state()

        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids = set()

        self.detail_plot_id = None

        self.care_mode = None
        self.care_targets = []
        self.care_dragging = False
        self.care_collected_ids = set()
        self.care_visible_until = {}

        self.harvest_plot_id = None
        self.harvest_targets = []
        self.harvest_dragging = False
        self.harvest_collected_ids = set()

        self.selected_recipe_id = None
        self.selected_ingredients = set()
        self.cooking_dragging = False
        self.cooking_path_samples = []
        self.cooking_visible_until = {}
        self.cooking_progress_index = 0
        self.cooking_stage_index = 0
        self.cooking_last_progress_at = None
        self.cooking_resume_marker = False

        self.active_buff = {
            "kind": None,
            "source": None,
            "multiplier": 1.0,
            "remaining_ticks": 0
        }

        self.hover_object_id = None
        self.last_hover_state = (None, False)
        self.location_detail_spoken = False
        self.last_pointer = (None, None)
        self.pointer_pressed = False

        time_config = self.config.get("time", {})
        self.time_total_cells = int(time_config.get("total_cells", 20))
        self.time_used_cells = 0
        self.registry.run("reset")

        self.render()

    def new_plot_state(self):
        return {
            "seed_id": None,
            "watered": False,
            "fertilized": False,
            "growth": 0,
            "mature": False
        }

    def clear_hover(self):
        self.hover_object_id = None
        self.last_hover_state = (None, False)
        self.location_detail_spoken = False

    def clear_care(self, keep_detail=False):
        if self.pending_visual_completion and self.pending_visual_completion[1] == "care":
            self.pending_visual_completion = None
        self.care_mode = None
        self.care_targets = []
        self.care_dragging = False
        self.care_collected_ids.clear()
        self.care_visible_until = {}
        if not keep_detail:
            self.detail_plot_id = None

    def clear_harvest(self):
        self.harvest_plot_id = None
        self.harvest_targets = []
        self.harvest_dragging = False
        self.harvest_collected_ids.clear()

    def clear_cooking(self, keep_recipe=False):
        if self.pending_visual_completion and self.pending_visual_completion[1] == "cooking":
            self.pending_visual_completion = None
        if not keep_recipe:
            self.selected_recipe_id = None
            self.selected_ingredients.clear()
        self.cooking_dragging = False
        self.cooking_path_samples = []
        self.cooking_visible_until = {}
        self.cooking_progress_index = 0
        self.cooking_stage_index = 0
        self.cooking_last_progress_at = None
        self.cooking_resume_marker = False

    def has_final_consonant(self, text):
        if not text:
            return False
        code = ord(str(text)[-1])
        if 0xAC00 <= code <= 0xD7A3:
            return (code - 0xAC00) % 28 != 0
        return False

    def josa(self, text, consonant_form, vowel_form):
        return consonant_form if self.has_final_consonant(text) else vowel_form

    def ro_particle(self, text):
        if not text:
            return " "
        code = ord(str(text)[-1])
        if 0xAC00 <= code <= 0xD7A3:
            jong = (code - 0xAC00) % 28
            return " " if jong in (0, 8) else " "
        return " "

    def get_page_name(self, page_id):
        registered = self.registry.page_name(page_id)
        if registered: return registered
        if page_id == "load_game": return "Load game"
        return self.config.get("pages", {}).get(page_id, page_id)

    def get_seed_config(self, seed_id):
        return self.config.get("seeds", {}).get(seed_id, {})

    def get_seed_label(self, seed_id):
        return self.get_seed_config(seed_id).get("label", seed_id)

    def get_recipe_config(self, recipe_id):
        return self.config.get("recipes", {}).get(recipe_id, {})

    def get_recipe_label(self, recipe_id):
        return self.get_recipe_config(recipe_id).get("label", recipe_id)

    def get_plot_label(self, plot_id):
        for plot in self.config.get("farm", {}).get("plots", []):
            if plot["id"] == plot_id:
                return plot.get("label", plot_id)
        return plot_id

    def get_action_cost(self, action_name):
        if action_name == "travel":
            return 0
        defaults = {"plant": 2, "water": 2, "fertilize": 2, "harvest": 3,
                    "research": 3, "cook": 3, "mine": 2}
        configured = self.config.get("time", {}).get("action_costs", {})
        return max(defaults.get(action_name, 0), int(configured.get(action_name, 0)))

    def get_time_cells(self):
        return max(0, min(self.time_total_cells, self.time_used_cells))

    def time_text(self):
        used = self.get_time_cells()
        remaining = max(0, self.time_total_cells - used)
        if self.day_ended:
            return "Night. Select the bed."
        return f"Activity: {remaining} hours left"

    def recipe_effect_text(self, recipe):
        if recipe.get('buff_kind') == 'sale_boost':
            return f"{recipe.get('buff_label', 'Better sales')}, {recipe.get('sale_uses', 3)} sales"
        return f"{recipe.get('buff_label', 'Food effect')}, {float(recipe.get('buff_ticks', 0)):g} hours"

    def buff_multiplier_for(self, kind):
        if self.active_buff.get("kind") == kind and float(self.active_buff.get("remaining_ticks", 0)) > 0:
            return float(self.active_buff.get("multiplier", 1.0))
        return 1.0

    def buff_text(self):
        if self.active_buff.get('kind')=='sale_boost' and self.active_buff.get('remaining_sales',0)>0:
            return f"Better sales, {self.active_buff['remaining_sales']} sales left"
        remaining = float(self.active_buff.get("remaining_ticks", 0))
        if remaining <= 0:
            return "No food effect"
        recipe = self.get_recipe_config(self.active_buff.get("source")) or {}
        return f"{recipe.get('buff_label', 'Food effect')}, {remaining:g} hours left"

    def tick_buff(self, cost):
        if self.active_buff.get("kind") == "sale_boost": return
        remaining = float(self.active_buff.get("remaining_ticks", 0))
        remaining = max(0, remaining - max(0, float(cost)))
        self.active_buff["remaining_ticks"] = remaining
        if remaining == 0:
            self.active_buff = {"kind": None, "source": None, "multiplier": 1.0, "remaining_ticks": 0}

    def consume_time(self, action_name):
        cost = max(0, self.get_action_cost(action_name))
        if self.day_ended:
            return {"cost": 0, "night": True}

        multiplier = self.buff_multiplier_for("time_slow")
        if 0 < multiplier < 1:
            remaining = float(self.active_buff["remaining_ticks"])
            covered = min(cost, remaining / multiplier)
            cost = covered * multiplier + (cost - covered)
        self.time_used_cells = min(self.time_total_cells, self.time_used_cells + cost)
        self.tick_buff(cost)

        if self.time_used_cells >= self.time_total_cells:
            self.enter_night()
            return {"cost": cost, "night": True}

        return {"cost": cost, "night": False}

    def enter_night(self):
        self.day_ended = True
        self.current_location = "home"
        self.current_page = "home"
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.pointer_pressed = False
        self.clear_hover()
        self.render()

    def night_response(self, prefix=None, sound_events=None):
        narration = "Night. Home now. Select the bed."
        if prefix:
            narration = f"{prefix}. {narration}"
        return self.response(tts=narration, sfx="day_end", sound_events=sound_events)

    def next_day(self):
        if self.sleep_until is not None:
            return self.response()
        self.sleep_until = time.monotonic() + self.sleep_blackout_seconds
        self.pointer_pressed = False
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.clear_hover()
        self.render()
        return self.response(tts="Sleeping.", sound_events=[{"kind": "one_shot", "sound": "sleep"}])

    def finish_sleep(self):
        self.registry.run("end_of_day")
        self.sleep_until = None
        matured = []
        for state in self.farm_plots.values():
            if state["seed_id"] is not None and not state["mature"] and state["watered"]:
                gain = 1
                seed_config = self.get_seed_config(state["seed_id"])
                needed = int(seed_config.get("growth_days", 3))
                state["growth"] = min(needed, state["growth"] + gain)
                if state["growth"] >= needed:
                    state["mature"] = True
                    matured.append(self.get_seed_label(state["seed_id"]))

            state["watered"] = False
            state["fertilized"] = False

        self.day += 1
        self.registry.run("start_of_day")
        self.time_used_cells = 0
        self.day_ended = False
        self.current_location = "home"
        self.current_page = "home"
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.clear_hover()
        self.render()

        text = f"Day {self.day}. Morning."
        if matured:
            names = ", ".join(dict.fromkeys(matured))
            text += f". {names} ready to harvest."
        return self.response(tts=text, sfx="morning")

    def lower_panel_state(self):
        if self.sleep_until is not None:
            return {"mode": "blank", "label": "Sleeping"}
        if self.current_page == "inventory":
            page, pages = self.inventory_page, self.inventory_page_count
        elif self.current_page in ("shop_buy", "shop_sell"):
            page, pages = self.shop_page, self.shop_page_count
        else:
            page, pages = 0, 1
        if pages > 1:
            return {"mode": "pages", "page": page + 1, "pages": pages,
                    "label": f"Page {page + 1} of {pages}"}
        labels = {"shop_choice": "shop", "shop_buy": "buy", "shop_sell": "sell"}
        if self.current_page in labels:
            return {"mode": "braille", "label": labels[self.current_page]}
        return {"mode": "time", "label": "Activity time"}

    def draw_time_bar(self):
        self.timepad.clear()
        panel = self.lower_panel_state()
        if panel["mode"] == "blank":
            return
        if panel["mode"] == "pages":
            start = (panel["page"] - 1) * self.timepad.width // panel["pages"]
            end = panel["page"] * self.timepad.width // panel["pages"]
            for x in range(start, max(start + 1, end)):
                for y in range(self.timepad.height):
                    self.timepad.set_dot(x, y)
            return
        if panel["mode"] == "braille":
            letters = {'s': (2,3,4), 'h': (1,2,5), 'o': (1,3,5),
                       'p': (1,2,3,4), 'b': (1,2), 'u': (1,3,6),
                       'y': (1,3,4,5,6), 'e': (1,5), 'l': (1,2,3)}
            positions = {1:(0,0), 2:(0,1), 3:(0,2), 4:(1,0), 5:(1,1), 6:(1,2)}
            for cell, char in enumerate(panel['label']):
                for dot in letters[char]:
                    x, y = positions[dot]
                    self.timepad.set_dot(cell * 2 + x, y)
            return
        bar = self.config.get("time", {}).get("bar", {})
        cell_width = int(bar.get("cell_width", 2))
        cell_height = int(bar.get("cell_height", 4))
        filled_columns = int(self.get_time_cells() * cell_width)
        for x in range(filled_columns):
            for dy in range(cell_height):
                self.timepad.set_dot(x, dy)

    def get_unlocked_plot_defs(self):
        return self.config.get("farm", {}).get("plots", [])[:self.unlocked_plot_count]

    def can_craft_recipe(self, recipe_id):
        recipe = self.get_recipe_config(recipe_id)
        if recipe.get("quest_only"): return False
        ingredients = recipe.get("ingredients", {})
        if recipe.get("seafood"): return self.seafood_ready(recipe)
        if len(ingredients) < 2:
            return False
        for seed_id, needed in ingredients.items():
            if int(self.resources["crops"].get(seed_id, 0)) < int(needed):
                return False
        return True

    def get_food_sell_price(self, recipe_id):
        recipe = self.get_recipe_config(recipe_id)
        if recipe.get("sell_price") is not None: return int(recipe["sell_price"])
        ingredient_total = 0
        for seed_id, count in recipe.get("ingredients", {}).items():
            crop_price = int(self.get_seed_config(seed_id).get("crop_price", 1))
            ingredient_total += crop_price * int(count)
        if recipe.get('seafood'):
            prices=[self.get_fish_price(k) for k,v in self.fishing_config()['fish'].items() if v['grade']==recipe.get('fish_grade','low')]
            ingredient_total += min(prices)*recipe.get('fish_required',1)
        return max(1, int(math.ceil(ingredient_total * 1.2)))

    def get_layout_objects(self):
        if self.sleep_until is not None:
            return []
        pages = {
            "load_game": self.get_load_objects,
            "home": self.get_home_objects,
            "farm": self.get_farm_objects,
            "seed_select": self.get_seed_select_objects,
            "plot_detail": self.get_plot_detail_objects,
            "water_minigame": self.get_care_minigame_objects,
            "fertilizer_minigame": self.get_care_minigame_objects,
            "harvest": self.get_harvest_objects,
            "recipe_select": self.get_recipe_select_objects,
            "ingredient_select": self.get_ingredient_select_objects,
            "cooking": self.get_cooking_objects,
            "shop_choice": self.get_shop_choice_objects,
            "shop_buy": self.get_shop_buy_objects,
            "shop_sell": self.get_shop_sell_objects,
        }
        getter = self.registry.page_hook(self.current_page, "objects") or pages.get(self.current_page)
        objects = self.compact_objects(getter()) if getter else []
        for obj in objects:
            if obj.get("type") == "arrow":
                if obj.get("action", "").startswith("shop_page:"):
                    obj.update(x=15 if obj["direction"] == "left" else 25, y=self.dotpad.height-5)
                elif obj.get("direction") == "left":
                    obj.update(direction="left", x=3, y=self.dotpad.height-5)
                elif obj.get("direction") == "right":
                    obj.update(direction="right", x=self.dotpad.width-4, y=5)
                w, h = (5, 9) if obj.get("direction") in ("left", "right") else (9, 5)
                obj["hit_width"], obj["hit_height"] = w, h
        horizontal_route = ("farm", "home", "town")
        if self.current_page in horizontal_route:
            origin = horizontal_route.index(self.current_page)
            for obj in objects:
                action = obj.get("action", "")
                if obj.get("type") == "arrow" and action.startswith("travel:"):
                    target = action.split(":", 1)[1]
                    if target in horizontal_route:
                        obj["direction"] = "left" if horizontal_route.index(target) < origin else "right"
                        obj["hit_width"], obj["hit_height"] = 5, 9
        return objects

    def get_objects(self):
        return [o for o in self.get_layout_objects() if o.get("type") != "arrow"]

    def get_home_objects(self):
        objects = []
        for obj in self.config.get("home", {}).get("objects", []):
            copied = dict(obj)
            if self.day_ended and copied.get("id") != "home_bed":
                continue
            if self.day_ended and copied.get("id") == "home_bed":
                copied["tts"] = "Bed. Sleep until morning."
            if copied.get("id") == "home_stove" and not self.day_ended:
                craftable = sum(
                    1 for rid in self.config.get("recipes", {})
                    if self.can_craft_recipe(rid)
                )
                copied["tts"] = f"Kitchen. Available recipes: {craftable}."
            objects.append(copied)

        if not self.day_ended:
            objects.extend(self.registry.collect("home.objects"))
        return objects + self.home_spatial_objects()

    def home_spatial_objects(self):
        bed_item = dict(id='home_scene_bed', type='home_hitbox', skip_grid=True,
                        x=13, y=19, width=9, height=9, hit_width=11, hit_height=10,
                        label='Bed', tts='Bed. Sleep until morning.', action='rest')
        if self.day_ended:
            return [bed_item]
        craftable = sum(1 for rid in self.config.get("recipes", {}) if self.can_craft_recipe(rid))
        return [
            bed_item,
            dict(id='home_scene_chest', type='home_hitbox', skip_grid=True,
                 x=30, y=19, width=11, height=8, hit_width=12, hit_height=9,
                 label='Research', tts='Research. Choose an upgrade.', action='open_research'),
            dict(id='home_scene_stove', type='home_hitbox', skip_grid=True,
                 x=46, y=19, width=11, height=8, hit_width=12, hit_height=9,
                 label='Kitchen', tts=f'Kitchen. Available recipes: {craftable}.', action='open_recipes'),
            *self.registry.collect("home.scene_objects"),
            dict(id='home_road_farm', type='home_hitbox', skip_grid=True,
                 x=2, y=26, width=5, height=7, hit_width=7, hit_height=9,
                 label='Farm', tts='Farm. Go west.', action='travel:farm'),
            dict(id='home_road_town', type='home_hitbox', skip_grid=True,
                 x=57, y=26, width=5, height=7, hit_width=7, hit_height=9,
                 label='Village', tts='Village. Go east.', action='travel:town'),
        ]

    def draw_home_scene(self):
        pad = self.dotpad
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
        for dx in (54, 55, 56):
            pad.set_dot(dx, 23)
            pad.set_dot(dx, 29)

        self.draw_icon_pattern(1, 26, (
            '001',
            '011',
            '111',
            '011',
            '001',
        ))
        self.draw_icon_pattern(58, 26, (
            '100',
            '110',
            '111',
            '110',
            '100',
        ))

        draw_solid_pattern = self.draw_solid_pattern

        draw_solid_pattern(13, 19, (
            '111111111',
            '110000011',
            '110111011',
            '111111111',
            '100000001',
            '111111111',
            '110111011',
            '111111111',
            '111111111',
        ))

        if self.day_ended:
            return

        draw_solid_pattern(30, 19, (
            '..1111111..',
            '11111011111',
            '11001010011',
            '11111111111',
            '10000000001',
            '11111111111',
            '11001110011',
            '11111111111',
        ))

        draw_solid_pattern(46, 19, (
            '....11111..',
            '...1110111.',
            '11111111111',
            '10001101011',
            '11111111111',
            '11011100011',
            '11011100011',
            '11111111111',
        ))
        self.registry.draw_slot("home.scene")

    def draw_solid_pattern(self, cx, cy, rows):
        """Centered pattern: '1' raises a dot, '0' clears it, any other character leaves it."""
        pad = self.dotpad
        w, h = len(rows[0]), len(rows)
        for r_idx, row in enumerate(rows):
            for c_idx, ch in enumerate(row):
                px = cx + c_idx - w // 2
                py = cy + r_idx - h // 2
                if ch == '1':
                    pad.set_dot(px, py, 1)
                elif ch == '0':
                    pad.set_dot(px, py, 0)

    def get_farm_objects(self):
        farm = self.config.get("farm", {})
        objects = []
        grid_positions = [
            (11, 10), (30, 10), (49, 10),
            (11, 27), (30, 27), (49, 27),
        ]

        for idx, plot in enumerate(self.get_unlocked_plot_defs()):
            obj = dict(plot)
            obj["type"] = "plot"
            if idx < len(grid_positions):
                px, py = grid_positions[idx]
                obj.update(x=px, y=py, width=16, height=14, hit_width=16, hit_height=14)
            state = self.farm_plots[plot["id"]]
            seed_id = state["seed_id"]

            if seed_id is None:
                obj["tts"] = f"{plot['label']}. Empty. Select to manage."
                obj["action"] = f"open_plot_detail:{plot['id']}"
            else:
                seed_label = self.get_seed_label(seed_id)
                needed = int(self.get_seed_config(seed_id).get("growth_days", 3))
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

    def draw_plot(self, obj):
        pad = self.dotpad
        cx, cy = round(obj["x"]), round(obj["y"])
        rx, ry = int(obj.get("width", 16)) // 2 - 1, int(obj.get("height", 14)) // 2 - 1
        pad.draw_box(cx, cy, 2 * rx, 2 * ry)

        state = self.farm_plots.get(obj["id"], self.new_plot_state())
        seed_id = state.get("seed_id")

        if not seed_id:
            for dy in (-3, 0, 3):
                for dx in range(-rx + 2, rx - 1, 2):
                    pad.set_dot(cx + dx, cy + dy)
            return

        if state.get("watered"):
            pad.draw_line(cx - rx + 1, cy + ry - 1, cx + rx - 1, cy + ry - 1)
        if state.get("fertilized"):
            pad.set_dot(cx - rx + 2, cy - ry + 2)
            pad.set_dot(cx + rx - 2, cy - ry + 2)

        growth = int(state.get("growth", 0))
        mature = bool(state.get("mature"))

        if mature:
            mature_patterns = {
                "tomato": (
                    "001010100",
                    "011111110",
                    "111101111",
                    "111000111",
                    "111101111",
                    "111111111",
                    "011111110",
                ),
                "carrot": (
                    "101010101",
                    "011111110",
                    "001111100",
                    "011111110",
                    "001111100",
                    "000111000",
                    "000010000",
                ),
                "potato": (
                    "011100110",
                    "111111111",
                    "110111011",
                    "011111110",
                    "111101111",
                    "111111111",
                    "011001110",
                ),
            }
            self.draw_icon_pattern(cx, cy, mature_patterns.get(seed_id, mature_patterns["tomato"]))
            return

        if growth <= 0:
            sprout_patterns = {
                "tomato": ("00100", "01110", "00100"),
                "carrot": ("10101", "01110", "00100"),
                "potato": ("01100", "11110", "00110"),
            }
            self.draw_icon_pattern(cx, cy + 1, sprout_patterns.get(seed_id, ("010", "111", "010")))
        else:
            mid_patterns = {
                "tomato": (
                    "0101010",
                    "1111111",
                    "0011100",
                    "0111110",
                    "0001000",
                ),
                "carrot": (
                    "1010101",
                    "0111110",
                    "0011100",
                    "0011100",
                    "0001000",
                ),
                "potato": (
                    "0011100",
                    "0111110",
                    "1110111",
                    "0111110",
                    "0110110",
                ),
            }
            self.draw_icon_pattern(cx, cy, mid_patterns.get(seed_id, mid_patterns["tomato"]))

    def get_plot_detail_objects(self):
        plot_id = self.detail_plot_id
        state = self.farm_plots.get(plot_id) if plot_id else None
        if state is None:
            return [self.back_arrow("plot_detail_back", "Back to farm", "return_scene")]

        plot_label = self.get_plot_label(plot_id)
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
                self.back_arrow("plot_detail_back", "Back to farm", "return_scene")
            ]

        seed_label = self.get_seed_label(seed_id)
        needed = int(self.get_seed_config(seed_id).get("growth_days", 3))
        water_text = "Watered" if state["watered"] else "Needs water"
        if state["fertilized"]:
            fertilizer_text = "Fertilized"
        elif int(self.resources.get("fertilizer", 0)) <= 0:
            fertilizer_text = "No fertilizer. Buy at the shop."
        else:
            fertilizer_text = f"Not fertilized. Stock: {self.resources.get('fertilizer', 0)} in stock"

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

            fertilizer_count = int(self.resources.get("fertilizer", 0))
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

        objects.append(self.back_arrow("plot_detail_back", "Back to farm", "return_scene"))
        return objects

    def get_care_minigame_objects(self):
        plot_id = self.detail_plot_id
        state = self.farm_plots.get(plot_id) if plot_id else None
        if state is None or state.get("seed_id") is None:
            return []
        seed_label = self.get_seed_label(state["seed_id"])
        mode_label = "Water" if self.care_mode == "water" else "Fertilizer"
        field = self.config.get("care_minigame", {}).get("field", {})
        objects = [{
            "id": "care_field", "type": "care_field",
            "x": int(field.get("x", 30)), "y": int(field.get("y", 20)),
            "width": int(field.get("width", 46)), "height": int(field.get("height", 30)),
            "hit_width": int(field.get("width", 46)), "hit_height": int(field.get("height", 30)),
            "label": f"{mode_label} plot",
            "tts": f" {seed_label} plot. Move to apply {mode_label}.",
            "action": ""
        }]
        for target in self.care_targets:
            if (target["id"] in self.care_collected_ids
                    and self.care_visible_until.get(target["id"], 0) <= time.monotonic()):
                continue
            objects.append({
                "id": target["id"], "type": "care_target", "care_kind": self.care_mode,
                "x": target["x"], "y": target["y"],
                "width": 5, "height": 5, "hit_width": 8, "hit_height": 8,
                "label": f"{mode_label} target",
                "tts": f"{mode_label} target. Move.",
                "action": ""
            })
        return objects

    def get_seed_select_objects(self):
        objects = []
        positions = [(12, 18), (30, 18), (48, 18)]
        available = []
        for seed_id, seed_config in self.config.get("seeds", {}).items():
            count = int(self.resources["seeds"].get(seed_id, 0))
            if count > 0:
                available.append((seed_id, seed_config, count))

        for index, (seed_id, seed_config, count) in enumerate(available[:len(positions)]):
            x, y = positions[index]
            yield_count = self.get_harvest_base_yield(seed_id)
            growth_days = int(seed_config.get("growth_days", 3))
            objects.append({
                "id": f"seed_{seed_id}", "type": "seed", "seed_id": seed_id,
                "x": x, "y": y, "width": 12, "height": 10,
                "hit_width": 15, "hit_height": 13,
                "label": f"{seed_config.get('label', seed_id)} seeds", "count": count,
                "tts": f"{seed_config.get('label', seed_id)} seeds {count}. Growth {growth_days} days, Harvest {yield_count}, Seed recovery level {self.research_levels.get('seed_return', 0)}",
                "action": f"plant:{self.seed_select_plot_id}:{seed_id}"
            })

        objects.append(self.back_arrow("seed_back", "Back to farm", "return_scene"))
        return objects

    @staticmethod
    def compress_axis(intervals, margin=2, max_gap=8):
        merged = []
        for low, high in sorted(intervals):
            if merged and low <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], high)
            else:
                merged.append([low, high])
        if not merged:
            return lambda value: value
        anchors = []
        target = margin
        previous_high = None
        for low, high in merged:
            if previous_high is not None:
                target += min(max_gap, low-previous_high)
            anchors.append((low, target))
            target += high-low
            anchors.append((high, target))
            previous_high = high
        def transform(value):
            if value <= anchors[0][0]: return value-anchors[0][0]+anchors[0][1]
            for (a, ta), (b, tb) in zip(anchors, anchors[1:]):
                if a <= value <= b and b > a:
                    return ta+(value-a)*(tb-ta)/(b-a)
            return value-anchors[-1][0]+anchors[-1][1]
        return transform

    def spatial_objects(self, objects):
        copied = [dict(o) for o in objects]
        if not copied: return copied
        def dims(o):
            if o.get("type") == "arrow":
                return (5,9) if o.get("direction") in ("left","right") else (9,5)
            return o.get("width",10), o.get("height",8)
        tx = self.compress_axis([(o["x"]-dims(o)[0]//2, o["x"]+(dims(o)[0]-1)//2) for o in copied], max_gap=5)
        ty = self.compress_axis([(o["y"]-dims(o)[1]//2, o["y"]+(dims(o)[1]-1)//2) for o in copied], max_gap=5)
        for o in copied:
            w,h=dims(o)
            o.update(x=round(tx(o["x"])), y=round(ty(o["y"])), hit_width=w, hit_height=h)
        return copied

    def get_harvest_objects(self):
        if self.harvest_plot_id is None:
            return []
        state = self.farm_plots.get(self.harvest_plot_id)
        if state is None or state["seed_id"] is None:
            return []
        seed_label = self.get_seed_label(state["seed_id"])
        field = self.config.get("harvest_minigame", {}).get("field", {})
        objects = [{
            "id": "harvest_field", "type": "harvest_field",
            "x": int(field.get("x", 30)), "y": int(field.get("y", 20)),
            "width": int(field.get("width", 46)), "height": int(field.get("height", 30)),
            "hit_width": int(field.get("width", 46)), "hit_height": int(field.get("height", 30)),
            "label": " Plot",
            "tts": f"Move over crops.",
            "action": ""
        }]
        for target in self.harvest_targets:
            if target["id"] in self.harvest_collected_ids:
                continue
            objects.append({
                "id": target["id"], "type": "harvest_crop", "x": target["x"], "y": target["y"],
                "width": 5, "height": 5, "hit_width": 7, "hit_height": 7,
                "label": f"Harvest {seed_label}", "tts": f"Harvest {seed_label}. Move.", "action": ""
            })
        return objects

    def get_recipe_select_objects(self):
        craftable = [(rid, cfg) for rid, cfg in self.config.get("recipes", {}).items() if not cfg.get("hidden_recipe") and self.can_craft_recipe(rid)]
        positions = [(0, 0)] * (self.icon_layout.grid.rows * self.icon_layout.grid.columns)
        objects = []
        for index, (recipe_id, recipe) in enumerate(craftable[:len(positions)]):
            x, y = positions[index]
            ingredient_text = self.recipe_ingredient_text(recipe_id)
            objects.append({
                "id": f"recipe_{recipe_id}", "type": "recipe", "recipe_id": recipe_id,
                "x": x, "y": y, "width": 12, "height": 9, "hit_width": 14, "hit_height": 11,
                "label": recipe.get("label", recipe_id),
                "tts": f"{recipe.get('label', recipe_id)}. {ingredient_text}. {self.recipe_effect_text(recipe)}",
                "action": f"select_recipe:{recipe_id}"
            })
        objects.append(self.back_arrow("recipe_back", "Back home", "return_scene"))
        return objects

    def get_ingredient_select_objects(self):
        recipe = self.get_recipe_config(self.selected_recipe_id)
        if not recipe:
            return [self.back_arrow("ingredient_back", "Back to kitchen", "open_recipes")]
        positions = [(15, 17), (30, 17), (45, 17)]
        objects = []
        for index, (seed_id, needed) in enumerate(recipe.get("ingredients", {}).items()):
            if index >= len(positions):
                break
            x, y = positions[index]
            selected = seed_id in self.selected_ingredients
            count = int(self.resources["crops"].get(seed_id, 0))
            label = self.get_seed_label(seed_id)
            status = "Selected" if selected else "Not selected"
            objects.append({
                "id": f"ingredient_{seed_id}", "type": "ingredient", "ingredient_id": seed_id,
                "count": count, "required_count": int(needed), "selected": selected, "x": x, "y": y, "width": 12, "height": 9,
                "hit_width": 14, "hit_height": 11, "label": f"{label} ingredient",
                "tts": f"{label}. Need {needed}, stock {count}. {status}",
                "action": f"toggle_ingredient:{seed_id}"
            })

        objects.append(self.back_arrow("ingredient_back", "Back to recipes", "open_recipes"))
        return self.seafood_ingredient_objects(objects)

    def get_cooking_objects(self):
        return []

    def get_shop_choice_objects(self):
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
        return base + self.shop_choice_spatial_objects()

    def shop_choice_spatial_objects(self):
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

    def draw_shop_choice_scene(self):
        pad = self.dotpad
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
        self.draw_icon_pattern(1, 26, (
            '001',
            '011',
            '111',
            '011',
            '001',
        ))

        def draw_solid_pattern(cx, cy, rows):
            w, h = len(rows[0]), len(rows)
            for r_idx, row in enumerate(rows):
                for c_idx, ch in enumerate(row):
                    px = cx + c_idx - w // 2
                    py = cy + r_idx - h // 2
                    if ch == '1':
                        pad.set_dot(px, py, 1)
                    elif ch == '0':
                        pad.set_dot(px, py, 0)

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

    def get_shop_buy_objects(self):
        entries = [("seed", seed_id, f"{self.get_seed_label(seed_id)} seeds", self.resources["seeds"].get(seed_id, 0),
                    int(seed.get("seed_price", max(1, round(int(seed.get("crop_price", 1)) * .8)))))
                   for seed_id, seed in self.config.get("seeds", {}).items()]
        entries += [("fertilizer", "fertilizer", "Fertilizer", self.resources["fertilizer"], self.get_fertilizer_price()),
                    ("pickaxe", "pickaxe", "Pickaxe", self.resources["pickaxe"], self.get_pickaxe_price())]
        entries += [("mineral", key, self.MINERAL_LABELS[key], self.resources[key], self.get_mineral_price(key, buying=True))
                    for key in ("stone", "copper", "iron")]
        entries.append(("fishing_rod", "fishing_rod", "Fishing rod", self.resources.get("fishing_rod",0), self.get_rod_price()))
        entries.extend(self.registry.collect("shop.buy_items"))
        return self.build_shop_objects(entries, "buy")

    def get_shop_sell_objects(self):
        entries = [("crop", key, f"{self.get_seed_label(key)} crops", self.resources["crops"].get(key, 0), int(seed.get("crop_price", 1)))
                   for key, seed in self.config.get("seeds", {}).items() if self.resources["crops"].get(key, 0) > 0]
        entries += [("food", key, recipe.get("label", key), self.resources["foods"].get(key, 0), self.get_food_sell_price(key))
                    for key, recipe in self.config.get("recipes", {}).items() if self.resources["foods"].get(key, 0) > 0]
        entries += [("mineral", key, label, self.resources[key], self.get_mineral_price(key))
                    for key, label in self.MINERAL_LABELS.items() if self.resources[key] > 0]
        entries += [("fish", key, fish['label'], self.resources['fish'].get(key,0), self.get_fish_price(key))
                    for key, fish in self.fishing_config()['fish'].items() if self.resources['fish'].get(key,0)>0]
        return self.build_shop_objects(entries, "sell")

    def back_arrow(self, object_id, label, action):
        return {
            "id": object_id, "type": "arrow", "x": 6, "y": 35,
            "direction": "left", "size": 2, "hit_width": 11, "hit_height": 9,
            "label": label, "tts": f"{label}.", "action": action
        }

    def recipe_ingredient_text(self, recipe_id):
        recipe = self.get_recipe_config(recipe_id)
        parts = []
        for seed_id, count in recipe.get("ingredients", {}).items():
            parts.append(f"{self.get_seed_label(seed_id)} {count} ")
        if recipe.get("seafood"): parts.append("Choose one fish")
        return ", ".join(parts)

    def get_relative_direction(self, origin, target):
        if origin is None:
            return ""
        dx = float(target["x"]) - float(origin["x"])
        dy = float(target["y"]) - float(origin["y"])
        if abs(dx) > 4 and abs(dy) > 4:
            horizontal = "right" if dx > 0 else "left"
            vertical = "down" if dy > 0 else "up"
            return f"{horizontal} {vertical}"
        if abs(dx) >= abs(dy):
            return "right" if dx > 0 else "left" if dx < 0 else ""
        return "down" if dy > 0 else "up" if dy < 0 else ""

    def render(self):
        self.dotpad.clear()
        if self.sleep_until is not None:
            self.timepad.clear()
            return
        for obj in self.get_objects():
            if self.icons.draw(obj):
                continue
            obj_type = obj.get("type")
            renderer = self.registry.renderers.get(obj_type)
            if renderer:
                renderer(obj)
            elif obj_type == "save_slot":
                self.dotpad.draw_box(obj["x"], obj["y"], obj["width"], obj["height"])
                self.dotpad.draw_box(obj["x"], obj["y"], 4, 4)
            elif obj_type == "arrow":
                self.draw_triangle(obj["x"], obj["y"], obj["direction"], obj.get("size", 2))
            elif obj_type == "box":
                self.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 6), obj.get("height", 5))
            elif obj_type == "bed":
                self.draw_bed(obj)
            elif obj_type == "chest":
                self.draw_chest(obj)
            elif obj_type == "stove":
                self.draw_stove(obj)
            elif obj_type == "plot":
                self.draw_plot(obj)
            elif obj_type == "watering_can":
                self.draw_watering_can(obj)
            elif obj_type == "fertilizer":
                self.draw_fertilizer(obj)
            elif obj_type == "seed":
                self.draw_seed(obj)
            elif obj_type == "resource":
                self.draw_resource(obj)
            elif obj_type == "plot_detail_field":
                self.draw_plot_detail_field(obj)
            elif obj_type == "growth_gauge":
                self.draw_plot_detail_gauge(obj)
            elif obj_type == "care_button":
                self.draw_care_button(obj)
            elif obj_type == "care_field":
                self.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 46), obj.get("height", 30))
            elif obj_type == "care_target":
                self.draw_care_target(obj)
            elif obj_type == "harvest_field":
                self.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 46), obj.get("height", 30))
            elif obj_type == "harvest_crop":
                self.draw_harvest_crop(obj)
            elif obj_type == "recipe":
                self.draw_recipe(obj)
            elif obj_type == "ingredient":
                self.draw_ingredient(obj)
            elif obj_type == "cooking_start":
                self.draw_cooking_start(obj)
            elif obj_type == "shop_npc":
                self.draw_shop_npc(obj)
            elif obj_type == "shop_choice":
                self.draw_shop_choice(obj)
            elif obj_type == "shop_item":
                self.draw_shop_item(obj)

        if self.current_page == "home":
            self.draw_home_scene()
        elif self.current_page == "shop_choice":
            self.draw_shop_choice_scene()
        elif self.current_page == "plot_detail":
            self.dotpad.draw_line(0, 12, self.dotpad.width - 1, 12)
            self.dotpad.draw_line(0, 13, self.dotpad.width - 1, 13)
        if self.current_page == "cooking":
            self.draw_cooking_path()
        scene = self.registry.page_hook(self.current_page, "scene")
        if scene:
            scene()
        self.draw_time_bar()

    def draw_triangle(self, x, y, direction, size=2):
        points = {(0,row) for row in range(9)}
        points.update((4-abs(row-4),row) for row in range(9))
        if direction == "left": points={(4-col,row) for col,row in points}
        elif direction == "up": points={(row,4-col) for col,row in points}
        elif direction == "down": points={(row,col) for col,row in points}
        elif direction != "right": raise ValueError("Unknown triangle direction")
        w,h = (5,9) if direction in ("left","right") else (9,5)
        for col,row in points:
            self.dotpad.set_dot(round(x)-w//2+col, round(y)-h//2+row)

    def draw_bed(self, obj):
        self.icons.draw(obj)

    def draw_chest(self, obj):
        self.icons.draw(obj)

    def draw_stove(self, obj):
        self.icons.draw(obj)

    @staticmethod
    def plot_bounds(obj):
        width, height = int(obj.get("width", 10)), int(obj.get("height", 8))
        return round(obj["x"])-width//2, round(obj["y"])-height//2, width, height

    def draw_plot_progress(self, obj, state):
        if state["seed_id"] is None: return
        needed = max(1, int(self.get_seed_config(state["seed_id"]).get("growth_days", 3)))
        ratio = 1.0 if state["mature"] else max(0.0, min(1.0, float(state["growth"]) / needed))
        left, top, width, height = self.plot_bounds(obj)
        rows = min(height-2, math.ceil((height-2)*ratio))
        for y in range(top+height-1-rows, top+height-1):
            for x in range(left+1, left+width-1): self.dotpad.set_dot(x, y)

    def draw_watering_can(self, obj):
        self.icons.draw(obj)

    def draw_fertilizer(self, obj):
        self.icons.draw(obj)

    def draw_seed(self, obj):
        self.icons.draw(obj)

    def draw_crop_symbol(self, x, y, seed_id):
        patterns = {
            "tomato": ["00100", "01010", "10001", "10001", "01110"],
            "carrot": ["10101", "01110", "01010", "00100", "00100"],
            "potato": ["11000", "10110", "01101", "00101", "00010"]
        }
        rows = patterns.get(seed_id, ["00100", "01110", "00100", "00000", "00000"])
        for j, row in enumerate(rows):
            for i, raised in enumerate(row):
                if raised == "1":
                    self.dotpad.set_dot(x + i - 2, y + j - 2)

    def draw_resource(self, obj):
        self.icons.draw(obj)

    def draw_filled_square(self, x, y, size=4):
        left, top = round(x)-size//2, round(y)-size//2
        for yy in range(top, top+size):
            for xx in range(left, left+size): self.dotpad.set_dot(xx, yy)

    def draw_icon_pattern(self, x, y, rows):
        if not rows:
            return
        width, height = max(map(len, rows)), len(rows)
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                if value == "1":
                    self.dotpad.set_dot(int(x) + column - width // 2, int(y) + row_index - height // 2)

    def draw_recipe_icon(self, x, y, recipe_id):
        self.draw_icon_pattern(x, y, self.get_recipe_config(recipe_id).get("icon", []))

    def draw_plot_detail_field(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        width, height = int(obj.get("width", 44)), int(obj.get("height", 18))
        self.dotpad.draw_box(x, y, width, height)
        plot_id = self.detail_plot_id
        state = self.farm_plots.get(plot_id) if plot_id else None
        if not state or state.get("seed_id") is None:
            return
        if state.get("mature"):
            for dx, dy in [(-8, 1), (-4, -2), (0, 2), (5, -1), (9, 2)]:
                for ox, oy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                    self.dotpad.set_dot(x + dx + ox, y + dy + oy)
        else:
            self.dotpad.set_dot(x, y)
            if state.get("watered"):
                self.dotpad.draw_line(x - 8, y + 5, x + 8, y + 5)
            if state.get("fertilized"):
                self.dotpad.set_dot(x - 10, y - 5)
                self.dotpad.set_dot(x + 10, y - 5)

    def draw_plot_detail_gauge(self, obj):
        plot_id = self.detail_plot_id
        state = self.farm_plots.get(plot_id) if plot_id else None
        if not state or state.get("seed_id") is None:
            return
        needed = max(1, int(self.get_seed_config(state["seed_id"]).get("growth_days", 3)))
        growth = needed if state.get("mature") else min(needed, int(state.get("growth", 0)))
        x1 = obj["x"] - obj["width"] // 2
        x2 = x1 + obj["width"] - 1
        y1 = obj["y"] - obj["height"] // 2
        y2 = y1 + obj["height"] - 1
        self.dotpad.draw_line(x1, y1, x2, y1)
        self.dotpad.draw_line(x2, y1, x2, y2)
        self.dotpad.draw_line(x2, y2, x1, y2)
        self.dotpad.draw_line(x1, y2, x1, y1)
        inner_width = x2 - x1 - 1
        fill = int(round(inner_width * growth / needed))
        for x in range(x1 + 1, x1 + 1 + fill):
            for y in range(y1 + 1, y2):
                self.dotpad.set_dot(x, y)

    def draw_care_button(self, obj):
        self.icons.draw(obj)

    def draw_care_target(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        if obj.get("care_kind") == "water":
            self.dotpad.set_dot(x, y - 1)
            self.dotpad.set_dot(x - 1, y)
            self.dotpad.set_dot(x, y)
            self.dotpad.set_dot(x + 1, y)
            self.dotpad.set_dot(x, y + 1)
        else:
            self.dotpad.set_dot(x - 1, y - 1)
            self.dotpad.set_dot(x + 1, y - 1)
            self.dotpad.set_dot(x - 1, y + 1)
            self.dotpad.set_dot(x + 1, y + 1)

    def draw_harvest_crop(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        for dx, dy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            self.dotpad.set_dot(x + dx, y + dy)

    def draw_recipe(self, obj):
        self.icons.draw(obj)

    def draw_ingredient(self, obj):
        self.icons.draw(obj)

    def draw_cooking_start(self, obj):
        self.icons.draw(obj)

    def cooking_resume_point(self):
        if not self.cooking_resume_marker or not self.cooking_path_samples:
            return None
        return self.cooking_path_samples[min(self.cooking_progress_index, len(self.cooking_path_samples) - 1)]

    def defer_visual_completion(self, kind, visible_until):
        deadline = max(visible_until.values(), default=0)
        if time.monotonic() >= deadline:
            return False
        self.pending_visual_completion = (deadline, kind)
        return True

    def visual_tick(self):
        if self.current_page == "load_game": return self.response()
        if self.sleep_until is not None:
            if time.monotonic() >= self.sleep_until:
                return self.finish_sleep()
            return self.response()
        if not self.paused and self.pending_visual_completion:
            deadline, kind = self.pending_visual_completion
            if time.monotonic() >= deadline:
                self.pending_visual_completion = None
                if kind == "care":
                    return self.finish_care_minigame()
                return self.complete_cooking_step()
        return self.response()

    def update_cooking_marker(self):
        if (self.current_page == "cooking" and not self.paused and self.cooking_dragging
                and self.cooking_last_progress_at is not None
                and time.monotonic() - self.cooking_last_progress_at >= self.resume_marker_delay_seconds
                and not self.cooking_resume_marker):
            self.cooking_resume_marker = True
            self.render()

    def draw_cooking_path(self):
        samples = self.cooking_path_samples
        if not samples:
            return
        progress = max(0, min(self.cooking_progress_index, len(samples)))
        visible_progress = next((i for i in range(progress)
                                 if self.cooking_visible_until.get(i, 0) > time.monotonic()), progress)
        remaining = samples[visible_progress:]
        if not remaining:
            return
        for start, end in zip(remaining, remaining[1:]):
            self.dotpad.draw_line(
                round(start[0]), round(start[1]),
                round(end[0]), round(end[1])
            )
        if visible_progress == 0:
            sx, sy = samples[0]
            self.draw_filled_square(sx, sy)
        resume = self.cooking_resume_point()
        if resume is not None:
            self.draw_filled_square(*resume)

    def draw_shop_npc(self, obj):
        self.icons.draw(obj)

    def draw_shop_choice(self, obj):
        self.icons.draw(obj)

    def draw_shop_item(self, obj):
        self.icons.draw(obj)

    def point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        nx, ny = x1 + t * dx, y1 + t * dy
        return ((px - nx) ** 2 + (py - ny) ** 2) ** 0.5

    def object_contains(self, obj, x, y):
        contains = self.registry.hit_tests.get(obj.get("type"))
        if contains:
            return contains(obj, x, y)
        half_width = obj.get("hit_width", obj.get("width", 8)) / 2
        half_height = obj.get("hit_height", obj.get("height", 8)) / 2
        return abs(x - obj["x"]) <= half_width and abs(y - obj["y"]) <= half_height

    def find_object(self, x, y):
        objects = self.get_objects()
        priority_types = ("care_target", "harvest_crop", "care_button", "growth_gauge", "plot", "seed", "ingredient", "recipe", "shop_item", "research", "node", "plot_detail_field")
        for obj_type in priority_types:
            for obj in objects:
                if obj.get("type") == obj_type and self.object_contains(obj, x, y):
                    return obj
        for obj in objects:
            if obj.get("type") != "route" and self.object_contains(obj, x, y):
                return obj
        for obj in objects:
            if obj.get("type") == "route" and self.object_contains(obj, x, y):
                return obj
        return None

    def find_farm_plot_at(self, x, y):
        for obj in self.get_objects():
            if obj.get("type") == "plot" and self.object_contains(obj, x, y):
                return obj
        return None
        
    def get_location_detail(self):
        loc = self.current_page
        detail = self.registry.page_hook(loc, "detail")
        if detail:
            return detail()
        if loc == "home":
            return "Home. Bed, Research, Kitchen, and Flower pot."
        elif loc == "farm":
            return "Farm. Choose a plot to manage your crops."
        elif loc == "town":
            return "Village. Shop and Rowan."
        elif loc == "inventory":
            return "Inventory. Select an item to use."
        elif loc == "shop_choice":
            return "Shop. Sell, Buy, Calendar, or Ask Rowan for advice."
        elif loc == "plot_detail":
            return "Plot details. Plant, water, or fertilize."
        elif loc == "seed_select":
            return "Seeds. Choose seeds to plant."
        elif loc == "recipe_select":
            return "Recipes. Choose a recipe to cook."
        elif loc == "ingredient_select":
            return "Ingredients. Select all ingredients to start cooking."
        elif loc == "cooking":
            return "Cooking. Start at the filled square and follow the line."
        return f"{self.get_page_name(loc)}."

    def get_object_tts(self, obj, detail=False):
        """Short hover: one target's name and its price/quantity only.

        Detailed inspection (Shift/hand gesture) is a separate read-only mode.
        Never derive the brief description by splitting verbose TTS sentences:
        prices, counts and actions may be buried in those sentences.
        """
        kind = obj.get("type")
        label = str(obj.get("label") or "Object").strip()
        if detail:
            return obj.get("tts") or label

        describe = self.registry.tts.get(kind)
        if describe:
            return describe(obj)

        # A map location, transition, building or navigation control has only
        # a name in standard hover, regardless of its verbose TTS.
        if kind in ("arrow", "home_hitbox", "shop_hitbox"):
            return label

        if kind in ("plot", "plot_detail_field"):
            plot_id = (self.detail_plot_id if kind == "plot_detail_field"
                       else obj.get("id"))
            state = self.farm_plots.get(plot_id) or {}
            plot_label = (self.get_plot_label(plot_id) if kind == "plot_detail_field"
                          and plot_id else label)
            seed_id = state.get("seed_id")
            return f"{plot_label}, {self.get_seed_label(seed_id)}." if seed_id else f"{plot_label}, empty."

        if kind == "shop_item":
            # shop_item.count means player-owned quantity; price is the
            # current market rate (already adjusted in build_shop_objects).
            price = obj.get("price")
            owned = obj.get("count")
            info = []
            if price is not None:
                info.append(f"{price} gold")
            if owned is not None:
                info.append(f"owned {owned}")
            return f"{label}, {', '.join(info)}." if info else label

        count = obj.get("count")
        if kind == "seed" and count is None:
            count = self.resources.get("seeds", {}).get(obj.get("seed_id"))
        if count is not None:
            return f"{label}, {count}."
        if obj.get("price") is not None:
            return f"{label}, {obj['price']} gold."
        return label

    def get_hover_sfx(self, obj):
        if obj.get("hover_sfx"):
            return obj["hover_sfx"]
        if obj.get("type") in self.registry.hover_sounds:
            return self.registry.hover_sounds[obj["type"]]
        mapping = {
            "bed": "hover_bed", "chest": "hover_chest", "stove": "hover_stove",
            "plot": "hover_plot",
            "watering_can": "hover_water_tool", "fertilizer": "hover_fertilizer",
            "seed": "hover_seed", "resource": "hover_resource",
            "harvest_crop": "hover_harvest_crop", "harvest_field": "hover_plot", "arrow": "hover_navigation",
            "recipe": "hover_recipe", "ingredient": "hover_ingredient", "cooking_start": "hover_cooking",
            "shop_npc": "hover_shop", "shop_choice": "hover_shop", "shop_item": "hover_shop_item",
            "plot_detail_field": "hover_plot", "growth_gauge": "hover_plot", "care_button": "hover_tool", "care_field": "hover_plot",
            "care_target": "hover_tool"
        }
        return mapping.get(obj.get("type"), "hover_object")

    def move_minigame(self, x, y):
        if self.paused or self.day_ended or self.sleep_until is not None or self.pending_visual_completion:
            self.last_pointer=(x,y)
            return self.response()
        px,py=self.last_pointer
        self.last_pointer=(x,y)
        if px is None or py is None: px,py=x,y
        if self.current_page=='cooking':
            if not self.cooking_dragging:
                if not self.cooking_path_samples:return self.response()
                index=min(self.cooking_progress_index,len(self.cooking_path_samples)-1)
                sx,sy=self.cooking_path_samples[index]
                tolerance=float(self.get_cooking_gesture().get('tolerance',4.5))*1.35
                if math.hypot(x-sx,y-sy)>tolerance:return self.response()
                return self.start_cooking_trace(x,y)
            return self.advance_cooking_trace(px,py,x,y)
        care=self.current_page in ('water_minigame','fertilizer_minigame')
        if care:
            self.care_dragging=True
            before=len(self.care_collected_ids)
            self.collect_care_segment(px,py,x,y)
            gained=len(self.care_collected_ids)-before
            complete=bool(self.care_targets) and len(self.care_collected_ids) == len(self.care_targets)
        else:
            self.harvest_dragging=True
            before=len(self.harvest_collected_ids)
            self.collect_harvest_segment(px,py,x,y)
            gained=len(self.harvest_collected_ids)-before
            complete=bool(self.harvest_targets) and len(self.harvest_collected_ids)==len(self.harvest_targets)
        if complete:
            result=self.finish_care_minigame() if care else self.finish_harvest_minigame()
        else:
            if gained:self.render()
            result=self.response(sfx=('care_spray' if care else 'harvest_collect') if gained else None)
        if gained:result.setdefault('sound_events',[]).append({'kind':'correct','count':gained})
        return result

    def page_pointer(self, kind, x, y):
        """Raw pointer input for a feature-owned page; None lets the core handler continue."""
        handler = self.registry.pointer(self.current_page, kind)
        return handler(x, y) if handler else None

    def pointer_move(self, x, y):
        result = self.page_pointer("move", x, y)
        if result is not None:
            return result
        if self.current_page in ('water_minigame','fertilizer_minigame','harvest','cooking'):
            return self.move_minigame(x,y)
        if self.sleep_until is not None:
            return self.response()
            
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()
            
        is_pointing = False  # Press/click does not double as detailed inspection.
        obj = self.find_object(x, y)
        
        if obj is None:
            self.hover_object_id = None
            self.last_hover_state = (None, is_pointing)
            if is_pointing and not getattr(self, 'location_detail_spoken', False):
                self.location_detail_spoken = True
                return self.response(tts=self.get_location_detail())
            return self.response()

        object_id = obj["id"]
        current_state = (object_id, is_pointing)

        if current_state != getattr(self, 'last_hover_state', (None, False)):
            self.last_hover_state = current_state
            self.hover_object_id = object_id
            tts_text = self.get_object_tts(obj, detail=is_pointing)
            return self.response(tts=tts_text, sfx=self.get_hover_sfx(obj))
            
        return self.response()

    def pointer_down(self, x, y):
        result = self.page_pointer("down", x, y)
        if result is not None:
            return result
        if self.current_page in ('water_minigame','fertilizer_minigame','harvest','cooking'):
            return self.move_minigame(x,y)
        if self.sleep_until is not None:
            return self.response()
        if self.pending_visual_completion:
            return self.response()

        self.location_detail_spoken = False
        self.last_hover_state = (None, True)

        single_press = self.registry.page_hook(self.current_page, "single_press")
        if single_press and self.pointer_pressed:
            return self.response()

        self.pointer_pressed = True
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()

        press = self.registry.page_hook(self.current_page, "press")
        if press:
            return press(x, y)

        if self.current_page in ("water_minigame", "fertilizer_minigame"):
            self.care_dragging = True
            before = len(self.care_collected_ids)
            collected = self.collect_care_point(x, y)
            if collected:
                self.render()
                return self.response(sfx="care_spray", sound_events=[{"kind": "correct", "count": len(self.care_collected_ids) - before}])
            mode_label = "Water " if self.care_mode == "water" else " fertilizer "
            return self.response(tts=f"{mode_label}. Move over targets.", sfx="tool_pickup")

        if self.current_page == "harvest":
            self.harvest_dragging = True
            before = len(self.harvest_collected_ids)
            collected = self.collect_harvest_point(x, y)
            if collected:
                self.render()
                return self.response(sfx="harvest_collect", sound_events=[{"kind": "correct", "count": len(self.harvest_collected_ids) - before}])
            return self.response(tts="Harvest. Move over crops.", sfx="tool_pickup")

        if self.current_page == "cooking":
            return self.start_cooking_trace(x, y)

        obj = self.find_object(x, y)
        if obj is None:
            return self.response()
        action = obj.get("action", "")

        if action.startswith("drag_tool:"):
            if self.day_ended:
                return self.night_only_response()
            self.drag_tool = action.split(":", 1)[1]
            self.drag_target_ids.clear()
            if self.drag_tool == "water":
                return self.response(tts="Watering can. Drag to a plot.", sfx="tool_pickup")
            if self.drag_tool == "fertilizer":
                count = int(self.resources.get("fertilizer", 0))
                if count <= 0:
                    self.drag_tool = None
                    return self.response(tts="No fertilizer.", sfx="error")
                return self.response(tts=f"Fertilizer. Stock: {count}. Drag to a watered plot.", sfx="tool_pickup")

        return self.perform_action(action, obj)

    def pointer_drag(self, x, y):
        result = self.page_pointer("drag", x, y)
        if result is not None:
            return result
        if self.current_page in ('water_minigame','fertilizer_minigame','harvest','cooking'):
            return self.move_minigame(x,y)
        if self.sleep_until is not None:
            return self.response()
        if self.pending_visual_completion:
            return self.response()
            
        previous_x, previous_y = self.last_pointer
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()

        if self.current_page in ("water_minigame", "fertilizer_minigame") and self.care_dragging:
            if previous_x is None or previous_y is None:
                previous_x, previous_y = x, y
            before = len(self.care_collected_ids)
            collected = self.collect_care_segment(previous_x, previous_y, x, y)
            if collected:
                self.render()
                return self.response(sfx="care_spray", sound_events=[{"kind": "correct", "count": len(self.care_collected_ids) - before}])
            return self.response()

        if self.current_page == "harvest" and self.harvest_dragging:
            if previous_x is None or previous_y is None:
                previous_x, previous_y = x, y
            before = len(self.harvest_collected_ids)
            collected = self.collect_harvest_segment(previous_x, previous_y, x, y)
            if collected:
                self.render()
                return self.response(sfx="harvest_collect", sound_events=[{"kind": "correct", "count": len(self.harvest_collected_ids) - before}])
            return self.response()

        if self.current_page == "cooking" and self.cooking_dragging:
            if previous_x is None or previous_y is None:
                previous_x, previous_y = x, y
            return self.advance_cooking_trace(previous_x, previous_y, x, y)

        if self.drag_tool is None:
            return self.pointer_move(x, y)

        plot = self.find_farm_plot_at(x, y)
        if plot is None:
            return self.response()
        plot_id = plot["id"]
        if plot_id in self.drag_target_ids:
            return self.response()
        self.drag_target_ids.add(plot_id)
        if self.drag_tool == "water":
            return self.water_plot(plot_id)
        if self.drag_tool == "fertilizer":
            return self.fertilize_plot(plot_id)
        return self.response()

    def pointer_up(self, x, y):
        result = self.page_pointer("up", x, y)
        if result is not None:
            return result
        if self.current_page in ('water_minigame','fertilizer_minigame','harvest','cooking'):
            self.pointer_pressed=False
            return self.response()
        if self.sleep_until is not None:
            return self.response()
            
        self.location_detail_spoken = False
        self.last_hover_state = (None, False)
        
        if self.paused:
            self.pointer_pressed = False
            self.care_dragging = self.harvest_dragging = self.cooking_dragging = False
            self.drag_tool = None
            return self.response()
            
        final = self.pointer_drag(x, y) if self.pointer_pressed else None
        self.pointer_pressed = False
        self.last_pointer = (x, y)
        
        if final and (final.get("sfx") in ("cooking_success", "cooking_step", "cooking_wait", "day_end")):
            final["state"] = self.get_state()
            return final
            
        if self.current_page in ("water_minigame", "fertilizer_minigame") and self.care_dragging:
            self.care_dragging = False
            result = self.finish_care_minigame()
        elif self.current_page == "harvest" and self.harvest_dragging:
            self.harvest_dragging = False
            result = self.finish_harvest_minigame()
        elif self.current_page == "cooking" and self.cooking_dragging:
            self.cooking_dragging = False
            result = self.fail_or_continue_cooking()
        else:
            self.drag_tool = None
            self.drag_target_ids.clear()
            result = self.response()
            
        if final:
            result["sound_events"] = final.get("sound_events", []) + result.get("sound_events", [])
        return result

    def perform_action(self, action, obj):
        before = (self.current_page, self.current_location, self.inventory_page, self.shop_page)
        result = self._perform_action(action, obj)
        after = (self.current_page, self.current_location, self.inventory_page, self.shop_page)
        if obj.get("type") == "arrow" and before != after:
            result.setdefault("sound_events", []).append({"kind": "one_shot", "sound": "step", "direction": obj.get("direction")})
        return result

    def _perform_action(self, action, obj):
        owned = self.registry.action_for(action, before_night_guard=True)
        if owned:
            handler, arg = owned
            return handler(arg, obj)
        if action == "close_load": return self.close_load_game()
        if action.startswith("load_slot:"): return self.load_game(action.split(":", 1)[1])
        if self.day_ended and action != "rest":
            return self.night_only_response()
        owned = self.registry.action_for(action, before_night_guard=False)
        if owned:
            handler, arg = owned
            return handler(arg, obj)
        if action.startswith("shop_page:"):
            if self.current_page not in ("shop_buy", "shop_sell"):
                return self.response()
            self.shop_page += int(action.split(":", 1)[1])
            self.clear_hover()
            self.render()
            return self.response(tts="Next page" if action.endswith(":1") else "Previous page")
        if action.startswith("travel:"):
            return self.travel_to(action.split(":", 1)[1])
        if action == "return_scene":
            return self.return_to_scene()
        if action == "open_recipes":
            return self.open_recipes()
        if action == "return_shop_choice":
            return self.return_to_shop_choice()
        if action == "open_shop":
            return self.open_shop()
        if action.startswith("shop_mode:"):
            return self.open_shop_mode(action.split(":", 1)[1])
        if action.startswith("buy:"):
            _, kind, item_id = action.split(":", 2)
            return self.buy_shop_item(kind, item_id)
        if action.startswith("sell:"):
            _, kind, item_id = action.split(":", 2)
            return self.sell_shop_item(kind, item_id)
        if action.startswith("open_plot_detail:"):
            return self.open_plot_detail(action.split(":", 1)[1])
        if action.startswith("start_care:"):
            _, mode, plot_id = action.split(":", 2)
            return self.start_care_minigame(plot_id, mode)
        if action.startswith("open_seed_select:"):
            return self.open_seed_select(action.split(":", 1)[1])
        if action.startswith("plant:"):
            _, plot_id, seed_id = action.split(":", 2)
            return self.plant_seed(plot_id, seed_id)
        if action.startswith("start_harvest:"):
            return self.start_harvest_minigame(action.split(":", 1)[1])
        if action.startswith("select_recipe:"):
            return self.select_recipe(action.split(":", 1)[1])
        if action.startswith("toggle_ingredient:"):
            return self.toggle_ingredient(action.split(":", 1)[1])
        if action == "start_cooking":
            return self.open_cooking_minigame()
        if action.startswith("use_food:"):
            return self.use_food(action.split(":", 1)[1])
        if action.startswith("inspect:"):
            return self.response(tts=self.get_object_tts(obj))
        if action == "rest":
            return self.next_day()
        return self.response(tts=self.get_object_tts(obj))

    def night_only_response(self):
        return self.response(tts="Night. Select the bed.", sfx="error")

    def travel_to(self, location):
        self.registry.run("before_navigation")
        if self.day_ended:
            return self.night_only_response()
        if location not in ("home", "farm", "town", "mine", "fishing"):
            return self.response(tts="Location unavailable.")
        self._menu_stack.clear()
        self.registry.run("close_dialogue")
        changed = location != self.current_location
        self.current_location = location
        self.current_page = location
        self.seed_select_plot_id = None
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.clear_hover()
        if changed:
            result = self.consume_time("travel")
            if result["night"]:
                return self.night_response()
        self.render()
        name = self.get_page_name(location)
        arrival = self.registry.page_hook(location, "arrival")
        text = arrival() if arrival else None
        if text:
            return self.response(tts=text, sfx="travel")
        return self.response(tts=f"{name}", sfx="travel")

    def navigate_key(self, direction):
        if self.current_page == 'load_game':
            if self.paused: return self.response(tts='Resume first.')
            if self.sleep_until is not None: return self.response(tts='Sleeping. Please wait.')
            return self.close_load_game()
        navigate = self.registry.page_hook(self.current_page, "navigate")
        if navigate:
            result = navigate(direction)
            if result is not None:
                return result
        return super().navigate_key(direction)

    def return_to_scene(self):
        self.registry.run("before_navigation")
        self.pointer_pressed = False
        self.current_page = "home" if self.day_ended else self.current_location
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_page_name(self.current_location)}.", sfx="open_page")

    def plot_status_text(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None:
            return "Plot unavailable."
        label = self.get_plot_label(plot_id)
        if not state.get("seed_id"):
            return f"{label}. Empty. Plant seeds."
        seed = self.get_seed_label(state["seed_id"])
        if state["mature"]:
            return f"{label}, {seed}. Ready to harvest"
        needed = int(self.get_seed_config(state["seed_id"]).get("growth_days", 3))
        water = "Watered" if state["watered"] else "Needs water"
        fertilizer = "Fertilized" if state["fertilized"] else "Not fertilized"
        return f"{label}, {seed}. Growth {state['growth']} of {needed} days. {water}. {fertilizer}"

    def open_plot_detail(self, plot_id):
        unlocked = {p["id"] for p in self.get_unlocked_plot_defs()}
        state = self.farm_plots.get(plot_id)
        if state is None or plot_id not in unlocked:
            return self.response(tts="Plot unavailable.", sfx="error")
        self.detail_plot_id = plot_id
        self.current_location = "farm"
        self.current_page = "plot_detail"
        self.clear_care(keep_detail=True)
        self.clear_harvest()
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_plot_label(plot_id)}.", sfx="open_page")

    def start_care_minigame(self, plot_id, mode):
        self.last_pointer = (None, None)
        state = self.farm_plots.get(plot_id)
        if state is None or state.get("seed_id") is None:
            return self.response(tts="Plant seeds first.", sfx="error")
        if state.get("mature"):
            return self.response(tts="Crop ready. Harvest now.", sfx="error")
        if mode == "water" and state.get("watered"):
            return self.response(tts="Already watered.", sfx="error")
        if mode == "fertilizer":
            if not state.get("watered"):
                return self.response(tts="Water first.", sfx="error")
            if state.get("fertilized"):
                return self.response(tts="Already fertilized.", sfx="error")
            if int(self.resources.get("fertilizer", 0)) <= 0:
                return self.response(tts="No fertilizer. Buy at the shop.", sfx="error")

        cfg = self.config.get("care_minigame", {})
        positions = [tuple(v) for v in cfg.get("target_positions", [])]
        target_count = min(int(cfg.get("target_count", 8)), len(positions))
        selected = random.sample(positions, target_count) if target_count else []
        self.detail_plot_id = plot_id
        self.care_mode = mode
        self.care_targets = [
            {"id": f"care_target_{i}", "x": x, "y": y}
            for i, (x, y) in enumerate(selected)
        ]
        self.care_collected_ids.clear()
        self.care_visible_until = {}
        self.care_dragging = False
        self.current_page = "water_minigame" if mode == "water" else "fertilizer_minigame"
        self.clear_hover()
        self.render()
        mode_label = "Water" if mode == "water" else "Fertilize"
        return self.response(
            tts=f"{mode_label}. Move over targets.",
            sfx="care_start"
        )

    def collect_care_point(self, x, y):
        collected = False
        tolerance = float(self.config.get("care_minigame", {}).get("tolerance", 4.0))
        for target in self.care_targets:
            if target["id"] not in self.care_collected_ids and math.hypot(x - target["x"], y - target["y"]) <= tolerance:
                self.care_collected_ids.add(target["id"])
                self.care_visible_until[target["id"]] = time.monotonic() + self.disappear_delay_seconds
                collected = True
        return collected

    def collect_care_segment(self, x1, y1, x2, y2):
        collected = False
        tolerance = float(self.config.get("care_minigame", {}).get("tolerance", 4.0))
        for target in self.care_targets:
            if target["id"] in self.care_collected_ids:
                continue
            if self.point_to_segment_distance(target["x"], target["y"], x1, y1, x2, y2) <= tolerance:
                self.care_collected_ids.add(target["id"])
                self.care_visible_until[target["id"]] = time.monotonic() + self.disappear_delay_seconds
                collected = True
        return collected

    def finish_care_minigame(self):
        if self.detail_plot_id is None or not self.care_targets:
            self.clear_care()
            return self.return_to_scene()
        total = len(self.care_targets)
        collected = len(self.care_collected_ids)
        mode = self.care_mode
        plot_id = self.detail_plot_id

        # All visible targets must be collected, regardless of the old
        # care_minigame.success_ratio configuration setting.
        if collected < total:
            self.render()
            mode_label = "Water" if mode == "water" else "Fertilizer"
            return self.response(
                tts=f"{mode_label} {collected} of {total}. Continue over remaining targets.",
                sfx="error"
            )

        if self.defer_visual_completion("care", self.care_visible_until):
            return self.response()

        state = self.farm_plots[plot_id]
        if mode == "water":
            state["watered"] = True
            action_name = "water"
            text = f"Watered. Sleep to grow crops."
            sfx = "water"
        else:
            count = int(self.resources.get("fertilizer", 0))
            if count <= 0:
                self.clear_care(keep_detail=True)
                self.current_page = "plot_detail"
                self.render()
                return self.response(tts="No fertilizer. Buy at the shop.", sfx="error")
            self.resources["fertilizer"] = count - 1
            fertilizer_text = self.apply_fertilizer_bonus(state)
            action_name = "fertilize"
            text = f"Fertilized. {fertilizer_text}.  fertilizer {self.resources['fertilizer']} remaining"
            sfx = "fertilize"

        self.clear_care(keep_detail=True)
        self.current_page = "plot_detail"
        self.clear_hover()
        result = self.consume_time(action_name)
        if result["night"]:
            return self.night_response(text)
        self.render()
        return self.response(tts=text, sfx=sfx)

    def open_seed_select(self, plot_id):
        if self.day_ended:
            return self.night_only_response()
        state = self.farm_plots.get(plot_id)
        unlocked = [p["id"] for p in self.get_unlocked_plot_defs()]
        if state is None or plot_id not in unlocked:
            return self.response(tts="Plot unavailable.", sfx="error")
        if state["seed_id"] is not None:
            return self.response(tts="Plot occupied.")
        if not any(int(count) > 0 for count in self.resources["seeds"].values()):
            return self.response(tts="No seeds. Buy at the shop.", sfx="error")
        self.seed_select_plot_id = plot_id
        self.current_page = "seed_select"
        self.clear_hover()
        self.render()
        return self.response(tts="Seeds.", sfx="open_page")

    def plant_seed(self, plot_id, seed_id):
        state = self.farm_plots.get(plot_id)
        seed_config = self.get_seed_config(seed_id)
        if state is None or not seed_config:
            return self.response(tts="Cannot plant here.", sfx="error")
        if state["seed_id"] is not None:
            return self.response(tts="Plot occupied.", sfx="error")
        count = int(self.resources["seeds"].get(seed_id, 0))
        if count <= 0:
            return self.response(tts="No seeds of this type.", sfx="error")
        self.resources["seeds"][seed_id] = count - 1
        self.farm_plots[plot_id] = self.new_plot_state()
        self.farm_plots[plot_id]["seed_id"] = seed_id
        self.detail_plot_id = plot_id
        self.current_page = "plot_detail"
        self.current_location = "farm"
        self.seed_select_plot_id = None
        self.clear_hover()
        result = self.consume_time("plant")
        if result["night"]:
            return self.night_response(f"{self.get_seed_label(seed_id)} planted.")
        self.render()
        return self.response(tts=f"{self.get_seed_label(seed_id)} planted. Water, then sleep.", sfx="plant")

    def water_plot(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None:
            return self.response()
        label = self.get_plot_label(plot_id)
        if state["seed_id"] is None:
            return self.response(tts=f"{label} is empty. Plant seeds first.", sfx="error")
        if state["mature"]:
            return self.response(tts=f"{label} is ready to harvest.", sfx="error")
        if state["watered"]:
            return self.response(tts=f"{label} Already watered.", sfx="error")
        state["watered"] = True
        result = self.consume_time("water")
        if result["night"]:
            return self.night_response(f"{label} watered")
        self.render()
        return self.response(tts=f"{label} watered. {self.get_seed_label(state['seed_id'])} will grow after sleep.", sfx="water")

    def apply_fertilizer_bonus(self, state):
        needed = int(self.get_seed_config(state["seed_id"]).get("growth_days", 3))
        bonus = max(0, int(self.config.get("fertilizer", {}).get("growth_day_bonus", 1)))
        before = state["growth"]
        state["growth"] = min(needed, before + bonus)
        state["fertilized"] = True
        state["mature"] = state["growth"] >= needed
        saved = state["growth"] - before
        remaining = max(0, needed - state["growth"])
        status = "Ready to harvest" if state["mature"] else f"Water, then sleep {remaining} more days to harvest."
        return f"Harvest {saved} days sooner. {status}"

    def fertilize_plot(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None:
            return self.response()
        label = self.get_plot_label(plot_id)
        if state["seed_id"] is None:
            return self.response(tts=f"{label} is empty. Plant first.", sfx="error")
        if state["mature"]:
            return self.response(tts=f"{label} is ready to harvest.", sfx="error")
        if not state["watered"]:
            return self.response(tts=f"{label} needs water first.", sfx="error")
        if state["fertilized"]:
            return self.response(tts=f"{label} is already fertilized.", sfx="error")
        count = int(self.resources.get("fertilizer", 0))
        if count <= 0:
            return self.response(tts="No fertilizer. Buy at the shop.", sfx="error")
        self.resources["fertilizer"] = count - 1
        fertilizer_text = self.apply_fertilizer_bonus(state)
        result = self.consume_time("fertilize")
        if result["night"]:
            return self.night_response(f"{label} fertilized.")
        self.render()
        return self.response(tts=f"{label} fertilized. {fertilizer_text}.  fertilizer {self.resources.get('fertilizer', 0)} remaining", sfx="fertilize")

    def get_effective_seed_return_chance(self, seed_id):
        cfg = self.config.get("research", {}).get("seed_return", {})
        level = int(self.research_levels.get("seed_return", 0))
        chances = cfg.get("return_chances", [0.3, 0.6])
        chance = chances[min(level - 1, len(chances) - 1)] if level > 0 else self.get_seed_config(seed_id).get("seed_return_chance", 0.0)
        return min(1.0, max(0.0, float(chance)))

    def start_harvest_minigame(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None or not state["mature"]:
            return self.response(tts="Crop not ready.", sfx="error")
        cfg = self.config.get("harvest_minigame", {})
        positions = [tuple(v) for v in cfg.get("target_positions", [])]
        target_count = min(int(cfg.get("target_count", 6)), len(positions))
        selected = random.sample(positions, target_count)
        self.harvest_plot_id = plot_id
        self.harvest_targets = [{"id": f"harvest_target_{i}", "x": x, "y": y} for i, (x, y) in enumerate(selected)]
        self.harvest_collected_ids.clear()
        self.harvest_dragging = False
        self.last_pointer = (None, None)
        self.current_page = "harvest"
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_seed_label(state['seed_id'])} harvest. Collect all crops.", sfx="harvest_start")

    def collect_harvest_point(self, x, y):
        collected = False
        for target in self.harvest_targets:
            if target["id"] not in self.harvest_collected_ids and abs(x - target["x"]) <= 3.5 and abs(y - target["y"]) <= 3.5:
                self.harvest_collected_ids.add(target["id"])
                collected = True
        return collected

    def collect_harvest_segment(self, x1, y1, x2, y2):
        collected = False
        for target in self.harvest_targets:
            if target["id"] in self.harvest_collected_ids:
                continue
            if self.point_to_segment_distance(target["x"], target["y"], x1, y1, x2, y2) <= 3.5:
                self.harvest_collected_ids.add(target["id"])
                collected = True
        return collected

    def finish_harvest_minigame(self):
        if self.harvest_plot_id is None or not self.harvest_targets:
            self.clear_harvest()
            return self.return_to_scene()
        collected = len(self.harvest_collected_ids)
        total = len(self.harvest_targets)
        if collected < total:
            self.render()
            return self.response(tts=f"Harvest {collected}/{total}. Collect remaining crops.")

        plot_id = self.harvest_plot_id
        state = self.farm_plots[plot_id]
        seed_id = state["seed_id"]
        seed_config = self.get_seed_config(seed_id)
        seed_label = self.get_seed_label(seed_id)
        base_yield = self.get_harvest_base_yield(seed_id)
        buff_multiplier = self.buff_multiplier_for("harvest_multiplier")
        buff_applied = buff_multiplier > 1.0
        yield_count = self.loot_amount(max(1, int(math.ceil(base_yield * buff_multiplier)))) + self.registry.total("harvest.bonus")
        self.resources["crops"][seed_id] = int(self.resources["crops"].get(seed_id, 0)) + yield_count

        chance = self.get_effective_seed_return_chance(seed_id)
        got_seed = random.random() < chance
        seed_count = self.loot_amount(1) if got_seed else 0
        if got_seed:
            self.resources["seeds"][seed_id] = int(self.resources["seeds"].get(seed_id, 0)) + seed_count

        self.farm_plots[plot_id] = self.new_plot_state()
        self.current_location = "farm"
        self.current_page = "farm"
        self.detail_plot_id = None
        self.clear_harvest()
        self.clear_hover()

        text = f"Harvested. {seed_label} {yield_count}."
        self.registry.run("activity", "harvest", seed_label, yield_count)
        if buff_applied:
            text += ". Harvest boost applied."
        if got_seed:
            text += f". {seed_count} seeds recovered."
        else:
            text += ". No seed recovered."

        result = self.consume_time("harvest")
        if result["night"]:
            return self.night_response(text)
        self.render()
        return self.response(tts=text, sfx="harvest")

    def open_recipes(self):
        if self.day_ended:
            return self.night_only_response()
        craftable = [rid for rid,cfg in self.config.get("recipes", {}).items() if not cfg.get("hidden_recipe") and self.can_craft_recipe(rid)]
        self.selected_recipe_id = None
        self.selected_ingredients.clear()
        self.current_page = "recipe_select"
        self.clear_hover()
        self.render()
        if not craftable:
            return self.response(tts="No recipes available. Gather ingredients.", sfx="open_page")
        names = ", ".join(self.get_recipe_label(rid) for rid in craftable)
        return self.response(tts="Recipes.", sfx="open_page")

    def select_recipe(self, recipe_id):
        if self.get_recipe_config(recipe_id).get("hidden_recipe") or not self.can_craft_recipe(recipe_id):
            return self.response(tts="Not enough ingredients.", sfx="error")
        self.selected_recipe_id = recipe_id
        self.selected_ingredients.clear()
        self.current_page = "ingredient_select"
        self.clear_hover()
        self.render()
        return self.response(tts="Ingredients.", sfx="open_page")

    def toggle_ingredient(self, seed_id):
        if self.current_page != "ingredient_select":
            return self.response()
        recipe = self.get_recipe_config(self.selected_recipe_id)
        if seed_id.startswith("fish:"): return self.toggle_fish(seed_id)
        if seed_id not in recipe.get("ingredients", {}):
            return self.response(tts="Ingredient not required.", sfx="error")
        if seed_id in self.selected_ingredients:
            self.selected_ingredients.remove(seed_id)
            text = f"{self.get_seed_label(seed_id)} deselected."
        else:
            self.selected_ingredients.add(seed_id)
            label = self.get_seed_label(seed_id)
            text = f"{label} selected."
        self.clear_hover()
        self.render()
        required = set(recipe.get("ingredients", {}).keys())
        if required and required.issubset(self.selected_ingredients) and (not recipe.get("seafood") or self.selected_fish()):
            self.pointer_pressed = False
            return self.open_cooking_minigame()
        return self.response(tts=text, sfx="ingredient_select")

    def get_cooking_steps(self):
        recipe = self.get_recipe_config(self.selected_recipe_id)
        steps = recipe.get("gesture_steps")
        steps = steps if steps else [recipe.get("gesture", {})]
        registry = self.config.get('cooking_methods', {}).get('gestures', {})
        return [copy.deepcopy(registry[step['method']]) if 'method' in step else step for step in steps]

    def get_scaled_cooking_gesture(self):
        steps = self.get_cooking_steps()
        gesture = steps[min(self.cooking_stage_index, len(steps) - 1)]
        path = gesture.get("path", [])
        if gesture.get("kind") != "stir" or len(path) < 2:
            return gesture
        xs, ys = [p[0] for p in path], [p[1] for p in path]
        span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
        if span_x <= 0 or span_y <= 0:
            return gesture
        width, height = self.config["dotpad"]["width"], self.config["dotpad"]["height"]
        scale = min(self.stir_scale, (width - 10) / span_x, (height - 10) / span_y)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        return {**gesture, "path": [
            [round((x - cx) * scale + (width - 1) / 2),
             round((y - cy) * scale + (height - 1) / 2)] for x, y in path
        ]}

    def get_cooking_gesture(self):
        gesture = dict(self.get_scaled_cooking_gesture())
        path = [list(p) for p in gesture.get("path", [])]
        if not path: return gesture
        if not gesture.get("closed") and len(path) > 2 and math.dist(path[0], path[-1]) < 8:
            while len(path) > 2 and math.dist(path[0], path[-1]) < 8:
                path.pop()
        gesture["path"] = path
        return gesture

    def get_cooking_kind(self):
        return "stir" if self.get_cooking_gesture().get("kind") in ("stir", "grill", "fry") else "cut"

    def get_cooking_stage_label(self):
        return self.get_cooking_gesture().get("label") or ("Stir" if self.get_cooking_kind() == "stir" else "Chop")

    def cooking_step_text(self):
        label = self.get_cooking_stage_label()
        return f"Step {self.cooking_stage_index + 1}. {label}. Start at the filled square. Follow the line."

    def complete_cooking_step(self):
        self.cooking_dragging = False
        if self.defer_visual_completion("cooking", self.cooking_visible_until):
            return self.response(sfx="cooking_wait")
        if self.cooking_stage_index + 1 >= len(self.get_cooking_steps()):
            return self.finish_cooking_success()
        self.last_pointer = (None, None)
        self.cooking_stage_index += 1
        self.cooking_last_progress_at = None
        self.cooking_resume_marker = False
        self.cooking_progress_index = 0
        self.cooking_visible_until = {}
        self.cooking_path_samples = self.build_path_samples(self.get_cooking_gesture().get("path", []))
        self.clear_hover()
        self.render()
        return self.response(tts= self.cooking_step_text(), sfx="cooking_step")

    def open_cooking_minigame(self):
        recipe = self.get_recipe_config(self.selected_recipe_id)
        if not recipe:
            return self.response(tts="Choose a recipe first.", sfx="error")
        required = set(recipe.get("ingredients", {}).keys())
        if recipe.get("seafood") and not self.seafood_ready(recipe, selected=True):
            return self.response(tts="Choose one fish first.")
        if not required.issubset(self.selected_ingredients):
            return self.response(tts="Select all ingredients first.", sfx="error")
        if not self.can_craft_recipe(self.selected_recipe_id):
            return self.response(tts="Not enough ingredients.", sfx="error")
        self.last_pointer = (None, None)
        self.current_page = "cooking"
        self.cooking_dragging = False
        self.cooking_progress_index = 0
        self.cooking_stage_index = 0
        self.cooking_last_progress_at = None
        self.cooking_resume_marker = False
        self.cooking_visible_until = {}
        self.cooking_path_samples = self.build_path_samples(self.get_cooking_gesture().get("path", []))
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_recipe_label(self.selected_recipe_id)}. {self.cooking_step_text()}.", sfx="cooking_start")

    def build_path_samples(self, path, spacing=1.5):
        if len(path) < 2:
            return [tuple(path[0])] if path else []
        samples = [tuple(path[0])]
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            length = math.hypot(x2 - x1, y2 - y1)
            steps = max(1, int(math.ceil(length / spacing)))
            for step in range(1, steps + 1):
                t = step / steps
                samples.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
        return samples

    def start_cooking_trace(self, x, y):
        if not self.cooking_path_samples:
            return self.response(tts="Cooking path unavailable.", sfx="error")
        recipe = self.get_recipe_config(self.selected_recipe_id)
        tolerance = float(self.get_cooking_gesture().get("tolerance", 4.5))
        resume_index = min(self.cooking_progress_index, len(self.cooking_path_samples) - 1)
        sx, sy = self.cooking_path_samples[resume_index]
        if math.hypot(x - sx, y - sy) > tolerance * 1.35:
            self.cooking_dragging = False
            return self.response(tts="Move to the filled square to continue.", sfx="error")
        self.cooking_dragging = True
        if self.cooking_progress_index == 0:
            self.cooking_visible_until[0] = time.monotonic() + self.disappear_delay_seconds
        self.cooking_progress_index = max(1, self.cooking_progress_index)
        self.cooking_last_progress_at = time.monotonic()
        self.cooking_resume_marker = False
        self.render()
        return self.response(sfx="tool_pickup", sound_events=[{"kind": "work_start", "sound": "cook" if self.get_cooking_kind() == "stir" else "cut"}])

    def advance_cooking_trace(self, x1, y1, x2, y2):
        if not self.cooking_path_samples:
            return self.response()
        recipe = self.get_recipe_config(self.selected_recipe_id)
        tolerance = float(self.get_cooking_gesture().get("tolerance", 4.5))
        if math.hypot(x2 - x1, y2 - y1) < 0.05:
            return self.response()
        before = self.cooking_progress_index
        advanced = False
        while self.cooking_progress_index < len(self.cooking_path_samples):
            px, py = self.cooking_path_samples[self.cooking_progress_index]
            if self.point_to_segment_distance(px, py, x1, y1, x2, y2) <= tolerance:
                self.cooking_visible_until[self.cooking_progress_index] = time.monotonic() + self.disappear_delay_seconds
                self.cooking_progress_index += 1
                advanced = True
            else:
                break
        if self.cooking_progress_index >= len(self.cooking_path_samples):
            gained = self.cooking_progress_index - before
            result = self.complete_cooking_step()
            result["sound_events"] = [{"kind": "correct", "activity": "cooking", "count": gained}]
            return result
        if advanced:
            self.cooking_last_progress_at = time.monotonic()
            self.cooking_resume_marker = False
            self.render()
            return self.response(sfx="cooking_trace", sound_events=[{"kind": "correct", "activity": "cooking", "count": self.cooking_progress_index - before}])
        return self.response()

    def fail_or_continue_cooking(self):
        total = len(self.cooking_path_samples)
        progress = self.cooking_progress_index
        percent = int(round((progress / total) * 100)) if total else 0
        self.cooking_resume_marker = progress > 0
        self.render()
        return self.response(tts=f"Progress {percent} percent.")

    def finish_cooking_success(self):
        recipe_id = self.selected_recipe_id
        recipe = self.get_recipe_config(recipe_id)
        if recipe.get("seafood"): return self.finish_seafood(recipe)
        if not recipe or not self.can_craft_recipe(recipe_id):
            self.clear_cooking()
            self.current_page = "home"
            self.current_location = "home"
            self.render()
            return self.response(tts="Not enough ingredients.", sfx="error")
        for seed_id, count in recipe.get("ingredients", {}).items():
            self.resources["crops"][seed_id] -= int(count)
        food_count = self.loot_amount(1)
        self.resources["foods"][recipe_id] = int(self.resources["foods"].get(recipe_id, 0)) + food_count
        label = self.get_recipe_label(recipe_id)
        self.current_location = "home"
        self.current_page = "home"
        self.clear_cooking()
        self.clear_hover()
        result = self.consume_time("cook")
        text = f"{label} {food_count} made." + (" Bonus." if food_count>1 else "")
        self.registry.run("activity", "cooking", label, food_count)
        if result["night"]:
            return self.night_response(text)
        self.render()
        return self.response(tts=text, sfx="cooking_success")

    def use_food(self, recipe_id):
        count = int(self.resources["foods"].get(recipe_id, 0))
        recipe = self.get_recipe_config(recipe_id)
        if count <= 0 or not recipe:
            return self.response(tts="No food available.", sfx="error")
        self.resources["foods"][recipe_id] = count - 1
        self.active_buff = {
            "kind": recipe.get("buff_kind", "harvest_multiplier"),
            "source": recipe_id,
            "multiplier": float(recipe.get("buff_multiplier", 1.0)),
            "remaining_ticks": float(recipe.get("buff_ticks", 0)),
            "remaining_sales": int(recipe.get("sale_uses", 0)),
            "rare_weight_multiplier": float(recipe.get("rare_weight_multiplier", 1)),
            "double_chance": float(recipe.get("double_chance", 0))
        }
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_recipe_label(recipe_id)} used. {self.buff_text()}", sfx="eat_food")

    def open_shop(self):
        self.registry.run("close_dialogue")
        if self.current_location != "town":
            self.current_location = "town"
        self.current_page = "shop_choice"
        self.clear_hover()
        self.render()
        return self.response(tts="Shop.", sfx="shop_open", sound_events=[{"kind": "one_shot", "sound": "door"}])

    def return_to_shop_choice(self):
        self.current_page = "shop_choice"
        self.shop_page = 0
        self.clear_hover()
        self.render()
        return self.response(tts="Shop.", sfx="open_page")

    def open_shop_mode(self, mode):
        self.shop_page = 0
        if mode == "sell":
            self.current_page = "shop_sell"
            text = "Sell."
        else:
            self.current_page = "shop_buy"
            text = "Buy."
        self.clear_hover()
        self.render()
        return self.response(tts=text, sfx="open_page")

    def buy_shop_item(self, kind, item_id):
        buyer = self.registry.shop_buyers.get(kind)
        if buyer:
            result = buyer(item_id)
            if result is not None: return result
        if kind == "seed":
            seed = self.get_seed_config(item_id)
            if not seed:
                return self.response(tts="Seed not sold here.", sfx="error")
            price = int(seed.get("seed_price", max(1, round(int(seed.get("crop_price", 1)) * 0.8))))
            label = f"{self.get_seed_label(item_id)} seeds"
        elif kind == "fertilizer":
            price = self.get_fertilizer_price()
            label = "Fertilizer"
        else:
            return self.response(tts="Item unavailable.", sfx="error")
        price = self.market_price(price, kind, "buy")
        if int(self.resources.get("coin", 0)) < price:
            return self.response(tts=f"Not enough gold. {label} costs {price} gold.", sfx="error")
        self.resources["coin"] -= price
        if kind == "seed":
            self.resources["seeds"][item_id] = int(self.resources["seeds"].get(item_id, 0)) + 1
            count = self.resources["seeds"][item_id]
        else:
            self.resources["fertilizer"] = int(self.resources.get("fertilizer", 0)) + 1
            count = self.resources["fertilizer"]
        self.clear_hover()
        self.render()
        return self.response(tts=f"{label} bought. Gold left: {self.resources['coin']} gold", sfx="shop_buy", sound_events=[{"kind": "one_shot", "sound": "coin"}] if price > 0 else [])

    def sell_shop_item(self, kind, item_id):
        if kind == "fish" and item_id in self.fishing_config()['fish']:
            if self.resources['fish'].get(item_id,0) < 1:
                return self.response(tts="No fish to sell.")
            fish = self.fishing_config()['fish'][item_id]
            price, label = self.get_fish_price(item_id), fish['label']
            self.resources['fish'][item_id] -= 1
        elif kind == "mineral" and item_id in self.MINERAL_LABELS:
            if self.resources[item_id] < 1:
                return self.response(tts="No mineral to sell.", sfx="error")
            price, label = self.get_mineral_price(item_id), self.MINERAL_LABELS[item_id]
            self.resources[item_id] -= 1
        elif kind == "crop":
            count = int(self.resources["crops"].get(item_id, 0))
            if count <= 0:
                return self.response(tts="No crop to sell.", sfx="error")
            price = int(self.get_seed_config(item_id).get("crop_price", 1))
            label = f"{self.get_seed_label(item_id)} crops"
            self.resources["crops"][item_id] = count - 1
        elif kind == "food":
            count = int(self.resources["foods"].get(item_id, 0))
            if count <= 0:
                return self.response(tts="No food to sell.", sfx="error")
            price = self.get_food_sell_price(item_id)
            label = self.get_recipe_label(item_id)
            self.resources["foods"][item_id] = count - 1
        else:
            return self.response(tts="Cannot sell this item.", sfx="error")
        price = self.market_price(price, kind, "sell")
        self.resources["coin"] += price
        self.consume_sale()
        self.clear_hover()
        self.render()
        return self.response(tts=f"{label} sold. Gold left: {self.resources['coin']} gold", sfx="shop_sell", sound_events=[{"kind": "one_shot", "sound": "coin"}] if price > 0 else [])

    def handle_command(self, command):
        command = str(command).lower().strip()
        command = {"f1":"minimap", "f2":"resources", "f3":"load", "f3_long":"save",
                   "f4":"click", "arrowleft":"left", "arrowright":"right"}.get(command, command)
        if command == "save":
            return self.save_game()
        if command == "load": return self.toggle_menu("load_game")
        if command == "minimap": return self.toggle_menu("minimap")
        if command == "resources": return self.toggle_menu("inventory")
        if command in ("left", "right"): return self.navigate_key(command)
        if command == "release":
            self.pointer_pressed = self.care_dragging = self.harvest_dragging = self.cooking_dragging = False
            self.drag_tool = None
            return self.response()
        if command in ("click", "pause"):
            x, y = self.last_pointer
            if x is None or y is None:
                return self.response(tts="Move to an item first.")
            result = self.pointer_down(x, y)
            self.pointer_pressed = False
            result["state"] = self.get_state()
            return result
        return self.response()

    def resource_summary_text(self):
        seed_total = sum(int(v) for v in self.resources["seeds"].values())
        crop_total = sum(int(v) for v in self.resources["crops"].values())
        food_total = sum(int(v) for v in self.resources["foods"].values())
        return f"Gold {self.resources.get('coin', 0)},  fertilizer {self.resources.get('fertilizer', 0)}, seeds {seed_total}, crops {crop_total}, food {food_total}. {self.buff_text()}"

    def response(self, tts=None, sfx=None, sound_events=None, speech_profile="system", priority=None):
        return {"tts": tts, "sfx": sfx, "sound_events": sound_events or [], "speech_profile": speech_profile,
                "priority": priority or ("hover" if (sfx or "").startswith("hover_") else "action"), "state": self.get_state()}

    def audio_guidance(self):
        kind, targets, completed, total = None, [], 0, 0
        if not (self.paused or self.day_ended or self.sleep_until is not None):
            if self.current_page in ("water_minigame", "fertilizer_minigame"):
                kind = "water" if self.care_mode == "water" else "soil"
                targets = [dict(target) for target in self.care_targets if target["id"] not in self.care_collected_ids]
                completed, total = len(self.care_collected_ids), len(self.care_targets)
            elif self.current_page == "harvest":
                kind = "crop"
                targets = [dict(target) for target in self.harvest_targets if target["id"] not in self.harvest_collected_ids]
                completed, total = len(self.harvest_collected_ids), len(self.harvest_targets)
            else:
                guidance = self.registry.page_hook(self.current_page, "guidance")
                if guidance:
                    kind, targets, completed, total = guidance()
        return {"kind": kind, "targets": targets, "completed": completed, "total": total}

    def get_state(self):
        self.update_cooking_marker()
        if self.current_page in ("water_minigame", "fertilizer_minigame", "cooking"):
            self.render()
        plots = {plot_id: dict(state) for plot_id, state in self.farm_plots.items()}
        objects = self.get_objects()
        return self.ordered_state({
            "spectator": spectator_snapshot(self, objects),
            "location_description": self.get_location_detail(),
            "inspect_objects": [
                {"id": o["id"], "type": o.get("type"), "label": o.get("label", ""),
                 "description": self.get_object_tts(o, detail=True),
                 "short_description": self.get_object_tts(o, detail=False),
                 "x": o.get("x"), "y": o.get("y"),
                 "width": o.get("width"), "height": o.get("height"),
                 "hit_width": o.get("hit_width"), "hit_height": o.get("hit_height"),
                 "x1": o.get("x1"), "y1": o.get("y1"),
                 "x2": o.get("x2"), "y2": o.get("y2"),
                 "hit_radius": o.get("hit_radius")}
                for o in objects
            ],
            "audio_guidance": self.audio_guidance(),
            "objects": [{"id": o["id"], "label": o.get("label", ""),
                         "type": o.get("type"), "x": o.get("x"), "y": o.get("y"),
                         "description": self.get_object_tts(o, detail=True),
                         "short_description": self.get_object_tts(o, detail=False),
                         "actionable": bool(o.get("action"))}
                        for o in objects if o.get("type") != "route"],
            "action_costs": {k: self.get_action_cost(k) for k in ("travel", "plant", "water", "fertilize", "harvest", "research", "cook", "mine", "fish")},
            "sleeping": self.sleep_until is not None,
            "client_settings": self.client_settings,
            "navigation": {d: bool(self.key_arrows(d)) for d in ("left", "right")},
            "page": self.current_page,
            "page_name": self.get_page_name(self.current_page),
            "current_location": self.current_location,
            "current_location_name": self.get_page_name(self.current_location),
            "day": self.day,
            "time": {
                "mode": "action",
                "used_cells": self.get_time_cells(),
                "total_cells": self.time_total_cells,
                "remaining_cells": max(0, self.time_total_cells - self.get_time_cells())
            },
            "day_ended": self.day_ended,
            "paused": self.paused,
            "resources": self.resources,
            "active_buff": dict(self.active_buff),
            "buff_text": self.buff_text(),
            "farm_plots": plots,
            "seed_select_plot_id": self.seed_select_plot_id,
            "drag_tool": self.drag_tool,
            "plot_detail_id": self.detail_plot_id,
            "care": {
                "mode": self.care_mode,
                "total_targets": len(self.care_targets),
                "collected_targets": len(self.care_collected_ids),
                "dragging": self.care_dragging
            },
            "harvest": {
                "plot_id": self.harvest_plot_id,
                "total_targets": len(self.harvest_targets),
                "collected_targets": len(self.harvest_collected_ids),
                "dragging": self.harvest_dragging
            },
            "cooking": {
                "resume_point": self.cooking_resume_point(),
                "stage_index": self.cooking_stage_index,
                "stage_count": len(self.get_cooking_steps()),
                "gesture_kind": self.get_cooking_kind(),
                "stage_label": self.get_cooking_stage_label(),
                "start_point": list(self.cooking_path_samples[0]) if self.cooking_path_samples else None,
                "recipe_id": self.selected_recipe_id,
                "recipe_name": self.get_recipe_label(self.selected_recipe_id) if self.selected_recipe_id else None,
                "selected_ingredients": list(self.selected_ingredients),
                "progress": self.cooking_progress_index,
                "total": len(self.cooking_path_samples),
                "dragging": self.cooking_dragging
            },
            "dots": self.dotpad.to_list(),
            "width": self.dotpad.width,
            "height": self.dotpad.height,
            "lower_panel": self.lower_panel_state(),
            "time_dots": self.timepad.to_list(),
            "time_width": self.timepad.width,
            "time_height": self.timepad.height,
            "pointer": {"x": self.last_pointer[0], "y": self.last_pointer[1], "pressed": self.pointer_pressed},
            "hover_object": self.hover_object_id,
            "controls": {"F1": "Map", "F2": "Inventory", "F3": "Load / hold to save", "F4": "Pause"}
        })

    # Key order of /api/state before features registered their own keys; new keys follow it.
    STATE_KEY_ORDER = (
        "spectator", "location_description", "inspect_objects", "dialogue", "rowan_submission", "calendar",
        "fishing", "flowers", "audio_guidance", "objects", "action_costs", "sleeping", "client_settings",
        "navigation", "page", "page_name", "current_location", "current_location_name", "day", "time",
        "day_ended", "paused", "resources", "active_buff", "buff_text", "research_levels",
        "unlocked_plot_count", "farm_plots", "seed_select_plot_id", "drag_tool", "plot_detail_id", "care",
        "harvest", "inventory", "cooking", "dots", "width", "height", "lower_panel", "time_dots",
        "time_width", "time_height", "pointer", "hover_object", "controls",
    )

    def ordered_state(self, state):
        for key, provider in self.registry.state_providers.items():
            if key in state:
                raise ValueError(f"State key {key!r} is provided by both core and a feature")
            state[key] = provider()
        ordered = {key: state.pop(key) for key in self.STATE_KEY_ORDER if key in state}
        ordered.update(state)
        return ordered

    MINERAL_LABELS = {"stone": "Stone", "copper": "Copper", "iron": "Iron", "diamond": "Diamond"}

    def get_fertilizer_price(self):
        cfg = self.config.get("fertilizer", {})
        return int(cfg.get("shop_price", cfg.get("price", self.config.get("shop", {}).get("fertilizer_price", 12))))

    def get_pickaxe_price(self):
        return int(math.ceil(self.get_fertilizer_price() * float(self.config.get("mine", {}).get("pickaxe_price_multiplier", 5))))

    def item_destroyed_event(self, item_id, reward_sound=None, loot_tts=None):
        self.registry.run("activity", "tool_broken", "Fishing rod" if item_id == "fishing_rod" else "Pickaxe")
        event = {"kind": "item_destroyed", "item_id": item_id}
        if reward_sound is not None:
            event.update(reward_sound=reward_sound, tts=loot_tts or "")
        return event

    def get_harvest_base_yield(self, seed_id):
        return int(self.get_seed_config(seed_id).get("yield", 1))

    def build_shop_objects(self, entries, mode):
        page_size = 12
        pages = max(1, math.ceil(len(entries) / page_size))
        self.shop_page_count = pages
        self.shop_page = max(0, min(self.shop_page, pages - 1))
        objects = []
        for i, (kind, item_id, label, count, price) in enumerate(entries[self.shop_page * page_size:(self.shop_page + 1) * page_size]):
            price = price if kind in self.registry.fixed_price_kinds else self.market_price(price, kind, mode)
            x, y = (9, 23, 37, 51)[i % 4], (5, 15, 25)[i // 4]
            text = f"{label}, {price} gold. stock {count} " if mode == "buy" else f"{label}, stock {count}. Sell {price} gold"
            if kind == "pickaxe" and count:
                text = "Pickaxe owned. Limit one."
            objects.append({"id": f"shop_{mode}_{kind}_{item_id}", "type": "shop_item", "shop_kind": kind, "item_id": item_id,
                            "x": x, "y": y, "width": 10, "height": 6, "hit_width": 10, "hit_height": 6,
                            "count": int(count), "price": int(price), "label": label, "tts": text, "action": f"{mode}:{kind}:{item_id}"})
        objects.append(self.back_arrow(f"shop_{mode}_back", "Back to shop", "return_shop_choice"))
        for delta, x, direction, label in [(-1, 30, "left", "Previous page"), (1, 51, "right", "Next page")]:
            if 0 <= self.shop_page + delta < pages:
                objects.append({"id": f"shop_page_{direction}", "type": "arrow", "x": x, "y": 35, "direction": direction,
                                "size": 2, "hit_width": 11, "hit_height": 7, "label": label, "action": f"shop_page:{delta}"})
        if not entries:
            objects.append({"id": "shop_empty", "type": "box", "x": 30, "y": 16, "width": 20, "height": 8,
                            "label": "Nothing to sell", "tts": "Nothing to sell.", "action": ""})
        return objects

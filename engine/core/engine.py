import copy

from pathlib import Path
from engine.core.effects import FoodEffects
from engine.core.input import InputDispatch
from engine.core.render import Rendering
from engine.core.time import TimeAndSleep
from engine.core.registry import Registry
from engine.core.state import SharedState
from engine.display.dotpad import DotPad
from engine.display.icons import IconGrid, IconLayout, IconRenderer
from engine.display.keypad import KeypadUI
from game import load_features
from engine.paths import SAVES_DIR
from engine.services.saves import SaveMixin
from engine.spectator.state import spectator_snapshot


class GameEngine(InputDispatch, KeypadUI, SaveMixin, SharedState, FoodEffects, TimeAndSleep, Rendering):

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
                 "shop_choice": "Shop", "shop_buy": "General goods", "shop_sell": "Sell"}
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
                               "vegetable_fritters": "Vegetable fritters", "rowan_soup": "Rowan's soup"}.get(key, recipe.get("label", key.replace("_", " ").title()))
            recipe["buff_label"] = {"harvest_multiplier": "Harvest boost", "pickaxe_protection": "Pickaxe protection",
                                    "research_discount": "Research discount", "time_slow": "Time saving"}.get(recipe.get("buff_kind"), recipe.get("buff_label", "Food effect"))
            for stage in recipe.get("gesture_steps", []):
                stage["label"] = "Crack eggs" if stage.get("kind") == "crack" else ("Trace eight petals" if key in ("vegetable_fritters", "fried_egg") else "Stir") if stage.get("kind") == "stir" else "Chop"
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
        objects = self.icon_layout.arrange(self.current_page, objects,
                                           self.dotpad.width, self.dotpad.height,
                                           types=self.icons.types, layout_order=self.registry.icon_layout_order,
                                           grid_pages=self.registry.icon_grid_pages(),
                                           only=self.registry.page_hook(self.current_page, "icon_only"))
        layout = self.registry.page_hook(self.current_page, "layout")
        if layout:
            layout(objects)
        return objects

    def reset(self):
        self._menu_stack = []
        self._load_return = None
        self._save_slots = []
        self.sleep_until = None
        self.pending_visual_completion = None
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

        self.drag_tool = None
        self.drag_target_ids = set()

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

    def clear_hover(self):
        self.hover_object_id = None
        self.last_hover_state = (None, False)
        self.location_detail_spoken = False

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

    def get_layout_objects(self):
        if self.sleep_until is not None:
            return []
        pages = {
            "load_game": self.get_load_objects,
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
            guidance = self.registry.page_hook(self.current_page, "guidance")
            if guidance:
                kind, targets, completed, total = guidance()
        return {"kind": kind, "targets": targets, "completed": completed, "total": total}

    def get_state(self):
        self.registry.run("before_state")
        if self.registry.page_hook(self.current_page, "live"):
            self.render()
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
            "drag_tool": self.drag_tool,
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

    def item_destroyed_event(self, item_id, reward_sound=None, loot_tts=None):
        self.registry.run("activity", "tool_broken", "Fishing rod" if item_id == "fishing_rod" else "Pickaxe")
        event = {"kind": "item_destroyed", "item_id": item_id}
        if reward_sound is not None:
            event.update(reward_sound=reward_sound, tts=loot_tts or "")
        return event

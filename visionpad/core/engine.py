import copy
import math
import random
import time

from pathlib import Path
from visionpad.core.effects import FoodEffects
from visionpad.core.registry import Registry
from visionpad.core.state import SharedState
from visionpad.display.dotpad import DotPad
from visionpad.display.icons import IconGrid, IconLayout, IconRenderer
from visionpad.display.keypad import KeypadUI
from visionpad.features import load_features
from visionpad.paths import SAVES_DIR
from visionpad.services.saves import SaveMixin
from visionpad.spectator.state import spectator_snapshot


class GameEngine(KeypadUI, SaveMixin, SharedState, FoodEffects):

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
        self.leave_activities()
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
        self.leave_activities()
        self.clear_hover()
        self.render()
        return self.response(tts="Sleeping.", sound_events=[{"kind": "one_shot", "sound": "sleep"}])

    def finish_sleep(self):
        notes = self.registry.run("end_of_day")
        self.sleep_until = None

        self.day += 1
        self.registry.run("start_of_day")
        self.time_used_cells = 0
        self.day_ended = False
        self.current_location = "home"
        self.current_page = "home"
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.leave_activities()
        self.clear_hover()
        self.render()

        text = f"Day {self.day}. Morning."
        for note in notes:
            text += f". {note}"
        return self.response(tts=text, sfx="morning")

    def lower_panel_state(self):
        if self.sleep_until is not None:
            return {"mode": "blank", "label": "Sleeping"}
        panel = self.registry.page_hook(self.current_page, "panel")
        page, pages, braille = panel() if panel else (0, 1, None)
        if pages > 1:
            return {"mode": "pages", "page": page + 1, "pages": pages,
                    "label": f"Page {page + 1} of {pages}"}
        if braille:
            return {"mode": "braille", "label": braille}
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

    def back_arrow(self, object_id, label, action):
        return {
            "id": object_id, "type": "arrow", "x": 6, "y": 35,
            "direction": "left", "size": 2, "hit_width": 11, "hit_height": 9,
            "label": label, "tts": f"{label}.", "action": action
        }

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
                return self.registry.visual_completions[kind]()
        return self.response()

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

    def get_location_detail(self):
        loc = self.current_page
        detail = self.registry.page_hook(loc, "detail")
        if detail:
            return detail()
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
        if kind == "arrow":
            return label

        count = obj.get("count")
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
        return "hover_navigation" if obj.get("type") == "arrow" else "hover_object"

    def minigame_input(self, x, y, step):
        """Pointer input on a tracing minigame page. Blocked while paused, at night, asleep or while a
        step finishes; otherwise step(px, py, x, y) gets the previous and the current point."""
        if self.paused or self.day_ended or self.sleep_until is not None or self.pending_visual_completion:
            self.last_pointer=(x,y)
            return self.response()
        px,py=self.last_pointer
        self.last_pointer=(x,y)
        if px is None or py is None: px,py=x,y
        return step(px, py, x, y)

    def minigame_release(self, x, y):
        self.pointer_pressed=False
        return self.response()

    def release_pointer(self):
        """Drop the pointer and any held drag (menus, save, pause, release command)."""
        self.pointer_pressed = False
        self.registry.run("release_drag")
        self.drag_tool = None

    def leave_activities(self):
        self.registry.run("leave_activity")

    def page_pointer(self, kind, x, y):
        """Raw pointer input for a feature-owned page; None lets the core handler continue."""
        handler = self.registry.pointer(self.current_page, kind)
        return handler(x, y) if handler else None

    def pointer_move(self, x, y):
        result = self.page_pointer("move", x, y)
        if result is not None:
            return result
        if self.current_page in ('water_minigame','fertilizer_minigame'):
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

        obj = self.find_object(x, y)
        if obj is None:
            return self.response()
        action = obj.get("action", "")
        return self.perform_action(action, obj)

    def pointer_drag(self, x, y):
        result = self.page_pointer("drag", x, y)
        if result is not None:
            return result
        if self.sleep_until is not None:
            return self.response()
        if self.pending_visual_completion:
            return self.response()

        previous_x, previous_y = self.last_pointer
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()

        if self.drag_tool is None:
            return self.pointer_move(x, y)
        drop = self.registry.drag_tools.get(self.drag_tool)
        return drop(x, y) if drop else self.response()

    def pointer_up(self, x, y):
        result = self.page_pointer("up", x, y)
        if result is not None:
            return result
        if self.sleep_until is not None:
            return self.response()

        self.location_detail_spoken = False
        self.last_hover_state = (None, False)

        if self.paused:
            self.release_pointer()
            return self.response()

        final = self.pointer_drag(x, y) if self.pointer_pressed else None
        self.pointer_pressed = False
        self.last_pointer = (x, y)

        if final and (final.get("sfx") in ("cooking_success", "cooking_step", "cooking_wait", "day_end")):
            final["state"] = self.get_state()
            return final

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
        if action.startswith("travel:"):
            return self.travel_to(action.split(":", 1)[1])
        if action == "return_scene":
            return self.return_to_scene()
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
        self.leave_activities()
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
        self.leave_activities()
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_page_name(self.current_location)}.", sfx="open_page")

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
            self.release_pointer()
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

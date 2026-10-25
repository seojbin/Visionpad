"""Cooking: recipes, ingredient selection, the traced cutting/stirring minigame, and eating food.

Engine attributes (save format): selected_recipe_id, selected_ingredients, cooking_dragging,
cooking_path_samples, cooking_visible_until, cooking_progress_index, cooking_stage_index,
cooking_last_progress_at, cooking_resume_marker.
Shared state written: resources crops/foods, current_page/current_location, last_pointer,
pointer_pressed, pending_visual_completion; starts food effects (core effects); spends time.
Paired with seafood: seafood recipes call the exposed seafood functions, and seafood calls
open_cooking_minigame / clear_cooking here.
"""
import copy
import math
import time

from engine.core import order
from engine.core.registry import Feature

STATE_FIELDS = ("selected_recipe_id", "selected_ingredients", "cooking_dragging", "cooking_path_samples",
                "cooking_visible_until", "cooking_progress_index", "cooking_stage_index",
                "cooking_last_progress_at", "cooking_resume_marker")


class Cooking(Feature):
    name = "cooking"

    def register(self, reg):
        reg.owns(*STATE_FIELDS)
        reg.page("recipe_select", objects=self.recipe_objects, icon_grid=True,
                 detail=lambda: "Recipes. Choose a recipe to cook.")
        reg.page("ingredient_select", objects=self.ingredient_objects, icon_grid=True,
                 detail=lambda: "Ingredients. Select all ingredients to start cooking.")
        reg.page("cooking", objects=self.cooking_objects, scene=self.draw_path, live=True,
                 detail=lambda: "Cooking. Start at the filled square and follow the line.",
                 pointer_move=self.move, pointer_down=self.move, pointer_drag=self.move,
                 pointer_up=self.engine.minigame_release)
        reg.action("open_recipes", lambda arg, obj: self.open_recipes())
        reg.action("select_recipe:", lambda arg, obj: self.select_recipe(arg))
        reg.action("toggle_ingredient:", lambda arg, obj: self.toggle_ingredient(arg))
        reg.action("start_cooking", lambda arg, obj: self.open_minigame())
        reg.action("use_food:", lambda arg, obj: self.use_food(arg))
        reg.icon("recipe", symbol=lambda obj: 'food')
        reg.icon("ingredient", symbol=lambda obj: 'check' if obj.get('selected') else self.engine.icons.category(obj.get('item_kind','crop')))
        reg.icon("cooking_start", symbol=lambda obj: 'start')
        reg.hover_sfx("recipe", "hover_recipe")
        reg.hover_sfx("ingredient", "hover_ingredient")
        reg.hover_sfx("cooking_start", "hover_cooking")
        reg.visual_completion("cooking", self.complete_step)
        reg.state("cooking", self.public_state)
        reg.spectator("path", self.spectator_path)
        reg.contribute("inventory.items", self.inventory_items, order=order.InventoryItems.COOKING)
        reg.contribute("shop.sell_items", self.shop_sell_rows, order=order.ShopSellItems.COOKING)
        reg.shop_item("food", sell=self.sell_food)
        reg.on("reset", self.reset, order=order.Reset.COOKING)
        reg.on("leave_activity", self.clear, order=order.LeaveActivity.COOKING)
        reg.on("release_drag", self.release)
        reg.on("before_state", self.update_marker)
        reg.save_fields(transient={"cooking_dragging": False}, clock=("cooking_last_progress_at",),
                        clock_maps=("cooking_visible_until",))
        reg.expose("can_craft_recipe", self.can_craft)
        reg.expose("open_cooking_minigame", self.open_minigame)
        reg.expose("clear_cooking", self.clear)
        reg.expose("finish_cooking_success", self.finish_success)
        reg.expose("get_cooking_gesture", self.gesture)
        reg.expose("use_food", self.use_food)

    def reset(self):
        e = self.engine
        e.selected_recipe_id = None
        e.selected_ingredients = set()
        e.cooking_dragging = False
        e.cooking_path_samples = []
        e.cooking_visible_until = {}
        e.cooking_progress_index = 0
        e.cooking_stage_index = 0
        e.cooking_last_progress_at = None
        e.cooking_resume_marker = False

    def release(self):
        self.engine.cooking_dragging = False

    def move(self, x, y):
        """Pointer move, press and drag on the cooking page: start at the filled square, then trace."""
        return self.engine.minigame_input(x, y, self.trace_step)

    def trace_step(self, px, py, x, y):
        e = self.engine
        if not e.cooking_dragging:
            if not e.cooking_path_samples:return e.response()
            index=min(e.cooking_progress_index,len(e.cooking_path_samples)-1)
            sx,sy=e.cooking_path_samples[index]
            tolerance=float(self.gesture().get('tolerance',4.5))*1.35
            if math.hypot(x-sx,y-sy)>tolerance:return e.response()
            return self.start_trace(x,y)
        return self.advance_trace(px,py,x,y)

    def public_state(self):
        e = self.engine
        return {
            "resume_point": self.resume_point(),
            "stage_index": e.cooking_stage_index,
            "stage_count": len(self.steps()),
            "gesture_kind": self.kind(),
            "stage_label": self.stage_label(),
            "start_point": list(e.cooking_path_samples[0]) if e.cooking_path_samples else None,
            "recipe_id": e.selected_recipe_id,
            "recipe_name": e.get_recipe_label(e.selected_recipe_id) if e.selected_recipe_id else None,
            "selected_ingredients": list(e.selected_ingredients),
            "progress": e.cooking_progress_index,
            "total": len(e.cooking_path_samples),
            "dragging": e.cooking_dragging
        }

    def spectator_path(self, objects):
        e = self.engine
        now = time.monotonic()
        return [dict(x=p[0], y=p[1], passed=i < e.cooking_progress_index,
                     visible=i >= e.cooking_progress_index or e.cooking_visible_until.get(i, 0) > now)
                for i, p in enumerate(e.cooking_path_samples)]

    def inventory_items(self):
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

    def food_sell_price(self, recipe_id):
        e = self.engine
        recipe = e.get_recipe_config(recipe_id)
        if recipe.get("sell_price") is not None: return int(recipe["sell_price"])
        ingredient_total = 0
        for seed_id, count in recipe.get("ingredients", {}).items():
            crop_price = int(e.get_seed_config(seed_id).get("crop_price", 1))
            ingredient_total += crop_price * int(count)
        if recipe.get('seafood'):
            prices=[e.get_fish_price(k) for k,v in e.fishing_config()['fish'].items() if v['grade']==recipe.get('fish_grade','low')]
            ingredient_total += min(prices)*recipe.get('fish_required',1)
        return max(1, int(math.ceil(ingredient_total * 1.2)))

    def shop_sell_rows(self):
        e = self.engine
        return [("food", key, recipe.get("label", key), e.resources["foods"].get(key, 0), self.food_sell_price(key))
                for key, recipe in e.config.get("recipes", {}).items() if e.resources["foods"].get(key, 0) > 0]

    def sell_food(self, item_id):
        e = self.engine
        count = int(e.resources["foods"].get(item_id, 0))
        if count <= 0:
            return e.response(tts="No food to sell.", sfx="error")
        price = self.food_sell_price(item_id)
        label = e.get_recipe_label(item_id)
        e.resources["foods"][item_id] = count - 1
        return price, label

    def clear(self, keep_recipe=False):
        e = self.engine
        if e.pending_visual_completion and e.pending_visual_completion[1] == "cooking":
            e.pending_visual_completion = None
        if not keep_recipe:
            e.selected_recipe_id = None
            e.selected_ingredients.clear()
        e.cooking_dragging = False
        e.cooking_path_samples = []
        e.cooking_visible_until = {}
        e.cooking_progress_index = 0
        e.cooking_stage_index = 0
        e.cooking_last_progress_at = None
        e.cooking_resume_marker = False

    def can_craft(self, recipe_id):
        e = self.engine
        recipe = e.get_recipe_config(recipe_id)
        if recipe.get("quest_only"): return False
        ingredients = recipe.get("ingredients", {})
        if recipe.get("seafood"): return e.seafood_ready(recipe)
        if len(ingredients) < 2:
            return False
        for seed_id, needed in ingredients.items():
            if int(e.resources["crops"].get(seed_id, 0)) < int(needed):
                return False
        return True

    def recipe_objects(self):
        e = self.engine
        craftable = [(rid, cfg) for rid, cfg in e.config.get("recipes", {}).items() if not cfg.get("hidden_recipe") and self.can_craft(rid)]
        positions = [(0, 0)] * (e.icon_layout.grid.rows * e.icon_layout.grid.columns)
        objects = []
        for index, (recipe_id, recipe) in enumerate(craftable[:len(positions)]):
            x, y = positions[index]
            ingredient_text = self.ingredient_text(recipe_id)
            objects.append({
                "id": f"recipe_{recipe_id}", "type": "recipe", "recipe_id": recipe_id,
                "x": x, "y": y, "width": 12, "height": 9, "hit_width": 14, "hit_height": 11,
                "label": recipe.get("label", recipe_id),
                "tts": f"{recipe.get('label', recipe_id)}. {ingredient_text}. {e.recipe_effect_text(recipe)}",
                "action": f"select_recipe:{recipe_id}"
            })
        objects.append(e.back_arrow("recipe_back", "Back home", "return_scene"))
        return objects

    def ingredient_objects(self):
        e = self.engine
        recipe = e.get_recipe_config(e.selected_recipe_id)
        if not recipe:
            return [e.back_arrow("ingredient_back", "Back to kitchen", "open_recipes")]
        positions = [(15, 17), (30, 17), (45, 17)]
        objects = []
        for index, (seed_id, needed) in enumerate(recipe.get("ingredients", {}).items()):
            if index >= len(positions):
                break
            x, y = positions[index]
            selected = seed_id in e.selected_ingredients
            count = int(e.resources["crops"].get(seed_id, 0))
            label = e.get_seed_label(seed_id)
            status = "Selected" if selected else "Not selected"
            objects.append({
                "id": f"ingredient_{seed_id}", "type": "ingredient", "ingredient_id": seed_id,
                "count": count, "required_count": int(needed), "selected": selected, "x": x, "y": y, "width": 12, "height": 9,
                "hit_width": 14, "hit_height": 11, "label": f"{label} ingredient",
                "tts": f"{label}. Need {needed}, stock {count}. {status}",
                "action": f"toggle_ingredient:{seed_id}"
            })

        objects.append(e.back_arrow("ingredient_back", "Back to recipes", "open_recipes"))
        return e.seafood_ingredient_objects(objects)

    def cooking_objects(self):
        return []

    def ingredient_text(self, recipe_id):
        e = self.engine
        recipe = e.get_recipe_config(recipe_id)
        parts = []
        for seed_id, count in recipe.get("ingredients", {}).items():
            parts.append(f"{e.get_seed_label(seed_id)} {count} ")
        if recipe.get("seafood"): parts.append("Choose one fish")
        return ", ".join(parts)

    def draw_recipe_icon(self, x, y, recipe_id):
        e = self.engine
        e.draw_icon_pattern(x, y, e.get_recipe_config(recipe_id).get("icon", []))

    def resume_point(self):
        e = self.engine
        if not e.cooking_resume_marker or not e.cooking_path_samples:
            return None
        return e.cooking_path_samples[min(e.cooking_progress_index, len(e.cooking_path_samples) - 1)]

    def update_marker(self):
        e = self.engine
        if (e.current_page == "cooking" and not e.paused and e.cooking_dragging
                and e.cooking_last_progress_at is not None
                and time.monotonic() - e.cooking_last_progress_at >= e.resume_marker_delay_seconds
                and not e.cooking_resume_marker):
            e.cooking_resume_marker = True
            e.render()

    def draw_path(self):
        e = self.engine
        samples = e.cooking_path_samples
        if not samples:
            return
        progress = max(0, min(e.cooking_progress_index, len(samples)))
        visible_progress = next((i for i in range(progress)
                                 if e.cooking_visible_until.get(i, 0) > time.monotonic()), progress)
        remaining = samples[visible_progress:]
        if not remaining:
            return
        for start, end in zip(remaining, remaining[1:]):
            e.dotpad.draw_line(
                round(start[0]), round(start[1]),
                round(end[0]), round(end[1])
            )
        if visible_progress == 0:
            sx, sy = samples[0]
            e.draw_filled_square(sx, sy)
        resume = self.resume_point()
        if resume is not None:
            e.draw_filled_square(*resume)

    def open_recipes(self):
        e = self.engine
        if e.day_ended:
            return e.night_only_response()
        craftable = [rid for rid,cfg in e.config.get("recipes", {}).items() if not cfg.get("hidden_recipe") and self.can_craft(rid)]
        e.selected_recipe_id = None
        e.selected_ingredients.clear()
        e.set_page("recipe_select")
        e.clear_hover()
        e.render()
        if not craftable:
            return e.response(tts="No recipes available. Gather ingredients.", sfx="open_page")
        names = ", ".join(e.get_recipe_label(rid) for rid in craftable)
        return e.response(tts="Recipes.", sfx="open_page")

    def select_recipe(self, recipe_id):
        e = self.engine
        if e.get_recipe_config(recipe_id).get("hidden_recipe") or not self.can_craft(recipe_id):
            return e.response(tts="Not enough ingredients.", sfx="error")
        e.selected_recipe_id = recipe_id
        e.selected_ingredients.clear()
        e.set_page("ingredient_select")
        e.clear_hover()
        e.render()
        return e.response(tts="Ingredients.", sfx="open_page")

    def toggle_ingredient(self, seed_id):
        e = self.engine
        if e.current_page != "ingredient_select":
            return e.response()
        recipe = e.get_recipe_config(e.selected_recipe_id)
        if seed_id.startswith("fish:"): return e.toggle_fish(seed_id)
        if seed_id not in recipe.get("ingredients", {}):
            return e.response(tts="Ingredient not required.", sfx="error")
        if seed_id in e.selected_ingredients:
            e.selected_ingredients.remove(seed_id)
            text = f"{e.get_seed_label(seed_id)} deselected."
        else:
            e.selected_ingredients.add(seed_id)
            label = e.get_seed_label(seed_id)
            text = f"{label} selected."
        e.clear_hover()
        e.render()
        required = set(recipe.get("ingredients", {}).keys())
        if required and required.issubset(e.selected_ingredients) and (not recipe.get("seafood") or e.selected_fish()):
            e.pointer_pressed = False
            return self.open_minigame()
        return e.response(tts=text, sfx="ingredient_select")

    def steps(self):
        e = self.engine
        recipe = e.get_recipe_config(e.selected_recipe_id)
        steps = recipe.get("gesture_steps")
        steps = steps if steps else [recipe.get("gesture", {})]
        registry = e.config.get('cooking_methods', {}).get('gestures', {})
        return [copy.deepcopy(registry[step['method']]) if 'method' in step else step for step in steps]

    def scaled_gesture(self):
        e = self.engine
        steps = self.steps()
        gesture = steps[min(e.cooking_stage_index, len(steps) - 1)]
        path = gesture.get("path", [])
        if gesture.get("kind") != "stir" or len(path) < 2:
            return gesture
        xs, ys = [p[0] for p in path], [p[1] for p in path]
        span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
        if span_x <= 0 or span_y <= 0:
            return gesture
        width, height = e.config["dotpad"]["width"], e.config["dotpad"]["height"]
        scale = min(e.stir_scale, (width - 10) / span_x, (height - 10) / span_y)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        return {**gesture, "path": [
            [round((x - cx) * scale + (width - 1) / 2),
             round((y - cy) * scale + (height - 1) / 2)] for x, y in path
        ]}

    def gesture(self):
        e = self.engine
        gesture = dict(self.scaled_gesture())
        path = [list(p) for p in gesture.get("path", [])]
        if not path: return gesture
        if not gesture.get("closed") and len(path) > 2 and math.dist(path[0], path[-1]) < 8:
            while len(path) > 2 and math.dist(path[0], path[-1]) < 8:
                path.pop()
        gesture["path"] = path
        return gesture

    def kind(self):
        return "stir" if self.gesture().get("kind") in ("stir", "grill", "fry") else "cut"

    def stage_label(self):
        return self.gesture().get("label") or ("Stir" if self.kind() == "stir" else "Chop")

    def step_text(self):
        e = self.engine
        label = self.stage_label()
        return f"Step {e.cooking_stage_index + 1}. {label}. Start at the filled square. Follow the line."

    def complete_step(self):
        e = self.engine
        e.cooking_dragging = False
        if e.defer_visual_completion("cooking", e.cooking_visible_until):
            return e.response(sfx="cooking_wait")
        if e.cooking_stage_index + 1 >= len(self.steps()):
            return self.finish_success()
        e.last_pointer = (None, None)
        e.cooking_stage_index += 1
        e.cooking_last_progress_at = None
        e.cooking_resume_marker = False
        e.cooking_progress_index = 0
        e.cooking_visible_until = {}
        e.cooking_path_samples = e.build_path_samples(self.gesture().get("path", []))
        e.clear_hover()
        e.render()
        return e.response(tts= self.step_text(), sfx="cooking_step")

    def open_minigame(self):
        e = self.engine
        recipe = e.get_recipe_config(e.selected_recipe_id)
        if not recipe:
            return e.response(tts="Choose a recipe first.", sfx="error")
        required = set(recipe.get("ingredients", {}).keys())
        if recipe.get("seafood") and not e.seafood_ready(recipe, selected=True):
            return e.response(tts="Choose one fish first.")
        if not required.issubset(e.selected_ingredients):
            return e.response(tts="Select all ingredients first.", sfx="error")
        if not self.can_craft(e.selected_recipe_id):
            return e.response(tts="Not enough ingredients.", sfx="error")
        e.last_pointer = (None, None)
        e.set_page("cooking")
        e.cooking_dragging = False
        e.cooking_progress_index = 0
        e.cooking_stage_index = 0
        e.cooking_last_progress_at = None
        e.cooking_resume_marker = False
        e.cooking_visible_until = {}
        e.cooking_path_samples = e.build_path_samples(self.gesture().get("path", []))
        e.clear_hover()
        e.render()
        return e.response(tts=f"{e.get_recipe_label(e.selected_recipe_id)}. {self.step_text()}.", sfx="cooking_start")

    def start_trace(self, x, y):
        e = self.engine
        if not e.cooking_path_samples:
            return e.response(tts="Cooking path unavailable.", sfx="error")
        recipe = e.get_recipe_config(e.selected_recipe_id)
        tolerance = float(self.gesture().get("tolerance", 4.5))
        resume_index = min(e.cooking_progress_index, len(e.cooking_path_samples) - 1)
        sx, sy = e.cooking_path_samples[resume_index]
        if math.hypot(x - sx, y - sy) > tolerance * 1.35:
            e.cooking_dragging = False
            return e.response(tts="Move to the filled square to continue.", sfx="error")
        e.cooking_dragging = True
        if e.cooking_progress_index == 0:
            e.cooking_visible_until[0] = time.monotonic() + e.disappear_delay_seconds
        e.cooking_progress_index = max(1, e.cooking_progress_index)
        e.cooking_last_progress_at = time.monotonic()
        e.cooking_resume_marker = False
        e.render()
        return e.response(sfx="tool_pickup", sound_events=[{"kind": "work_start", "sound": "cook" if self.kind() == "stir" else "cut"}])

    def advance_trace(self, x1, y1, x2, y2):
        e = self.engine
        if not e.cooking_path_samples:
            return e.response()
        recipe = e.get_recipe_config(e.selected_recipe_id)
        tolerance = float(self.gesture().get("tolerance", 4.5))
        if math.hypot(x2 - x1, y2 - y1) < 0.05:
            return e.response()
        before = e.cooking_progress_index
        advanced = False
        while e.cooking_progress_index < len(e.cooking_path_samples):
            px, py = e.cooking_path_samples[e.cooking_progress_index]
            if e.point_to_segment_distance(px, py, x1, y1, x2, y2) <= tolerance:
                e.cooking_visible_until[e.cooking_progress_index] = time.monotonic() + e.disappear_delay_seconds
                e.cooking_progress_index += 1
                advanced = True
            else:
                break
        if e.cooking_progress_index >= len(e.cooking_path_samples):
            gained = e.cooking_progress_index - before
            result = self.complete_step()
            result["sound_events"] = [{"kind": "correct", "activity": "cooking", "count": gained}]
            return result
        if advanced:
            e.cooking_last_progress_at = time.monotonic()
            e.cooking_resume_marker = False
            e.render()
            return e.response(sfx="cooking_trace", sound_events=[{"kind": "correct", "activity": "cooking", "count": e.cooking_progress_index - before}])
        return e.response()

    def fail_or_continue(self):
        e = self.engine
        total = len(e.cooking_path_samples)
        progress = e.cooking_progress_index
        percent = int(round((progress / total) * 100)) if total else 0
        e.cooking_resume_marker = progress > 0
        e.render()
        return e.response(tts=f"Progress {percent} percent.")

    def finish_success(self):
        e = self.engine
        recipe_id = e.selected_recipe_id
        recipe = e.get_recipe_config(recipe_id)
        if recipe.get("seafood"): return e.finish_seafood(recipe)
        if not recipe or not self.can_craft(recipe_id):
            self.clear()
            e.set_page("home")
            e.current_location = "home"
            e.render()
            return e.response(tts="Not enough ingredients.", sfx="error")
        for seed_id, count in recipe.get("ingredients", {}).items():
            e.add_resource("crops", -int(count), item=seed_id)
        food_count = e.loot_amount(1)
        e.resources["foods"][recipe_id] = int(e.resources["foods"].get(recipe_id, 0)) + food_count
        label = e.get_recipe_label(recipe_id)
        e.current_location = "home"
        e.set_page("home")
        self.clear()
        e.clear_hover()
        result = e.consume_time("cook")
        text = f"{label} {food_count} made." + (" Bonus." if food_count>1 else "")
        e.registry.run("activity", "cooking", label, food_count)
        if result["night"]:
            return e.night_response(text)
        e.render()
        return e.response(tts=text, sfx="cooking_success")

    def use_food(self, recipe_id):
        e = self.engine
        count = int(e.resources["foods"].get(recipe_id, 0))
        recipe = e.get_recipe_config(recipe_id)
        if count <= 0 or not recipe:
            return e.response(tts="No food available.", sfx="error")
        e.resources["foods"][recipe_id] = count - 1
        e.start_food_effect(recipe_id, recipe)
        e.clear_hover()
        e.render()
        return e.response(tts=f"{e.get_recipe_label(recipe_id)} used. {e.buff_text()}", sfx="eat_food")

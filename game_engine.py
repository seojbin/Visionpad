import math
import random
import time

from dotpad import DotPad


class GameEngine:

    def __init__(self, config):
        self.config = config
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

        self.reset()

    def reset(self):
        self.pending_visual_completion = None
        self.inventory_page = 0
        self.inventory_page_count = 1
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

        for seed_id in self.config.get("seeds", {}):
            self.resources["seeds"].setdefault(seed_id, 0)
            self.resources["crops"].setdefault(seed_id, 0)

        for recipe_id in self.config.get("recipes", {}):
            self.resources["foods"].setdefault(recipe_id, 0)

        research = self.config.get("research", {})
        expansion = research.get("field_expansion", {})
        self.research_levels = {"seed_return": 0}
        self.unlocked_plot_count = int(expansion.get("initial_plot_count", 2))

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
        self.last_pointer = (None, None)
        self.pointer_pressed = False

        time_config = self.config.get("time", {})
        self.time_total_cells = int(time_config.get("total_cells", 20))
        self.time_used_cells = 0

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
            return "로"
        code = ord(str(text)[-1])
        if 0xAC00 <= code <= 0xD7A3:
            jong = (code - 0xAC00) % 28
            return "로" if jong in (0, 8) else "으로"
        return "로"

    def get_page_name(self, page_id):
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
        # Movement never consumes time, even with an older configuration.
        if action_name == "travel":
            return 0
        defaults = {"plant": 2, "water": 2, "fertilize": 2, "harvest": 3,
                    "research": 3, "cook": 3}
        configured = self.config.get("time", {}).get("action_costs", {})
        return max(defaults.get(action_name, 0), int(configured.get(action_name, 0)))

    def get_time_cells(self):
        return max(0, min(self.time_total_cells, self.time_used_cells))

    def time_text(self):
        used = self.get_time_cells()
        remaining = max(0, self.time_total_cells - used)
        if self.day_ended:
            return "밤입니다. 침대를 눌러 잠을 자세요"
        return f"활동 {remaining}시간 남음"

    def buff_text(self):
        remaining = int(self.active_buff.get("remaining_ticks", 0))
        multiplier = float(self.active_buff.get("multiplier", 1.0))
        if remaining <= 0 or multiplier <= 1.0:
            return "버프 없음"
        percent = int(round((multiplier - 1.0) * 100))
        return f"수확 +{percent}퍼센트, {remaining}틱 남음"

    def tick_buff(self, cost):
        cost = max(0, int(cost))
        remaining = int(self.active_buff.get("remaining_ticks", 0))
        if remaining <= 0 or cost <= 0:
            return
        remaining = max(0, remaining - cost)
        self.active_buff["remaining_ticks"] = remaining
        if remaining == 0:
            self.active_buff = {
                "kind": None,
                "source": None,
                "multiplier": 1.0,
                "remaining_ticks": 0
            }

    def consume_time(self, action_name):
        cost = max(0, self.get_action_cost(action_name))
        if self.day_ended:
            return {"cost": 0, "night": True}

        self.time_used_cells = min(
            self.time_total_cells,
            self.time_used_cells + cost
        )
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

    def night_response(self, prefix=None):
        narration = "밤이 되어 집에 도착했습니다. 침대를 눌러 주무세요"
        if prefix:
            narration = f"{prefix}. {narration}"
        return self.response(tts=narration, sfx="day_end")

    def next_day(self):
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

        text = f"{self.day}일차 아침입니다"
        if matured:
            names = ", ".join(dict.fromkeys(matured))
            text += f". {names} 작물이 밤사이 다 자랐습니다"
        return self.response(tts=text, sfx="morning")

    def draw_time_bar(self):
        self.timepad.clear()
        bar = self.config.get("time", {}).get("bar", {})
        cell_width = int(bar.get("cell_width", 2))
        cell_height = int(bar.get("cell_height", 4))
        for cell_index in range(self.get_time_cells()):
            start_x = cell_index * cell_width
            for dy in range(cell_height):
                for dx in range(cell_width):
                    self.timepad.set_dot(start_x + dx, dy)

    def get_unlocked_plot_defs(self):
        return self.config.get("farm", {}).get("plots", [])[:self.unlocked_plot_count]

    def can_craft_recipe(self, recipe_id):
        recipe = self.get_recipe_config(recipe_id)
        ingredients = recipe.get("ingredients", {})
        if len(ingredients) < 2:
            return False
        for seed_id, needed in ingredients.items():
            if int(self.resources["crops"].get(seed_id, 0)) < int(needed):
                return False
        return True

    def get_food_sell_price(self, recipe_id):
        recipe = self.get_recipe_config(recipe_id)
        ingredient_total = 0
        for seed_id, count in recipe.get("ingredients", {}).items():
            crop_price = int(self.get_seed_config(seed_id).get("crop_price", 1))
            ingredient_total += crop_price * int(count)
        return max(1, int(math.ceil(ingredient_total * 1.2)))

    def get_objects(self):
        pages = {
            "home": self.get_home_objects,
            "farm": self.get_farm_objects,
            "town": self.get_town_objects,
            "minimap": self.get_minimap_objects,
            "seed_select": self.get_seed_select_objects,
            "inventory": self.get_inventory_objects,
            "research": self.get_research_objects,
            "plot_detail": self.get_plot_detail_objects,
            "water_minigame": self.get_care_minigame_objects,
            "fertilizer_minigame": self.get_care_minigame_objects,
            "harvest": self.get_harvest_objects,
            "recipe_select": self.get_recipe_select_objects,
            "ingredient_select": self.get_ingredient_select_objects,
            "cooking": self.get_cooking_objects,
            "shop_choice": self.get_shop_choice_objects,
            "shop_buy": self.get_shop_buy_objects,
            "shop_sell": self.get_shop_sell_objects
        }
        getter = pages.get(self.current_page)
        return getter() if getter else []

    def get_home_objects(self):
        objects = []
        for obj in self.config.get("home", {}).get("objects", []):
            copied = dict(obj)
            if self.day_ended and copied.get("id") != "home_bed":
                continue
            if self.day_ended and copied.get("id") == "home_bed":
                copied["tts"] = "침대입니다. 밤이 되었습니다. 선택하면 다음 날 아침으로 넘어갑니다"
            if copied.get("id") == "home_stove" and not self.day_ended:
                craftable = sum(1 for rid in self.config.get("recipes", {}) if self.can_craft_recipe(rid))
                copied["tts"] = f"주방입니다. 현재 만들 수 있는 요리는 {craftable}개입니다."
            objects.append(copied)
        return objects

    def get_farm_objects(self):
        farm = self.config.get("farm", {})
        objects = []

        for plot in self.get_unlocked_plot_defs():
            obj = dict(plot)
            obj["type"] = "plot"
            state = self.farm_plots[plot["id"]]
            seed_id = state["seed_id"]

            if seed_id is None:
                obj["tts"] = f"{plot['label']}입니다. 비어 있습니다. 선택하면 상세 밭 관리 화면으로 들어갑니다"
                obj["action"] = f"open_plot_detail:{plot['id']}"
            else:
                seed_label = self.get_seed_label(seed_id)
                needed = int(self.get_seed_config(seed_id).get("growth_days", 3))
                if state["mature"]:
                    obj["tts"] = f"{plot['label']}입니다. {seed_label}가 다 자랐습니다. 선택하면 상세 밭 관리 화면으로 들어갑니다"
                else:
                    water_text = "물을 줬습니다" if state["watered"] else "물이 부족합니다"
                    fertilizer_text = "비료를 줬습니다" if state["fertilized"] else "비료가 부족합니다"
                    obj["tts"] = (
                        f"{plot['label']}입니다. {seed_label}가 자라는 중입니다. "
                        f"성장 {state['growth']}일 중 {needed}일입니다. {water_text}. {fertilizer_text}. "
                        "선택하면 상세 밭 관리 화면으로 들어갑니다"
                    )
                obj["action"] = f"open_plot_detail:{plot['id']}"
            objects.append(obj)

        for obj in farm.get("objects", []):
            objects.append(dict(obj))
        return objects

    def get_plot_detail_objects(self):
        plot_id = self.detail_plot_id
        state = self.farm_plots.get(plot_id) if plot_id else None
        if state is None:
            return [self.back_arrow("plot_detail_back", "농장으로 돌아가기", "return_scene")]

        plot_label = self.get_plot_label(plot_id)
        seed_id = state.get("seed_id")
        if seed_id is None:
            return [
                {
                    "id": "plot_detail_empty", "type": "plot_detail_field",
                    "x": 30, "y": 17, "width": 44, "height": 18,
                    "hit_width": 48, "hit_height": 18,
                    "label": f"{plot_label} 상세",
                    "tts": f"{plot_label} 상세 관리입니다. 현재 비어 있습니다. 씨앗 심기를 선택해 작물을 심을 수 있습니다",
                    "action": ""
                },
                {
                    "id": "plot_detail_plant", "type": "care_button", "care_kind": "plant",
                    "x": 30, "y": 31, "width": 18, "height": 6,
                    "hit_width": 22, "hit_height": 10,
                    "label": "씨앗 심기",
                    "tts": "씨앗 심기입니다. 선택하면 현재 보유한 씨앗 목록을 엽니다",
                    "action": f"open_seed_select:{plot_id}"
                },
                self.back_arrow("plot_detail_back", "농장으로 돌아가기", "return_scene")
            ]

        seed_label = self.get_seed_label(seed_id)
        needed = int(self.get_seed_config(seed_id).get("growth_days", 3))
        water_text = "물이 충분합니다" if state["watered"] else "물이 부족합니다"
        if state["fertilized"]:
            fertilizer_text = "비료가 적용되어 있습니다"
        elif int(self.resources.get("fertilizer", 0)) <= 0:
            fertilizer_text = "비료가 부족합니다. 보유한 비료가 없습니다"
        else:
            fertilizer_text = f"비료가 부족합니다. 비료는 {self.resources.get('fertilizer', 0)}개 보유 중입니다"

        field_tts = (
            f"{plot_label} 상세 관리입니다. {seed_label}입니다. "
            f"성장 {state['growth']}일 중 {needed}일입니다. {water_text}. {fertilizer_text}"
        )
        if state["mature"]:
            field_tts = f"{plot_label} 상세 관리입니다. {seed_label}가 다 자랐습니다. 수확할 수 있습니다"

        objects = [{
            "id": "plot_detail_field", "type": "plot_detail_field",
            "x": 30, "y": 17, "width": 44, "height": 18,
            "hit_width": 48, "hit_height": 18,
            "label": f"{plot_label} 상세", "tts": field_tts, "action": ""
        }, {
            "id": "plot_detail_growth_gauge", "type": "growth_gauge",
            "x": 30, "y": 4, "width": 42, "height": 5,
            "hit_width": 44, "hit_height": 6,
            "label": "성장 게이지",
            "tts": f"성장 게이지입니다. {seed_label}는 {needed}일 중 {needed if state['mature'] else state['growth']}일 성장했습니다",
            "action": ""
        }]

        if state["mature"]:
            objects.append({
                "id": "plot_detail_harvest", "type": "care_button", "care_kind": "harvest",
                "x": 30, "y": 31, "width": 18, "height": 6,
                "hit_width": 22, "hit_height": 10,
                "label": "수확",
                "tts": f"수확입니다. {seed_label}가 다 자랐습니다.",
                "action": f"start_harvest:{plot_id}"
            })
        else:
            water_action = "" if state["watered"] else f"start_care:water:{plot_id}"
            water_tts = (
                "물 주기입니다. 오늘 이미 물을 줬습니다"
                if state["watered"]
                else "물 주기입니다."
            )
            objects.append({
                "id": "plot_detail_water", "type": "care_button", "care_kind": "water",
                "x": 23, "y": 31, "width": 18, "height": 6,
                "hit_width": 21, "hit_height": 10,
                "label": "물 주기", "tts": water_tts, "action": water_action
            })

            fertilizer_count = int(self.resources.get("fertilizer", 0))
            fertilizer_action = ""
            if not state["fertilized"] and fertilizer_count > 0:
                fertilizer_action = f"start_care:fertilizer:{plot_id}"
            if state["fertilized"]:
                fertilizer_tts = "비료 주기입니다. 오늘 이미 비료를 줬습니다"
            elif fertilizer_count <= 0:
                fertilizer_tts = "비료 주기입니다. 보유한 비료가 없습니다. 마을 상점에서 구매할 수 있습니다"
            else:
                fertilizer_tts = f"비료 주기입니다. 비료 {fertilizer_count}개를 보유 중입니다."
            objects.append({
                "id": "plot_detail_fertilizer", "type": "care_button", "care_kind": "fertilizer",
                "x": 46, "y": 31, "width": 18, "height": 6,
                "hit_width": 21, "hit_height": 10,
                "label": "비료 주기", "tts": fertilizer_tts, "action": fertilizer_action
            })

        objects.append(self.back_arrow("plot_detail_back", "농장으로 돌아가기", "return_scene"))
        return objects

    def get_care_minigame_objects(self):
        plot_id = self.detail_plot_id
        state = self.farm_plots.get(plot_id) if plot_id else None
        if state is None or state.get("seed_id") is None:
            return []
        seed_label = self.get_seed_label(state["seed_id"])
        mode_label = "물" if self.care_mode == "water" else "비료"
        field = self.config.get("care_minigame", {}).get("field", {})
        objects = [{
            "id": "care_field", "type": "care_field",
            "x": int(field.get("x", 30)), "y": int(field.get("y", 20)),
            "width": int(field.get("width", 46)), "height": int(field.get("height", 30)),
            "hit_width": int(field.get("width", 46)), "hit_height": int(field.get("height", 30)),
            "label": f"{mode_label} 주기 밭",
            "tts": f"확대된 {seed_label} 밭입니다. 손가락을 누른 채 지점들을 지나가며 {mode_label}을 고르게 뿌리세요",
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
                "label": f"{mode_label}을 뿌릴 위치",
                "tts": f"{mode_label}을 뿌릴 위치입니다. 누른 채 지나가세요",
                "action": ""
            })
        return objects

    def get_town_objects(self):
        return [dict(obj) for obj in self.config.get("town", {}).get("objects", [])]

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
            yield_count = int(seed_config.get("yield", 1))
            growth_days = int(seed_config.get("growth_days", 3))
            chance = self.get_effective_seed_return_chance(seed_id)
            objects.append({
                "id": f"seed_{seed_id}", "type": "seed", "seed_id": seed_id,
                "x": x, "y": y, "width": 12, "height": 10,
                "hit_width": 15, "hit_height": 13,
                "label": f"{seed_config.get('label', seed_id)} 씨앗",
                "tts": f"{seed_config.get('label', seed_id)} 씨앗 {count}개. 성장 {growth_days}일, 수확 {yield_count}개, 씨앗 회수 {int(round(chance * 100))}퍼센트",
                "action": f"plant:{self.seed_select_plot_id}:{seed_id}"
            })

        objects.append(self.back_arrow("seed_back", "농장으로 돌아가기", "return_scene"))
        return objects

    def get_inventory_objects(self):
        entries = [
            {"id": "coin", "label": "골드", "count": int(self.resources.get("coin", 0)), "kind": "coin", "action": ""},
            {"id": "fertilizer", "label": "비료", "count": int(self.resources.get("fertilizer", 0)), "kind": "fertilizer", "action": ""},
            {"id": "wood", "label": "나무", "count": int(self.resources.get("wood", 0)), "kind": "material", "action": ""},
            {"id": "stone", "label": "돌", "count": int(self.resources.get("stone", 0)), "kind": "material", "action": ""}
        ]
        for seed_id, seed_config in self.config.get("seeds", {}).items():
            entries.append({"id": f"seed_{seed_id}", "label": f"{seed_config.get('label', seed_id)} 씨앗", "count": int(self.resources["seeds"].get(seed_id, 0)), "kind": "seed", "seed_id": seed_id, "action": ""})
        for seed_id, seed_config in self.config.get("seeds", {}).items():
            entries.append({"id": f"crop_{seed_id}", "label": f"{seed_config.get('label', seed_id)} 작물", "count": int(self.resources["crops"].get(seed_id, 0)), "kind": "crop", "seed_id": seed_id, "action": ""})
        for recipe_id, recipe in self.config.get("recipes", {}).items():
            count = int(self.resources["foods"].get(recipe_id, 0))
            if count <= 0 and self.inventory_hide_zero_items:
                continue
            ticks = int(recipe.get("buff_ticks", 0))
            multiplier = float(recipe.get("harvest_multiplier", 1.0))
            percent = int(round((multiplier - 1.0) * 100))
            entries.append({
                "id": f"food_{recipe_id}", "label": recipe.get("label", recipe_id),
                "count": count, "kind": "food", "action": f"use_food:{recipe_id}",
                "extra_tts": f"사용하면 {ticks}시간 동안 수확량이 {percent}퍼센트 증가합니다"
            })

        if self.inventory_hide_zero_items:
            entries = [entry for entry in entries if entry["count"] > 0]
        page_size = self.inventory_items_per_page
        self.inventory_page_count = max(1, math.ceil(len(entries) / page_size))
        self.inventory_page = min(self.inventory_page, self.inventory_page_count - 1)
        entries = entries[self.inventory_page * page_size:(self.inventory_page + 1) * page_size]
        positions = [
            (9, 5), (23, 5), (37, 5), (51, 5),
            (9, 15), (23, 15), (37, 15), (51, 15),
            (9, 25), (23, 25), (37, 25), (51, 25)
        ]
        objects = []
        for index, entry in enumerate(entries[:len(positions)]):
            x, y = positions[index]
            extra = entry.get("extra_tts", "")
            tts = f"{entry['label']} {entry['count']}개입니다"
            if extra:
                tts += f". {extra}"
            objects.append({
                "id": f"inventory_{entry['id']}", "type": "resource",
                "resource_kind": entry["kind"], "seed_id": entry.get("seed_id"), "x": x, "y": y,
                "width": 10, "height": 6, "hit_width": 13, "hit_height": 9,
                "label": entry["label"], "tts": tts, "action": entry.get("action", "")
            })
        for delta, x, label, direction in [(-1, 9, "이전 페이지입니다", "left"), (1, 51, "다음 페이지입니다", "right")]:
            if 0 <= self.inventory_page + delta < self.inventory_page_count:
                objects.append({"id": f"inventory_page_{direction}", "type": "arrow",
                                "x": x, "y": 35, "direction": direction, "size": 2,
                                "hit_width": 11, "hit_height": 7,
                                "label": label, "tts": label,
                                "action": f"inventory_page:{delta}"})
        return objects

    def get_minimap_objects(self):
        minimap = self.config.get("minimap", {})
        objects = []
        locations = minimap.get("locations", [])
        current_node = next((loc for loc in locations if loc.get("location") == self.current_location), None)

        for route in minimap.get("routes", []):
            obj = dict(route)
            obj["type"] = "route"
            obj.setdefault("tts", f"{obj.get('label', '길')}입니다")
            objects.append(obj)

        for location in locations:
            obj = dict(location)
            obj["type"] = "node"
            location_id = obj["location"]
            if location_id == self.current_location:
                obj["current"] = True
                obj["tts"] = f"{obj['label']}입니다. 현재 위치입니다"
            else:
                obj["current"] = False
                direction = self.get_relative_direction(current_node, obj)
                obj["tts"] = f"{obj['label']}입니다. 현재 위치에서 {direction}에 있습니다" if direction else f"{obj['label']}입니다"
            obj["action"] = f"travel:{location_id}"
            objects.append(obj)
        return objects

    def get_research_objects(self):
        objects = []
        coin = int(self.resources.get("coin", 0))
        seed_cfg = self.config.get("research", {}).get("seed_return", {})
        level = int(self.research_levels.get("seed_return", 0))
        max_level = int(seed_cfg.get("max_level", 3))
        costs = list(seed_cfg.get("costs", []))

        if level >= max_level:
            seed_tts = f"씨앗 회수 연구입니다. 현재 {level}단계로 최대 단계입니다"
            seed_action = ""
        else:
            cost = int(costs[level]) if level < len(costs) else 999999
            bonus = float(seed_cfg.get("bonus_per_level", 0.1))
            seed_tts = f"씨앗 회수 {level}단계. {cost}골드로 +{int(round(bonus * 100))}퍼센트. 보유 {coin}골드"
            seed_action = "research:seed_return"

        objects.append({
            "id": "research_seed_return", "type": "research", "research_kind": "seed_return",
            "x": 19, "y": 18, "width": 18, "height": 12, "hit_width": 20, "hit_height": 14,
            "label": "씨앗 회수 연구", "tts": seed_tts, "action": seed_action
        })

        expand_cfg = self.config.get("research", {}).get("field_expansion", {})
        all_plots = self.config.get("farm", {}).get("plots", [])
        costs = list(expand_cfg.get("costs", []))
        initial = int(expand_cfg.get("initial_plot_count", 2))
        expansion_index = max(0, self.unlocked_plot_count - initial)
        if self.unlocked_plot_count >= len(all_plots):
            expand_tts = f"밭 확장 연구입니다. 현재 밭 {self.unlocked_plot_count}개를 사용하며 최대 확장 상태입니다"
            expand_action = ""
        else:
            cost = int(costs[expansion_index]) if expansion_index < len(costs) else 999999
            expand_tts = f"밭 {self.unlocked_plot_count}개. {cost}골드로 1개 확장. 보유 {coin}골드"
            expand_action = "research:field_expand"

        objects.append({
            "id": "research_field_expand", "type": "research", "research_kind": "field_expand",
            "x": 41, "y": 18, "width": 18, "height": 12, "hit_width": 20, "hit_height": 14,
            "label": "밭 확장 연구", "tts": expand_tts, "action": expand_action
        })
        objects.append(self.back_arrow("research_back", "집으로 돌아가기", "return_scene"))
        return objects

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
            "label": "확대된 밭",
            "tts": f"확대된 {seed_label} 밭입니다. 손가락을 누른 채 작물들을 채집하세요",
            "action": ""
        }]
        for target in self.harvest_targets:
            if target["id"] in self.harvest_collected_ids:
                continue
            objects.append({
                "id": target["id"], "type": "harvest_crop", "x": target["x"], "y": target["y"],
                "width": 5, "height": 5, "hit_width": 7, "hit_height": 7,
                "label": f"수확할 {seed_label}", "tts": f"수확할 {seed_label}입니다. 누른 채 지나가면 채집", "action": ""
            })
        return objects

    def get_recipe_select_objects(self):
        craftable = [(rid, cfg) for rid, cfg in self.config.get("recipes", {}).items() if self.can_craft_recipe(rid)]
        positions = [(15, 17), (30, 17), (45, 17), (22, 29), (38, 29)]
        objects = []
        for index, (recipe_id, recipe) in enumerate(craftable[:len(positions)]):
            x, y = positions[index]
            ingredient_text = self.recipe_ingredient_text(recipe_id)
            ticks = int(recipe.get("buff_ticks", 0))
            objects.append({
                "id": f"recipe_{recipe_id}", "type": "recipe", "recipe_id": recipe_id,
                "x": x, "y": y, "width": 12, "height": 9, "hit_width": 14, "hit_height": 11,
                "label": recipe.get("label", recipe_id),
                "tts": f"{recipe.get('label', recipe_id)}. {ingredient_text}. 수확 +{int(round((float(recipe.get('harvest_multiplier', 1.0)) - 1) * 100))}퍼센트, {ticks}시간",
                "action": f"select_recipe:{recipe_id}"
            })
        objects.append(self.back_arrow("recipe_back", "집으로 돌아가기", "return_scene"))
        return objects

    def get_ingredient_select_objects(self):
        recipe = self.get_recipe_config(self.selected_recipe_id)
        if not recipe:
            return [self.back_arrow("ingredient_back", "주방으로 돌아가기", "open_recipes")]
        positions = [(15, 17), (30, 17), (45, 17)]
        objects = []
        for index, (seed_id, needed) in enumerate(recipe.get("ingredients", {}).items()):
            if index >= len(positions):
                break
            x, y = positions[index]
            selected = seed_id in self.selected_ingredients
            count = int(self.resources["crops"].get(seed_id, 0))
            label = self.get_seed_label(seed_id)
            status = "선택했습니다" if selected else "아직 선택하지 않았습니다"
            objects.append({
                "id": f"ingredient_{seed_id}", "type": "ingredient", "ingredient_id": seed_id,
                "selected": selected, "x": x, "y": y, "width": 12, "height": 9,
                "hit_width": 14, "hit_height": 11, "label": f"{label} 재료",
                "tts": f"{label} 재료입니다. {needed}개 필요, {count}개 보유 중. {status}",
                "action": f"toggle_ingredient:{seed_id}"
            })

        required = set(recipe.get("ingredients", {}).keys())
        ready = required and required.issubset(self.selected_ingredients)
        objects.append({
            "id": "ingredient_start", "type": "cooking_start", "x": 30, "y": 31,
            "width": 18, "height": 6, "hit_width": 20, "hit_height": 9,
            "label": "조리 시작",
            "tts": "조리 시작입니다." if ready else "조리 시작입니다. 필요한 재료를 모두 먼저 선택하세요",
            "action": "start_cooking" if ready else ""
        })
        objects.append(self.back_arrow("ingredient_back", "레시피로 돌아가기", "open_recipes"))
        return objects

    def get_cooking_objects(self):
        return []

    def get_shop_choice_objects(self):
        return [
            {
                "id": "shop_sell_choice", "type": "shop_choice", "choice": "sell",
                "x": 15, "y": 20, "width": 28, "height": 34, "hit_width": 30, "hit_height": 38,
                "label": "판매", "tts": "판매입니다. 왼쪽 영역을 선택하면 보유한 작물과 요리를 팝니다", "action": "shop_mode:sell"
            },
            {
                "id": "shop_buy_choice", "type": "shop_choice", "choice": "buy",
                "x": 45, "y": 20, "width": 28, "height": 34, "hit_width": 30, "hit_height": 38,
                "label": "구매", "tts": "구매입니다. 오른쪽 영역을 선택하면 씨앗과 비료를 삽니다", "action": "shop_mode:buy"
            }
        ]

    def get_shop_buy_objects(self):
        objects = []
        positions = [(9, 16), (23, 16), (37, 16), (51, 16)]
        index = 0
        for seed_id, seed in self.config.get("seeds", {}).items():
            if index >= len(positions):
                break
            x, y = positions[index]
            price = int(seed.get("seed_price", max(1, round(int(seed.get("crop_price", 1)) * 0.8))))
            count = int(self.resources["seeds"].get(seed_id, 0))
            objects.append({
                "id": f"shop_buy_seed_{seed_id}", "type": "shop_item", "shop_kind": "seed", "item_id": seed_id,
                "x": x, "y": y, "width": 10, "height": 8, "hit_width": 13, "hit_height": 11,
                "label": f"{self.get_seed_label(seed_id)} 씨앗",
                "tts": f"{self.get_seed_label(seed_id)} 씨앗, {price}골드. 보유 {count}개",
                "action": f"buy:seed:{seed_id}"
            })
            index += 1

        x, y = positions[min(index, len(positions) - 1)]
        fertilizer_price = int(self.config.get("fertilizer", {}).get("shop_price", 12))
        objects.append({
            "id": "shop_buy_fertilizer", "type": "shop_item", "shop_kind": "fertilizer", "item_id": "fertilizer",
            "x": x, "y": y, "width": 10, "height": 8, "hit_width": 13, "hit_height": 11,
            "label": "비료", "tts": f"비료, {fertilizer_price}골드. 보유 {self.resources.get('fertilizer', 0)}개",
            "action": "buy:fertilizer:fertilizer"
        })
        objects.append(self.back_arrow("shop_buy_back", "마을로 돌아가기", "return_scene"))
        return objects

    def get_shop_sell_objects(self):
        sellables = []
        for seed_id, seed in self.config.get("seeds", {}).items():
            count = int(self.resources["crops"].get(seed_id, 0))
            if count > 0:
                sellables.append(("crop", seed_id, f"{self.get_seed_label(seed_id)} 작물", count, int(seed.get("crop_price", 1))))
        for recipe_id, recipe in self.config.get("recipes", {}).items():
            count = int(self.resources["foods"].get(recipe_id, 0))
            if count > 0:
                sellables.append(("food", recipe_id, recipe.get("label", recipe_id), count, self.get_food_sell_price(recipe_id)))

        positions = [(9, 12), (23, 12), (37, 12), (51, 12), (9, 25), (23, 25), (37, 25), (51, 25)]
        objects = []
        for index, (kind, item_id, label, count, price) in enumerate(sellables[:len(positions)]):
            x, y = positions[index]
            objects.append({
                "id": f"shop_sell_{kind}_{item_id}", "type": "shop_item", "shop_kind": kind, "item_id": item_id,
                "x": x, "y": y, "width": 10, "height": 8, "hit_width": 13, "hit_height": 11,
                "label": label, "tts": f"{label}, 보유 {count}개. 판매 {price}골드",
                "action": f"sell:{kind}:{item_id}"
            })
        if not sellables:
            objects.append({
                "id": "shop_nothing_to_sell", "type": "box", "x": 30, "y": 18,
                "width": 22, "height": 10, "hit_width": 24, "hit_height": 12,
                "label": "판매할 물건 없음", "tts": "현재 판매할 수 있는 작물이나 요리가 없습니다", "action": ""
            })
        objects.append(self.back_arrow("shop_sell_back", "마을로 돌아가기", "return_scene"))
        return objects

    def back_arrow(self, object_id, label, action):
        return {
            "id": object_id, "type": "arrow", "x": 6, "y": 35,
            "direction": "left", "size": 2, "hit_width": 11, "hit_height": 9,
            "label": label, "tts": f"{label}입니다", "action": action
        }

    def recipe_ingredient_text(self, recipe_id):
        recipe = self.get_recipe_config(recipe_id)
        parts = []
        for seed_id, count in recipe.get("ingredients", {}).items():
            parts.append(f"{self.get_seed_label(seed_id)} {count}개")
        return ", ".join(parts)

    def get_relative_direction(self, origin, target):
        if origin is None:
            return ""
        dx = float(target["x"]) - float(origin["x"])
        dy = float(target["y"]) - float(origin["y"])
        if abs(dx) > 4 and abs(dy) > 4:
            horizontal = "오른쪽" if dx > 0 else "왼쪽"
            vertical = "아래쪽" if dy > 0 else "위쪽"
            return f"{horizontal} {vertical}"
        if abs(dx) >= abs(dy):
            return "오른쪽" if dx > 0 else "왼쪽" if dx < 0 else ""
        return "아래쪽" if dy > 0 else "위쪽" if dy < 0 else ""

    def render(self):
        self.dotpad.clear()
        for obj in self.get_objects():
            obj_type = obj.get("type")
            if obj_type == "arrow":
                self.dotpad.draw_arrow(obj["x"], obj["y"], obj["direction"], obj.get("size", 2))
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
            elif obj_type == "node":
                self.draw_node(obj)
            elif obj_type == "route":
                self.dotpad.draw_line(obj["x1"], obj["y1"], obj["x2"], obj["y2"])
            elif obj_type == "watering_can":
                self.draw_watering_can(obj)
            elif obj_type == "fertilizer":
                self.draw_fertilizer(obj)
            elif obj_type == "seed":
                self.draw_seed(obj)
            elif obj_type == "resource":
                self.draw_resource(obj)
            elif obj_type == "research":
                self.draw_research(obj)
            elif obj_type == "plot_detail_field":
                self.draw_plot_detail_field(obj)
            elif obj_type == "growth_gauge":
                self.draw_plot_detail_gauge()
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

        if self.current_page == "cooking":
            self.draw_cooking_path()
        self.draw_time_bar()

    def draw_bed(self, obj):
        width, height = obj.get("width", 10), obj.get("height", 6)
        self.dotpad.draw_box(obj["x"], obj["y"], width, height)
        x1 = int(obj["x"] - width // 2)
        y1 = int(obj["y"] - height // 2)
        self.dotpad.draw_line(x1 + 2, y1, x1 + 2, y1 + height)

    def draw_chest(self, obj):
        self.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 8), obj.get("height", 6))
        self.dotpad.set_dot(obj["x"], obj["y"])
        self.dotpad.draw_line(obj["x"] - 3, obj["y"], obj["x"] + 3, obj["y"])

    def draw_stove(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 10), obj.get("height", 7))
        for dx, dy in [(-2, -1), (2, -1), (-2, 2), (2, 2)]:
            self.dotpad.set_dot(x + dx, y + dy)
            self.dotpad.set_dot(x + dx + 1, y + dy)

    def draw_plot(self, obj):
        self.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 10), obj.get("height", 8))
        state = self.farm_plots.get(obj["id"], self.new_plot_state())
        if state["seed_id"] is None:
            return
        if state["mature"]:
            for dx, dy in [(0, -2), (0, -1), (0, 0), (-1, 0), (1, 0), (-2, -1), (2, -1)]:
                self.dotpad.set_dot(obj["x"] + dx, obj["y"] + dy)
        else:
            self.dotpad.set_dot(obj["x"], obj["y"])
            if state["growth"] >= 1:
                self.dotpad.set_dot(obj["x"], obj["y"] - 1)
            if state["growth"] >= 2:
                self.dotpad.set_dot(obj["x"] - 1, obj["y"])
                self.dotpad.set_dot(obj["x"] + 1, obj["y"])
            if state["fertilized"]:
                self.dotpad.set_dot(obj["x"] - 2, obj["y"] + 2)
        self.draw_plot_progress(obj, state)

    def draw_plot_progress(self, obj, state):
        if state["seed_id"] is None:
            return
        needed = max(1, int(self.get_seed_config(state["seed_id"]).get("growth_days", 3)))
        growth = needed if state["mature"] else int(state["growth"])
        bar_width = 10
        y = int(obj["y"] + obj.get("height", 8) / 2 + 2)
        x1 = int(obj["x"] - bar_width / 2)
        x2 = x1 + bar_width
        self.dotpad.draw_line(x1, y - 1, x2, y - 1)
        self.dotpad.set_dot(x1, y)
        self.dotpad.set_dot(x2, y)
        fill_width = int(round((bar_width - 1) * growth / needed))
        for x in range(x1 + 1, min(x2, x1 + 1 + fill_width)):
            self.dotpad.set_dot(x, y)

    def draw_watering_can(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, 6, 5)
        self.dotpad.draw_line(x + 3, y - 1, x + 7, y - 3)
        self.dotpad.draw_line(x + 7, y - 3, x + 8, y - 2)
        self.dotpad.draw_line(x - 3, y - 1, x - 5, y - 1)

    def draw_fertilizer(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, 6, 7)
        self.dotpad.draw_line(x - 2, y - 1, x + 2, y - 1)
        self.dotpad.set_dot(x, y + 1)
        self.dotpad.set_dot(x - 1, y + 2)
        self.dotpad.set_dot(x + 1, y + 2)

    def draw_seed(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 12), obj.get("height", 10))
        self.draw_crop_symbol(x, y, obj.get("seed_id"))

    def draw_crop_symbol(self, x, y, seed_id):
        # Distinct compact silhouettes: round fruit, tapered root, paired tubers.
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
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 10), obj.get("height", 7))
        kind = obj.get("resource_kind")
        if kind in ("seed", "crop"):
            self.draw_crop_symbol(x, y, obj.get("seed_id"))
        elif kind == "coin":
            self.dotpad.draw_box(x, y, 4, 4)
        elif kind == "food":
            self.dotpad.draw_line(x - 2, y, x + 2, y)
            self.dotpad.draw_line(x, y - 2, x, y + 2)
            self.dotpad.set_dot(x - 2, y - 2)
            self.dotpad.set_dot(x + 2, y - 2)
        else:
            self.dotpad.set_dot(x, y)
            self.dotpad.set_dot(x - 1, y)
            self.dotpad.set_dot(x + 1, y)

    def draw_node(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, 7, 7)
        if obj.get("current", False):
            self.dotpad.set_dot(x - 4, y)
            self.dotpad.set_dot(x + 4, y)
            self.dotpad.set_dot(x, y - 4)
            self.dotpad.set_dot(x, y + 4)

    def draw_research(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 18), obj.get("height", 12))
        if obj.get("research_kind") == "seed_return":
            self.dotpad.draw_line(x - 3, y, x + 3, y)
            self.dotpad.draw_line(x, y - 3, x, y + 3)
        else:
            self.dotpad.draw_box(x, y, 6, 6)
            self.dotpad.set_dot(x - 4, y)
            self.dotpad.set_dot(x + 4, y)

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

    def draw_plot_detail_gauge(self):
        plot_id = self.detail_plot_id
        state = self.farm_plots.get(plot_id) if plot_id else None
        if not state or state.get("seed_id") is None:
            return
        needed = max(1, int(self.get_seed_config(state["seed_id"]).get("growth_days", 3)))
        growth = needed if state.get("mature") else min(needed, int(state.get("growth", 0)))
        x1, x2 = 9, 50
        y1, y2 = 2, 6
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
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 18), obj.get("height", 7))
        kind = obj.get("care_kind")
        if kind == "water":
            self.dotpad.set_dot(x, y - 2)
            self.dotpad.set_dot(x - 1, y - 1)
            self.dotpad.set_dot(x + 1, y - 1)
            self.dotpad.draw_line(x - 1, y, x + 1, y)
        elif kind == "fertilizer":
            self.dotpad.draw_box(x, y, 5, 4)
            self.dotpad.set_dot(x - 1, y + 1)
            self.dotpad.set_dot(x + 1, y + 1)
        elif kind == "harvest":
            self.draw_harvest_crop({"x": x, "y": y})
        elif kind == "plant":
            self.dotpad.set_dot(x, y)
            self.dotpad.set_dot(x - 1, y + 1)
            self.dotpad.set_dot(x + 1, y + 1)
            self.dotpad.set_dot(x, y - 1)

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
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 12), obj.get("height", 9))
        self.dotpad.draw_line(x - 3, y + 1, x + 3, y + 1)
        self.dotpad.set_dot(x - 2, y - 2)
        self.dotpad.set_dot(x + 2, y - 2)

    def draw_ingredient(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 12), obj.get("height", 9))
        self.dotpad.set_dot(x, y)
        if obj.get("selected"):
            self.dotpad.draw_line(x - 3, y + 2, x - 1, y + 4)
            self.dotpad.draw_line(x - 1, y + 4, x + 4, y - 3)

    def draw_cooking_start(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 18), obj.get("height", 7))
        self.dotpad.draw_line(x - 3, y, x + 3, y)
        self.dotpad.draw_line(x, y - 2, x, y + 2)

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
        # Browser polling keeps physical output current even without movement.
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
        # Progress is the index of the next checkpoint to visit.
        # Render only unvisited samples; scoring still uses the full path.
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
            self.dotpad.draw_box(round(sx), round(sy), 4, 4)
        ex, ey = map(round, samples[-1])
        self.dotpad.set_dot(ex, ey)
        self.dotpad.set_dot(ex - 1, ey)
        self.dotpad.set_dot(ex + 1, ey)
        self.dotpad.set_dot(ex, ey - 1)
        self.dotpad.set_dot(ex, ey + 1)
        resume = self.cooking_resume_point()
        if resume is not None:
            self.dotpad.draw_box(round(resume[0]), round(resume[1]), 4, 4)

    def draw_shop_npc(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 16), obj.get("height", 12))
        self.dotpad.draw_box(x, y - 1, 6, 6)
        self.dotpad.draw_line(x - 5, y + 4, x + 5, y + 4)

    def draw_shop_choice(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 28), obj.get("height", 34))
        if obj.get("choice") == "sell":
            self.dotpad.draw_arrow(x, y, "left", 3)
        else:
            self.dotpad.draw_arrow(x, y, "right", 3)

    def draw_shop_item(self, obj):
        x, y = int(obj["x"]), int(obj["y"])
        self.dotpad.draw_box(x, y, obj.get("width", 11), obj.get("height", 9))
        kind = obj.get("shop_kind")
        if kind in ("seed", "crop"):
            self.draw_crop_symbol(x, y, obj.get("item_id"))
        elif kind == "fertilizer":
            self.dotpad.draw_line(x - 2, y, x + 2, y)
            self.dotpad.draw_line(x, y - 2, x, y + 2)
        else:
            self.dotpad.draw_line(x - 2, y + 1, x + 2, y + 1)
            self.dotpad.set_dot(x - 2, y)
            self.dotpad.set_dot(x + 2, y)

    def point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        nx, ny = x1 + t * dx, y1 + t * dy
        return ((px - nx) ** 2 + (py - ny) ** 2) ** 0.5

    def object_contains(self, obj, x, y):
        if obj.get("type") == "route":
            distance = self.point_to_segment_distance(x, y, obj["x1"], obj["y1"], obj["x2"], obj["y2"])
            return distance <= float(obj.get("hit_radius", 3.0))
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
        for plot in self.get_unlocked_plot_defs():
            obj = dict(plot)
            obj["type"] = "plot"
            if self.object_contains(obj, x, y):
                return obj
        return None

    def get_object_tts(self, obj):
        kind, label = obj.get("type"), obj.get("label", "")
        if kind == "plot":
            return self.plot_status_text(obj["id"])
        if kind == "plot_detail_field":
            return self.plot_status_text(self.detail_plot_id)
        if kind == "arrow":
            return label
        if kind == "bed":
            return "침대. 선택하면 다음 날"
        if kind == "chest":
            return "연구. 씨앗 회수와 밭 확장"
        if kind == "stove":
            count = sum(self.can_craft_recipe(r) for r in self.config.get("recipes", {}))
            return f"주방. 만들 수 있는 요리 {count}개"
        if kind == "shop_npc":
            return "상점. 작물 판매, 씨앗과 비료 구매"
        if kind == "care_button":
            mode = obj.get("care_kind")
            state = self.farm_plots.get(self.detail_plot_id, {})
            if mode == "water":
                return "물 주기 완료" if state.get("watered") else f"물 주기. 드래그로 뿌리기."
            if mode == "fertilizer":
                count = self.resources.get("fertilizer", 0)
                if state.get("fertilized"):
                    return "비료 주기 완료"
                return f"비료 {count}개. 물을 준 뒤 사용. 수확까지 {self.config.get('fertilizer', {}).get('growth_day_bonus', 1)}일 즉시 단축." if count else "비료 없음. 상점에서 구매"
            return label
        return obj.get("tts") or label

    def get_hover_sfx(self, obj):
        if obj.get("hover_sfx"):
            return obj["hover_sfx"]
        mapping = {
            "bed": "hover_bed", "chest": "hover_chest", "stove": "hover_stove",
            "plot": "hover_plot", "node": "hover_node", "route": "hover_route",
            "watering_can": "hover_water_tool", "fertilizer": "hover_fertilizer",
            "seed": "hover_seed", "resource": "hover_resource", "research": "hover_research",
            "harvest_crop": "hover_harvest_crop", "harvest_field": "hover_plot", "arrow": "hover_navigation",
            "recipe": "hover_recipe", "ingredient": "hover_ingredient", "cooking_start": "hover_cooking",
            "shop_npc": "hover_shop", "shop_choice": "hover_shop", "shop_item": "hover_shop_item",
            "plot_detail_field": "hover_plot", "growth_gauge": "hover_plot", "care_button": "hover_tool", "care_field": "hover_plot",
            "care_target": "hover_tool"
        }
        return mapping.get(obj.get("type"), "hover_object")

    def pointer_move(self, x, y):
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()
        if self.current_page == "cooking":
            return self.response()
        obj = self.find_object(x, y)
        if obj is None:
            self.clear_hover()
            return self.response()
        object_id = obj["id"]
        if object_id != self.hover_object_id:
            self.hover_object_id = object_id
            return self.response(tts=self.get_object_tts(obj), sfx=self.get_hover_sfx(obj))
        return self.response()

    def pointer_down(self, x, y):
        if self.pending_visual_completion:
            return self.response()
        self.pointer_pressed = True
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()

        if self.current_page in ("water_minigame", "fertilizer_minigame"):
            self.care_dragging = True
            before = len(self.care_collected_ids)
            collected = self.collect_care_point(x, y)
            if collected:
                self.render()
                return self.response(sfx="care_spray", sound_events=[{"kind": "correct", "count": len(self.care_collected_ids) - before}])
            mode_label = "물을" if self.care_mode == "water" else "비료를"
            return self.response(tts=f"{mode_label} 뿌리기 시작. 누른 채 지점들을 지나가세요", sfx="tool_pickup")

        if self.current_page == "harvest":
            self.harvest_dragging = True
            before = len(self.harvest_collected_ids)
            collected = self.collect_harvest_point(x, y)
            if collected:
                self.render()
                return self.response(sfx="harvest_collect", sound_events=[{"kind": "correct", "count": len(self.harvest_collected_ids) - before}])
            return self.response(tts="수확을 시작. 누른 채 작물들을 지나가세요", sfx="tool_pickup")

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
                return self.response(tts="물뿌리개를 잡았습니다. 누른 채 물을 줄 밭까지 드래그", sfx="tool_pickup")
            if self.drag_tool == "fertilizer":
                count = int(self.resources.get("fertilizer", 0))
                if count <= 0:
                    self.drag_tool = None
                    return self.response(tts="보유한 비료가 없습니다", sfx="error")
                return self.response(tts=f"비료를 잡았습니다. {count}개 보유 중. 누른 채 비료를 줄 밭까지 드래그", sfx="tool_pickup")

        return self.perform_action(action, obj)

    def pointer_drag(self, x, y):
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
        if self.day_ended and action != "rest":
            return self.night_only_response()
        if action.startswith("inventory_page:"):
            if self.current_page != "inventory":
                return self.response()
            delta = int(action.split(":", 1)[1])
            self.get_inventory_objects()
            self.inventory_page = max(0, min(self.inventory_page + delta, self.inventory_page_count - 1))
            self.clear_hover()
            self.render()
            return self.response(tts="다음 페이지입니다" if delta > 0 else "이전 페이지입니다", sfx="open_page")
        if action.startswith("travel:"):
            return self.travel_to(action.split(":", 1)[1])
        if action == "return_scene":
            return self.return_to_scene()
        if action == "open_research":
            return self.open_research()
        if action == "open_recipes":
            return self.open_recipes()
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
        if action.startswith("research:"):
            return self.buy_research(action.split(":", 1)[1])
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
        return self.response(tts="밤입니다. 침대를 눌러 잠을 자세요", sfx="error")

    def travel_to(self, location):
        if self.day_ended:
            return self.night_only_response()
        if location not in ("home", "farm", "town"):
            return self.response(tts="아직 이동할 수 없는 장소입니다")
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
        particle = self.ro_particle(name)
        return self.response(tts=f"{name}", sfx="travel")

    def open_minimap(self):
        if self.day_ended:
            return self.night_only_response()
        self.current_page = "minimap"
        self.seed_select_plot_id = None
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.clear_hover()
        self.render()
        return self.response(tts="미니맵입니다. 장소를 선택하면 이동합니다", sfx="open_page")

    def open_inventory(self):
        if self.day_ended:
            return self.night_only_response()
        self.inventory_page = 0
        self.current_page = "inventory"
        self.seed_select_plot_id = None
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.clear_hover()
        self.render()
        return self.response(tts=f"인벤토리입니다. {self.resources['coin']}골드. {self.buff_text()}", sfx="open_page")

    def open_research(self):
        if self.day_ended:
            return self.night_only_response()
        self.current_page = "research"
        self.clear_hover()
        self.render()
        return self.response(tts="연구입니다.", sfx="open_page")

    def return_to_scene(self):
        self.current_page = "home" if self.day_ended else self.current_location
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.clear_care()
        self.clear_harvest()
        self.clear_cooking()
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_page_name(self.current_location)}입니다", sfx="open_page")

    def plot_status_text(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None:
            return "밭 정보 없음"
        label = self.get_plot_label(plot_id)
        if not state.get("seed_id"):
            return f"{label}, 빈 밭. 씨앗을 심으세요"
        seed = self.get_seed_label(state["seed_id"])
        if state["mature"]:
            return f"{label}, {seed}. 수확 가능"
        needed = int(self.get_seed_config(state["seed_id"]).get("growth_days", 3))
        water = "물 완료" if state["watered"] else "물 필요"
        fertilizer = "비료 적용" if state["fertilized"] else "비료 미사용"
        return f"{label}, {seed}. 성장 {needed}일 중 {state['growth']}일. {water}. {fertilizer}"

    def open_plot_detail(self, plot_id):
        unlocked = {p["id"] for p in self.get_unlocked_plot_defs()}
        state = self.farm_plots.get(plot_id)
        if state is None or plot_id not in unlocked:
            return self.response(tts="사용할 수 없는 밭입니다", sfx="error")
        self.detail_plot_id = plot_id
        self.current_location = "farm"
        self.current_page = "plot_detail"
        self.clear_care(keep_detail=True)
        self.clear_harvest()
        self.clear_hover()
        self.render()
        text = self.plot_status_text(plot_id)
        return self.response(tts=text, sfx="open_page")

    def start_care_minigame(self, plot_id, mode):
        state = self.farm_plots.get(plot_id)
        if state is None or state.get("seed_id") is None:
            return self.response(tts="먼저 씨앗을 심어주세요", sfx="error")
        if state.get("mature"):
            return self.response(tts="이미 다 자란 작물입니다. 수확을 진행하세요", sfx="error")
        if mode == "water" and state.get("watered"):
            return self.response(tts="오늘 이미 물을 줬습니다", sfx="error")
        if mode == "fertilizer":
            if not state.get("watered"):
                return self.response(tts="먼저 물을 주세요", sfx="error")
            if state.get("fertilized"):
                return self.response(tts="오늘 이미 비료를 줬습니다", sfx="error")
            if int(self.resources.get("fertilizer", 0)) <= 0:
                return self.response(tts="보유한 비료가 없습니다. 마을 상점에서 구매할 수 있습니다", sfx="error")

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
        mode_label = "물 주기" if mode == "water" else "비료 주기"
        return self.response(
            tts=f"{mode_label}. 누른 채 지점을 지나가세요.",
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
        ratio = collected / total if total else 0.0
        success_ratio = float(self.config.get("care_minigame", {}).get("success_ratio", 0.65))
        percent = int(round(ratio * 100))
        mode = self.care_mode
        plot_id = self.detail_plot_id

        if ratio < success_ratio:
            self.render()
            mode_label = "물" if mode == "water" else "비료"
            return self.response(
                tts=f"{mode_label} {percent}퍼센트. 남은 지점에 이어서 뿌리세요",
                sfx="error"
            )

        if self.defer_visual_completion("care", self.care_visible_until):
            return self.response()

        state = self.farm_plots[plot_id]
        if mode == "water":
            state["watered"] = True
            action_name = "water"
            text = f"물 주기 완료. 잠을 자면 성장합니다"
            sfx = "water"
        else:
            count = int(self.resources.get("fertilizer", 0))
            if count <= 0:
                self.clear_care(keep_detail=True)
                self.current_page = "plot_detail"
                self.render()
                return self.response(tts="보유한 비료가 없어 비료 주기를 완료하지 못했습니다", sfx="error")
            self.resources["fertilizer"] = count - 1
            fertilizer_text = self.apply_fertilizer_bonus(state)
            action_name = "fertilize"
            text = f"비료 완료. {fertilizer_text}. 비료 {self.resources['fertilizer']}개 남음"
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
            return self.response(tts="사용할 수 없는 밭입니다", sfx="error")
        if state["seed_id"] is not None:
            return self.response(tts="이미 작물이 심어진 밭입니다")
        available = [f"{self.get_seed_label(seed_id)} {count}개" for seed_id, count in self.resources["seeds"].items() if int(count) > 0]
        if not available:
            return self.response(tts="보유한 씨앗이 없습니다. 마을 상점에서 씨앗을 구매할 수 있습니다", sfx="error")
        self.seed_select_plot_id = plot_id
        self.current_page = "seed_select"
        self.clear_hover()
        self.render()
        return self.response(tts="씨앗 선택입니다. " + ", ".join(available), sfx="open_page")

    def plant_seed(self, plot_id, seed_id):
        state = self.farm_plots.get(plot_id)
        seed_config = self.get_seed_config(seed_id)
        if state is None or not seed_config:
            return self.response(tts="씨앗을 심을 수 없습니다", sfx="error")
        if state["seed_id"] is not None:
            return self.response(tts="이미 작물이 심어진 밭입니다", sfx="error")
        count = int(self.resources["seeds"].get(seed_id, 0))
        if count <= 0:
            return self.response(tts="해당 씨앗이 없습니다", sfx="error")
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
            return self.night_response(f"{self.get_seed_label(seed_id)} 씨앗을 심었습니다")
        self.render()
        return self.response(tts=f"{self.get_seed_label(seed_id)} 심기 완료. 물을 주고 자세요", sfx="plant")

    def water_plot(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None:
            return self.response()
        label = self.get_plot_label(plot_id)
        if state["seed_id"] is None:
            return self.response(tts=f"{label}은 비어 있습니다. 먼저 씨앗을 심어주세요", sfx="error")
        if state["mature"]:
            return self.response(tts=f"{label}의 작물은 이미 다 자랐습니다", sfx="error")
        if state["watered"]:
            return self.response(tts=f"{label}은 오늘 이미 물을 줬습니다", sfx="error")
        state["watered"] = True
        result = self.consume_time("water")
        if result["night"]:
            return self.night_response(f"{label}에 물을 줬습니다")
        self.render()
        return self.response(tts=f"{label}에 물을 줬습니다. {self.get_seed_label(state['seed_id'])}의 성장은 오늘 밤 잠을 잔 뒤 진행됩니다", sfx="water")

    def apply_fertilizer_bonus(self, state):
        """Apply the saved growth days now; sleep must not apply them twice."""
        needed = int(self.get_seed_config(state["seed_id"]).get("growth_days", 3))
        bonus = max(0, int(self.config.get("fertilizer", {}).get("growth_day_bonus", 1)))
        before = state["growth"]
        state["growth"] = min(needed, before + bonus)
        state["fertilized"] = True
        state["mature"] = state["growth"] >= needed
        saved = state["growth"] - before
        remaining = max(0, needed - state["growth"])
        status = "수확 가능" if state["mature"] else f"물을 주고 {remaining}일 더 자면 수확"
        return f"수확까지 {saved}일 단축. {status}"

    def fertilize_plot(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None:
            return self.response()
        label = self.get_plot_label(plot_id)
        if state["seed_id"] is None:
            return self.response(tts=f"{label}은 비어 있습니다. 비료를 사용할 수 없습니다", sfx="error")
        if state["mature"]:
            return self.response(tts=f"{label}의 작물은 이미 다 자랐습니다", sfx="error")
        if not state["watered"]:
            return self.response(tts=f"{label}에 먼저 물을 주세요", sfx="error")
        if state["fertilized"]:
            return self.response(tts=f"{label}에는 오늘 이미 비료를 사용했습니다", sfx="error")
        count = int(self.resources.get("fertilizer", 0))
        if count <= 0:
            return self.response(tts="보유한 비료가 없습니다. 마을 상점에서 구매할 수 있습니다", sfx="error")
        self.resources["fertilizer"] = count - 1
        fertilizer_text = self.apply_fertilizer_bonus(state)
        result = self.consume_time("fertilize")
        if result["night"]:
            return self.night_response(f"{label}에 비료를 사용했습니다")
        self.render()
        return self.response(tts=f"{label}에 비료를 사용했습니다. {fertilizer_text}. 비료는 {self.resources.get('fertilizer', 0)}개 남았습니다", sfx="fertilize")

    def get_effective_seed_return_chance(self, seed_id):
        base = float(self.get_seed_config(seed_id).get("seed_return_chance", 0.0))
        cfg = self.config.get("research", {}).get("seed_return", {})
        bonus = float(cfg.get("bonus_per_level", 0.1)) * int(self.research_levels.get("seed_return", 0))
        return min(0.95, max(0.0, base + bonus))

    def buy_research(self, research_kind):
        if research_kind == "seed_return":
            cfg = self.config.get("research", {}).get("seed_return", {})
            level = int(self.research_levels.get("seed_return", 0))
            max_level = int(cfg.get("max_level", 3))
            costs = list(cfg.get("costs", []))
            if level >= max_level:
                return self.response(tts="씨앗 회수 연구는 이미 최대 단계입니다", sfx="error")
            cost = int(costs[level]) if level < len(costs) else 999999
            if int(self.resources.get("coin", 0)) < cost:
                return self.response(tts=f"골드가 부족합니다. 씨앗 회수 연구에는 골드 {cost}개가 필요합니다", sfx="error")
            self.resources["coin"] -= cost
            self.research_levels["seed_return"] = level + 1
            result = self.consume_time("research")
            text = f"씨앗 회수 연구를 {level + 1}단계로 올렸습니다. 골드 {cost}개를 사용했습니다"
            if result["night"]:
                return self.night_response(text)
            self.render()
            return self.response(tts=text, sfx="research")

        if research_kind == "field_expand":
            cfg = self.config.get("research", {}).get("field_expansion", {})
            plots = self.config.get("farm", {}).get("plots", [])
            initial = int(cfg.get("initial_plot_count", 2))
            costs = list(cfg.get("costs", []))
            if self.unlocked_plot_count >= len(plots):
                return self.response(tts="밭은 이미 최대 크기입니다", sfx="error")
            index = max(0, self.unlocked_plot_count - initial)
            cost = int(costs[index]) if index < len(costs) else 999999
            if int(self.resources.get("coin", 0)) < cost:
                return self.response(tts=f"골드가 부족합니다. 밭 확장에는 골드 {cost}개가 필요합니다", sfx="error")
            self.resources["coin"] -= cost
            self.unlocked_plot_count += 1
            result = self.consume_time("research")
            text = f"밭을 확장했습니다. 이제 밭 {self.unlocked_plot_count}개를 사용할 수 있습니다. 골드 {cost}개를 사용했습니다"
            if result["night"]:
                return self.night_response(text)
            self.render()
            return self.response(tts=text, sfx="research")
        return self.response()

    def start_harvest_minigame(self, plot_id):
        state = self.farm_plots.get(plot_id)
        if state is None or not state["mature"]:
            return self.response(tts="아직 수확할 수 없습니다", sfx="error")
        cfg = self.config.get("harvest_minigame", {})
        positions = [tuple(v) for v in cfg.get("target_positions", [])]
        target_count = min(int(cfg.get("target_count", 6)), len(positions))
        selected = random.sample(positions, target_count)
        self.harvest_plot_id = plot_id
        self.harvest_targets = [{"id": f"harvest_target_{i}", "x": x, "y": y} for i, (x, y) in enumerate(selected)]
        self.harvest_collected_ids.clear()
        self.harvest_dragging = False
        self.current_page = "harvest"
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_seed_label(state['seed_id'])} 수확. 모든 작물을 모으세요. 시간제한은 없습니다.", sfx="harvest_start")

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
            return self.response(tts=f"수확 {collected}/{total}. 남은 작물을 이어서 수확하세요")

        plot_id = self.harvest_plot_id
        state = self.farm_plots[plot_id]
        seed_id = state["seed_id"]
        seed_config = self.get_seed_config(seed_id)
        seed_label = self.get_seed_label(seed_id)
        base_yield = int(seed_config.get("yield", 1))
        buff_multiplier = 1.0
        buff_applied = False
        if int(self.active_buff.get("remaining_ticks", 0)) > 0:
            buff_multiplier = float(self.active_buff.get("multiplier", 1.0))
            buff_applied = buff_multiplier > 1.0
        yield_count = max(1, int(math.ceil(base_yield * buff_multiplier)))
        self.resources["crops"][seed_id] = int(self.resources["crops"].get(seed_id, 0)) + yield_count

        chance = self.get_effective_seed_return_chance(seed_id)
        got_seed = random.random() < chance
        if got_seed:
            self.resources["seeds"][seed_id] = int(self.resources["seeds"].get(seed_id, 0)) + 1

        self.farm_plots[plot_id] = self.new_plot_state()
        self.current_location = "farm"
        self.current_page = "farm"
        self.detail_plot_id = None
        self.clear_harvest()
        self.clear_hover()

        text = f"수확 완료. {seed_label} {yield_count}개."
        if buff_applied:
            bonus_percent = int(round((buff_multiplier - 1.0) * 100))
            text += f". 수확 버프 +{bonus_percent}퍼센트 적용"
        if got_seed:
            text += f". 씨앗 1개 회수"
        else:
            text += ". 씨앗 회수 없음"

        result = self.consume_time("harvest")
        if result["night"]:
            return self.night_response(text)
        self.render()
        return self.response(tts=text, sfx="harvest")

    def open_recipes(self):
        if self.day_ended:
            return self.night_only_response()
        craftable = [rid for rid in self.config.get("recipes", {}) if self.can_craft_recipe(rid)]
        self.selected_recipe_id = None
        self.selected_ingredients.clear()
        self.current_page = "recipe_select"
        self.clear_hover()
        self.render()
        if not craftable:
            return self.response(tts="요리 레시피입니다. 현재 보유한 작물로 만들 수 있는 요리가 없습니다.", sfx="open_page")
        names = ", ".join(self.get_recipe_label(rid) for rid in craftable)
        return self.response(tts=f"요리 선택입니다.", sfx="open_page")

    def select_recipe(self, recipe_id):
        if not self.can_craft_recipe(recipe_id):
            return self.response(tts="현재 재료로 만들 수 없는 요리입니다", sfx="error")
        self.selected_recipe_id = recipe_id
        self.selected_ingredients.clear()
        self.current_page = "ingredient_select"
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_recipe_label(recipe_id)}. {self.recipe_ingredient_text(recipe_id)}. 재료를 고르고 조리 시작", sfx="open_page")

    def toggle_ingredient(self, seed_id):
        recipe = self.get_recipe_config(self.selected_recipe_id)
        if seed_id not in recipe.get("ingredients", {}):
            return self.response(tts="이 레시피에 필요한 재료가 아닙니다", sfx="error")
        if seed_id in self.selected_ingredients:
            self.selected_ingredients.remove(seed_id)
            text = f"{self.get_seed_label(seed_id)} 선택을 취소했습니다"
        else:
            self.selected_ingredients.add(seed_id)
            label = self.get_seed_label(seed_id)
            particle = self.josa(label, "을", "를")
            text = f"{label}{particle} 재료로 선택했습니다"
        self.clear_hover()
        self.render()
        required = set(recipe.get("ingredients", {}).keys())
        if required.issubset(self.selected_ingredients):
            text += ". 필요한 재료를 모두 선택했습니다."
        return self.response(tts=text, sfx="ingredient_select")

    def get_cooking_steps(self):
        recipe = self.get_recipe_config(self.selected_recipe_id)
        steps = recipe.get("gesture_steps")
        return steps if steps else [recipe.get("gesture", {})]

    def get_cooking_gesture(self):
        steps = self.get_cooking_steps()
        gesture = steps[min(self.cooking_stage_index, len(steps) - 1)]
        path = gesture.get("path", [])
        if gesture.get("kind") != "stir" or len(path) < 2:
            return gesture
        # Enlarge both rendered path and hit-test samples, without editing recipes.
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

    def get_cooking_kind(self):
        return "stir" if self.get_cooking_gesture().get("kind") == "stir" else "cut"

    def cooking_step_text(self):
        label = "젓기" if self.get_cooking_kind() == "stir" else "자르기"
        return f"{self.cooking_stage_index + 1}단계 {label}. 사각형부터 선을 따라 드래그하세요"

    def complete_cooking_step(self):
        self.cooking_dragging = False
        if self.defer_visual_completion("cooking", self.cooking_visible_until):
            return self.response(sfx="cooking_wait")
        if self.cooking_stage_index + 1 >= len(self.get_cooking_steps()):
            return self.finish_cooking_success()
        self.cooking_stage_index += 1
        self.cooking_last_progress_at = None
        self.cooking_resume_marker = False
        self.cooking_progress_index = 0
        self.cooking_visible_until = {}
        self.cooking_path_samples = self.build_path_samples(self.get_cooking_gesture().get("path", []))
        self.clear_hover()
        self.render()
        return self.response(tts="자르기 완료." + self.cooking_step_text(), sfx="cooking_step")

    def open_cooking_minigame(self):
        recipe = self.get_recipe_config(self.selected_recipe_id)
        if not recipe:
            return self.response(tts="먼저 레시피를 선택하세요", sfx="error")
        required = set(recipe.get("ingredients", {}).keys())
        if not required.issubset(self.selected_ingredients):
            return self.response(tts="필요한 재료를 모두 선택하세요", sfx="error")
        if not self.can_craft_recipe(self.selected_recipe_id):
            return self.response(tts="필요한 재료 수량이 부족합니다", sfx="error")
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
        return self.response(tts=f"{self.get_recipe_label(self.selected_recipe_id)}. {self.cooking_step_text()}. 시간제한 없음", sfx="cooking_start")

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
            return self.response(tts="조리 경로를 불러오지 못했습니다", sfx="error")
        recipe = self.get_recipe_config(self.selected_recipe_id)
        tolerance = float(self.get_cooking_gesture().get("tolerance", 4.5))
        resume_index = min(self.cooking_progress_index, len(self.cooking_path_samples) - 1)
        sx, sy = self.cooking_path_samples[resume_index]
        if math.hypot(x - sx, y - sy) > tolerance * 1.35:
            self.cooking_dragging = False
            return self.response(tts="네모 지점에서 눌러 이어가세요", sfx="error")
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
        return self.response(tts=f"진행 {percent}퍼센트. 네모에서 이어가세요. 재료 소모 없음")

    def finish_cooking_success(self):
        recipe_id = self.selected_recipe_id
        recipe = self.get_recipe_config(recipe_id)
        if not recipe or not self.can_craft_recipe(recipe_id):
            self.clear_cooking()
            self.current_page = "home"
            self.current_location = "home"
            self.render()
            return self.response(tts="재료가 부족해 요리를 완성하지 못했습니다", sfx="error")
        for seed_id, count in recipe.get("ingredients", {}).items():
            self.resources["crops"][seed_id] -= int(count)
        self.resources["foods"][recipe_id] = int(self.resources["foods"].get(recipe_id, 0)) + 1
        label = self.get_recipe_label(recipe_id)
        self.current_location = "home"
        self.current_page = "home"
        self.clear_cooking()
        self.clear_hover()
        result = self.consume_time("cook")
        text = f"{label} 1개 완성. 인벤토리에 저장"
        if result["night"]:
            return self.night_response(text)
        self.render()
        return self.response(tts=text, sfx="cooking_success")

    def use_food(self, recipe_id):
        count = int(self.resources["foods"].get(recipe_id, 0))
        recipe = self.get_recipe_config(recipe_id)
        if count <= 0 or not recipe:
            return self.response(tts="보유한 요리가 없습니다", sfx="error")
        self.resources["foods"][recipe_id] = count - 1
        ticks = int(recipe.get("buff_ticks", 0))
        multiplier = float(recipe.get("harvest_multiplier", 1.0))
        current_remaining = int(self.active_buff.get("remaining_ticks", 0))
        self.active_buff = {
            "kind": "harvest_multiplier",
            "source": recipe_id,
            "multiplier": max(multiplier, float(self.active_buff.get("multiplier", 1.0))),
            "remaining_ticks": min(self.time_total_cells, current_remaining + ticks)
        }
        self.clear_hover()
        self.render()
        percent = int(round((self.active_buff["multiplier"] - 1.0) * 100))
        return self.response(tts=f"{self.get_recipe_label(recipe_id)} 사용. 수확 +{percent}퍼센트, {self.active_buff['remaining_ticks']}시간", sfx="eat_food")

    def open_shop(self):
        if self.current_location != "town":
            self.current_location = "town"
        self.current_page = "shop_choice"
        self.clear_hover()
        self.render()
        return self.response(tts="상점입니다. 왼쪽 판매, 오른쪽 구매", sfx="shop_open")

    def open_shop_mode(self, mode):
        if mode == "sell":
            self.current_page = "shop_sell"
            text = "판매 목록."
        else:
            self.current_page = "shop_buy"
            text = "구매 목록."
        self.clear_hover()
        self.render()
        return self.response(tts=text, sfx="open_page")

    def buy_shop_item(self, kind, item_id):
        if kind == "seed":
            seed = self.get_seed_config(item_id)
            if not seed:
                return self.response(tts="판매하지 않는 씨앗입니다", sfx="error")
            price = int(seed.get("seed_price", max(1, round(int(seed.get("crop_price", 1)) * 0.8))))
            label = f"{self.get_seed_label(item_id)} 씨앗"
        elif kind == "fertilizer":
            price = int(self.config.get("fertilizer", {}).get("shop_price", 12))
            label = "비료"
        else:
            return self.response(tts="구매할 수 없는 물건입니다", sfx="error")
        if int(self.resources.get("coin", 0)) < price:
            return self.response(tts=f"골드가 부족합니다. {label} 가격은 {price}골드입니다", sfx="error")
        self.resources["coin"] -= price
        if kind == "seed":
            self.resources["seeds"][item_id] = int(self.resources["seeds"].get(item_id, 0)) + 1
            count = self.resources["seeds"][item_id]
        else:
            self.resources["fertilizer"] = int(self.resources.get("fertilizer", 0)) + 1
            count = self.resources["fertilizer"]
        self.clear_hover()
        self.render()
        return self.response(tts=f"{label} 1개 구매, {price}골드. 보유 {count}개, 잔액 {self.resources['coin']}골드", sfx="shop_buy")

    def sell_shop_item(self, kind, item_id):
        if kind == "crop":
            count = int(self.resources["crops"].get(item_id, 0))
            if count <= 0:
                return self.response(tts="판매할 작물이 없습니다", sfx="error")
            price = int(self.get_seed_config(item_id).get("crop_price", 1))
            label = f"{self.get_seed_label(item_id)} 작물"
            self.resources["crops"][item_id] = count - 1
        elif kind == "food":
            count = int(self.resources["foods"].get(item_id, 0))
            if count <= 0:
                return self.response(tts="판매할 요리가 없습니다", sfx="error")
            price = self.get_food_sell_price(item_id)
            label = self.get_recipe_label(item_id)
            self.resources["foods"][item_id] = count - 1
        else:
            return self.response(tts="판매할 수 없는 물건입니다", sfx="error")
        self.resources["coin"] += price
        self.clear_hover()
        self.render()
        return self.response(tts=f"{label} 1개 판매, +{price}골드. 잔액 {self.resources['coin']}골드", sfx="shop_sell")

    def handle_command(self, command):
        command = str(command).lower().strip()
        if command == "pause":
            self.paused = not self.paused
            if self.paused:
                self.pointer_pressed = False
                self.care_dragging = self.harvest_dragging = self.cooking_dragging = False
                self.drag_tool = None
            return self.response(tts="게임 일시정지" if self.paused else "게임 재개")
        if self.paused:
            return self.response(tts="일시정지를 먼저 해제하세요")
        if self.day_ended:
            if command == "scene":
                return self.return_to_scene()
            return self.night_only_response()
        if command == "minimap":
            return self.open_minimap()
        if command == "scene":
            return self.return_to_scene()
        if command == "resources":
            return self.open_inventory()
        return self.response()

    def resource_summary_text(self):
        seed_total = sum(int(v) for v in self.resources["seeds"].values())
        crop_total = sum(int(v) for v in self.resources["crops"].values())
        food_total = sum(int(v) for v in self.resources["foods"].values())
        return f"골드 {self.resources.get('coin', 0)}개, 비료 {self.resources.get('fertilizer', 0)}개, 씨앗 {seed_total}개, 작물 {crop_total}개, 요리 {food_total}개. {self.buff_text()}"

    def response(self, tts=None, sfx=None, sound_events=None):
        return {"tts": tts, "sfx": sfx, "sound_events": sound_events or [], "priority": "hover" if (sfx or "").startswith("hover_") else "action", "state": self.get_state()}

    def get_state(self):
        self.update_cooking_marker()
        if self.current_page in ("water_minigame", "fertilizer_minigame", "cooking"):
            self.render()
        plots = {plot_id: dict(state) for plot_id, state in self.farm_plots.items()}
        return {
            "objects": [{"id": o["id"], "label": o.get("label", ""),
                         "type": o.get("type"), "x": o.get("x"), "y": o.get("y"),
                         "description": self.get_object_tts(o), "actionable": bool(o.get("action"))}
                        for o in self.get_objects() if o.get("type") != "route"],
            "action_costs": {k: self.get_action_cost(k) for k in ("travel", "plant", "water", "fertilize", "harvest", "research", "cook")},
            "client_settings": self.client_settings,
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
            "research_levels": dict(self.research_levels),
            "unlocked_plot_count": self.unlocked_plot_count,
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
            "inventory": {"page": self.inventory_page + 1, "pages": self.inventory_page_count},
            "cooking": {
                "resume_point": self.cooking_resume_point(),
                "stage_index": self.cooking_stage_index,
                "stage_count": len(self.get_cooking_steps()),
                "gesture_kind": self.get_cooking_kind(),
                "stage_label": "젓기" if self.get_cooking_kind() == "stir" else "자르기",
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
            "time_dots": self.timepad.to_list(),
            "time_width": self.timepad.width,
            "time_height": self.timepad.height,
            "pointer": {"x": self.last_pointer[0], "y": self.last_pointer[1], "pressed": self.pointer_pressed},
            "hover_object": self.hover_object_id,
            "controls": {"F1": "미니맵", "F2": "현재 씬", "F3": "인벤토리", "F4": "일시정지"}
        }

"""Harvest: the crop-collecting minigame on a mature plot, yield, seed recovery and the harvest bonus.

Engine attributes (save format): harvest_plot_id, harvest_targets, harvest_dragging,
harvest_collected_ids. Paired with farming: harvesting resets the plot in farm_plots and clears
detail_plot_id (both owned by farming).
Shared state written: resources crops/seeds, current_page/current_location, last_pointer; spends time.
"""
import math
import random

from engine.core import order
from engine.core.registry import Feature


class Harvest(Feature):
    name = "harvest"

    def register(self, reg):
        reg.owns("harvest_plot_id", "harvest_targets", "harvest_dragging", "harvest_collected_ids")
        reg.slot("harvest.bonus", "Integer added to every harvest yield. Provider returns a number.")
        reg.page("harvest", objects=self.page_objects, guidance=self.guidance,
                 pointer_move=self.move, pointer_down=self.move, pointer_drag=self.move,
                 pointer_up=self.engine.minigame_release)
        reg.action("start_harvest:", lambda arg, obj: self.start(arg))
        reg.renderer("harvest_field", lambda obj: self.engine.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 46), obj.get("height", 30)))
        reg.renderer("harvest_crop", self.draw_crop)
        reg.hover_sfx("harvest_crop", "hover_harvest_crop")
        reg.hover_sfx("harvest_field", "hover_plot")
        reg.state("harvest", self.public_state)
        reg.spectator("harvest_targets", self.spectator_targets)
        reg.on("reset", self.reset, order=order.Reset.HARVEST)
        reg.on("leave_activity", self.clear, order=order.LeaveActivity.HARVEST)
        reg.on("release_drag", self.release)
        reg.save_fields(transient={"harvest_dragging": False})
        reg.expose("start_harvest_minigame", self.start)
        reg.expose("finish_harvest_minigame", self.finish)
        reg.expose("clear_harvest", self.clear)
        reg.expose("get_harvest_base_yield", self.base_yield)

    def reset(self):
        e = self.engine
        e.harvest_plot_id = None
        e.harvest_targets = []
        e.harvest_dragging = False
        e.harvest_collected_ids = set()

    def release(self):
        self.engine.harvest_dragging = False

    def move(self, x, y):
        """Pointer move, press and drag on the harvest page collect the crops they pass."""
        return self.engine.minigame_input(x, y, self.collect_step)

    def collect_step(self, px, py, x, y):
        e = self.engine
        e.harvest_dragging=True
        before=len(e.harvest_collected_ids)
        self.collect_segment(px,py,x,y)
        gained=len(e.harvest_collected_ids)-before
        complete=bool(e.harvest_targets) and len(e.harvest_collected_ids)==len(e.harvest_targets)
        if complete:
            result=self.finish()
        else:
            if gained:e.render()
            result=e.response(sfx='harvest_collect' if gained else None)
        if gained:result.setdefault('sound_events',[]).append({'kind':'correct','count':gained})
        return result

    def guidance(self):
        e = self.engine
        targets = [dict(target) for target in e.harvest_targets if target["id"] not in e.harvest_collected_ids]
        return "crop", targets, len(e.harvest_collected_ids), len(e.harvest_targets)

    def public_state(self):
        e = self.engine
        return {
            "plot_id": e.harvest_plot_id,
            "total_targets": len(e.harvest_targets),
            "collected_targets": len(e.harvest_collected_ids),
            "dragging": e.harvest_dragging
        }

    def spectator_targets(self, objects):
        e = self.engine
        return [dict(id=t['id'], x=t['x'], y=t['y'],
                     collected=t['id'] in e.harvest_collected_ids,
                     visible=t['id'] not in e.harvest_collected_ids)
                for t in e.harvest_targets]

    def clear(self):
        e = self.engine
        e.harvest_plot_id = None
        e.harvest_targets = []
        e.harvest_dragging = False
        e.harvest_collected_ids.clear()

    def page_objects(self):
        e = self.engine
        if e.harvest_plot_id is None:
            return []
        state = e.farm_plots.get(e.harvest_plot_id)
        if state is None or state["seed_id"] is None:
            return []
        seed_label = e.get_seed_label(state["seed_id"])
        field = e.config.get("harvest_minigame", {}).get("field", {})
        objects = [{
            "id": "harvest_field", "type": "harvest_field",
            "x": int(field.get("x", 30)), "y": int(field.get("y", 20)),
            "width": int(field.get("width", 46)), "height": int(field.get("height", 30)),
            "hit_width": int(field.get("width", 46)), "hit_height": int(field.get("height", 30)),
            "label": " Plot",
            "tts": f"Move over crops.",
            "action": ""
        }]
        for target in e.harvest_targets:
            if target["id"] in e.harvest_collected_ids:
                continue
            objects.append({
                "id": target["id"], "type": "harvest_crop", "x": target["x"], "y": target["y"],
                "width": 5, "height": 5, "hit_width": 7, "hit_height": 7,
                "label": f"Harvest {seed_label}", "tts": f"Harvest {seed_label}. Move.", "action": ""
            })
        return objects

    def draw_crop(self, obj):
        e = self.engine
        x, y = int(obj["x"]), int(obj["y"])
        for dx, dy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            e.dotpad.set_dot(x + dx, y + dy)

    def start(self, plot_id):
        e = self.engine
        state = e.farm_plots.get(plot_id)
        if state is None or not state["mature"]:
            return e.response(tts="Crop not ready.", sfx="error")
        cfg = e.config.get("harvest_minigame", {})
        positions = [tuple(v) for v in cfg.get("target_positions", [])]
        target_count = min(int(cfg.get("target_count", 6)), len(positions))
        selected = random.sample(positions, target_count)
        e.harvest_plot_id = plot_id
        e.harvest_targets = [{"id": f"harvest_target_{i}", "x": x, "y": y} for i, (x, y) in enumerate(selected)]
        e.harvest_collected_ids.clear()
        e.harvest_dragging = False
        e.last_pointer = (None, None)
        e.set_page("harvest")
        e.clear_hover()
        e.render()
        return e.response(tts=f"{e.get_seed_label(state['seed_id'])} harvest. Collect all crops.", sfx="harvest_start")

    def press(self, x, y):
        """Unreachable before the split as well: pointer_down sent harvest presses to the minigame
        handler first (follow-up F14). Kept for parity, including its speech line."""
        e = self.engine
        e.harvest_dragging = True
        before = len(e.harvest_collected_ids)
        collected = self.collect_point(x, y)
        if collected:
            e.render()
            return e.response(sfx="harvest_collect", sound_events=[{"kind": "correct", "count": len(e.harvest_collected_ids) - before}])
        return e.response(tts="Harvest. Move over crops.", sfx="tool_pickup")

    def collect_point(self, x, y):
        e = self.engine
        collected = False
        for target in e.harvest_targets:
            if target["id"] not in e.harvest_collected_ids and abs(x - target["x"]) <= 3.5 and abs(y - target["y"]) <= 3.5:
                e.harvest_collected_ids.add(target["id"])
                collected = True
        return collected

    def collect_segment(self, x1, y1, x2, y2):
        e = self.engine
        collected = False
        for target in e.harvest_targets:
            if target["id"] in e.harvest_collected_ids:
                continue
            if e.point_to_segment_distance(target["x"], target["y"], x1, y1, x2, y2) <= 3.5:
                e.harvest_collected_ids.add(target["id"])
                collected = True
        return collected

    def finish(self):
        e = self.engine
        if e.harvest_plot_id is None or not e.harvest_targets:
            self.clear()
            return e.return_to_scene()
        collected = len(e.harvest_collected_ids)
        total = len(e.harvest_targets)
        if collected < total:
            e.render()
            return e.response(tts=f"Harvest {collected}/{total}. Collect remaining crops.")

        plot_id = e.harvest_plot_id
        state = e.farm_plots[plot_id]
        seed_id = state["seed_id"]
        seed_config = e.get_seed_config(seed_id)
        seed_label = e.get_seed_label(seed_id)
        base_yield = self.base_yield(seed_id)
        buff_multiplier = e.buff_multiplier_for("harvest_multiplier")
        buff_applied = buff_multiplier > 1.0
        yield_count = e.loot_amount(max(1, int(math.ceil(base_yield * buff_multiplier)))) + e.registry.total("harvest.bonus")
        e.resources["crops"][seed_id] = int(e.resources["crops"].get(seed_id, 0)) + yield_count

        chance = e.get_effective_seed_return_chance(seed_id)
        got_seed = random.random() < chance
        seed_count = e.loot_amount(1) if got_seed else 0
        if got_seed:
            e.resources["seeds"][seed_id] = int(e.resources["seeds"].get(seed_id, 0)) + seed_count

        e.farm_plots[plot_id] = e.new_plot_state()
        e.current_location = "farm"
        e.set_page("farm")
        e.detail_plot_id = None
        self.clear()
        e.clear_hover()

        text = f"Harvested. {seed_label} {yield_count}."
        e.registry.run("activity", "harvest", seed_label, yield_count)
        if buff_applied:
            text += ". Harvest boost applied."
        if got_seed:
            text += f". {seed_count} seeds recovered."
        else:
            text += ". No seed recovered."

        result = e.consume_time("harvest")
        if result["night"]:
            return e.night_response(text)
        e.render()
        return e.response(tts=text, sfx="harvest")

    def base_yield(self, seed_id):
        e = self.engine
        return int(e.get_seed_config(seed_id).get("yield", 1))

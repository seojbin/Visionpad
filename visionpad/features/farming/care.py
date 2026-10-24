"""The care minigame: cover the water or fertilizer targets on a plot, then apply the effect."""
import math
import random
import time


class CareMinigame:
    def care_objects(self):
        e = self.engine
        plot_id = e.detail_plot_id
        state = e.farm_plots.get(plot_id) if plot_id else None
        if state is None or state.get("seed_id") is None:
            return []
        seed_label = e.get_seed_label(state["seed_id"])
        mode_label = "Water" if e.care_mode == "water" else "Fertilizer"
        field = e.config.get("care_minigame", {}).get("field", {})
        objects = [{
            "id": "care_field", "type": "care_field",
            "x": int(field.get("x", 30)), "y": int(field.get("y", 20)),
            "width": int(field.get("width", 46)), "height": int(field.get("height", 30)),
            "hit_width": int(field.get("width", 46)), "hit_height": int(field.get("height", 30)),
            "label": f"{mode_label} plot",
            "tts": f" {seed_label} plot. Move to apply {mode_label}.",
            "action": ""
        }]
        for target in e.care_targets:
            if (target["id"] in e.care_collected_ids
                    and e.care_visible_until.get(target["id"], 0) <= time.monotonic()):
                continue
            objects.append({
                "id": target["id"], "type": "care_target", "care_kind": e.care_mode,
                "x": target["x"], "y": target["y"],
                "width": 5, "height": 5, "hit_width": 8, "hit_height": 8,
                "label": f"{mode_label} target",
                "tts": f"{mode_label} target. Move.",
                "action": ""
            })
        return objects

    def care_move(self, x, y):
        e = self.engine
        return e.minigame_input(x, y, self.care_step)

    def care_step(self, px, py, x, y):
        e = self.engine
        e.care_dragging=True
        before=len(e.care_collected_ids)
        self.collect_care_segment(px,py,x,y)
        gained=len(e.care_collected_ids)-before
        complete=bool(e.care_targets) and len(e.care_collected_ids) == len(e.care_targets)
        if complete:
            result=self.finish_care()
        else:
            if gained:e.render()
            result=e.response(sfx='care_spray' if gained else None)
        if gained:result.setdefault('sound_events',[]).append({'kind':'correct','count':gained})
        return result

    def start_care(self, plot_id, mode):
        e = self.engine
        e.last_pointer = (None, None)
        state = e.farm_plots.get(plot_id)
        if state is None or state.get("seed_id") is None:
            return e.response(tts="Plant seeds first.", sfx="error")
        if state.get("mature"):
            return e.response(tts="Crop ready. Harvest now.", sfx="error")
        if mode == "water" and state.get("watered"):
            return e.response(tts="Already watered.", sfx="error")
        if mode == "fertilizer":
            if not state.get("watered"):
                return e.response(tts="Water first.", sfx="error")
            if state.get("fertilized"):
                return e.response(tts="Already fertilized.", sfx="error")
            if int(e.resources.get("fertilizer", 0)) <= 0:
                return e.response(tts="No fertilizer. Buy at the shop.", sfx="error")

        cfg = e.config.get("care_minigame", {})
        positions = [tuple(v) for v in cfg.get("target_positions", [])]
        target_count = min(int(cfg.get("target_count", 8)), len(positions))
        selected = random.sample(positions, target_count) if target_count else []
        e.detail_plot_id = plot_id
        e.care_mode = mode
        e.care_targets = [
            {"id": f"care_target_{i}", "x": x, "y": y}
            for i, (x, y) in enumerate(selected)
        ]
        e.care_collected_ids.clear()
        e.care_visible_until = {}
        e.care_dragging = False
        e.set_page("water_minigame" if mode == "water" else "fertilizer_minigame")
        e.clear_hover()
        e.render()
        mode_label = "Water" if mode == "water" else "Fertilize"
        return e.response(
            tts=f"{mode_label}. Move over targets.",
            sfx="care_start"
        )

    def start_care_action(self, arg, obj):
        mode, plot_id = arg.split(":", 1)
        return self.start_care(plot_id, mode)

    def collect_care_point(self, x, y):
        e = self.engine
        collected = False
        tolerance = float(e.config.get("care_minigame", {}).get("tolerance", 4.0))
        for target in e.care_targets:
            if target["id"] not in e.care_collected_ids and math.hypot(x - target["x"], y - target["y"]) <= tolerance:
                e.care_collected_ids.add(target["id"])
                e.care_visible_until[target["id"]] = time.monotonic() + e.disappear_delay_seconds
                collected = True
        return collected

    def collect_care_segment(self, x1, y1, x2, y2):
        e = self.engine
        collected = False
        tolerance = float(e.config.get("care_minigame", {}).get("tolerance", 4.0))
        for target in e.care_targets:
            if target["id"] in e.care_collected_ids:
                continue
            if e.point_to_segment_distance(target["x"], target["y"], x1, y1, x2, y2) <= tolerance:
                e.care_collected_ids.add(target["id"])
                e.care_visible_until[target["id"]] = time.monotonic() + e.disappear_delay_seconds
                collected = True
        return collected

    def finish_care(self):
        e = self.engine
        if e.detail_plot_id is None or not e.care_targets:
            self.clear_care()
            return e.return_to_scene()
        total = len(e.care_targets)
        collected = len(e.care_collected_ids)
        mode = e.care_mode
        plot_id = e.detail_plot_id

        # All visible targets must be collected, regardless of the old
        # care_minigame.success_ratio configuration setting.
        if collected < total:
            e.render()
            mode_label = "Water" if mode == "water" else "Fertilizer"
            return e.response(
                tts=f"{mode_label} {collected} of {total}. Continue over remaining targets.",
                sfx="error"
            )

        if e.defer_visual_completion("care", e.care_visible_until):
            return e.response()

        state = e.farm_plots[plot_id]
        if mode == "water":
            state["watered"] = True
            action_name = "water"
            text = f"Watered. Sleep to grow crops."
            sfx = "water"
        else:
            count = int(e.resources.get("fertilizer", 0))
            if count <= 0:
                self.clear_care(keep_detail=True)
                e.set_page("plot_detail")
                e.render()
                return e.response(tts="No fertilizer. Buy at the shop.", sfx="error")
            e.resources["fertilizer"] = count - 1
            fertilizer_text = self.apply_fertilizer_bonus(state)
            action_name = "fertilize"
            text = f"Fertilized. {fertilizer_text}.  fertilizer {e.resources['fertilizer']} remaining"
            sfx = "fertilize"

        self.clear_care(keep_detail=True)
        e.set_page("plot_detail")
        e.clear_hover()
        result = e.consume_time(action_name)
        if result["night"]:
            return e.night_response(text)
        e.render()
        return e.response(tts=text, sfx=sfx)

    def care_press(self, x, y):
        """Unreachable before the split as well: care presses went to the minigame handler first
        (AUDIT.md section 2.4). Kept for parity."""
        e = self.engine
        e.care_dragging = True
        before = len(e.care_collected_ids)
        collected = self.collect_care_point(x, y)
        if collected:
            e.render()
            return e.response(sfx="care_spray", sound_events=[{"kind": "correct", "count": len(e.care_collected_ids) - before}])
        mode_label = "Water " if e.care_mode == "water" else " fertilizer "
        return e.response(tts=f"{mode_label}. Move over targets.", sfx="tool_pickup")

    def care_guidance(self):
        e = self.engine
        kind = "water" if e.care_mode == "water" else "soil"
        targets = [dict(target) for target in e.care_targets if target["id"] not in e.care_collected_ids]
        return kind, targets, len(e.care_collected_ids), len(e.care_targets)

    def care_state(self):
        e = self.engine
        return {
            "mode": e.care_mode,
            "total_targets": len(e.care_targets),
            "collected_targets": len(e.care_collected_ids),
            "dragging": e.care_dragging
        }

    def spectator_care_targets(self, objects):
        e = self.engine
        now = time.monotonic()
        return [dict(id=t['id'], x=t['x'], y=t['y'],
                     collected=t['id'] in e.care_collected_ids,
                     visible=t['id'] not in e.care_collected_ids or e.care_visible_until.get(t['id'], 0) > now)
                for t in e.care_targets]

    def clear_care(self, keep_detail=False):
        e = self.engine
        if e.pending_visual_completion and e.pending_visual_completion[1] == "care":
            e.pending_visual_completion = None
        e.care_mode = None
        e.care_targets = []
        e.care_dragging = False
        e.care_collected_ids.clear()
        e.care_visible_until = {}
        if not keep_detail:
            e.detail_plot_id = None

    def release(self):
        self.engine.care_dragging = False

"""Versioned local JSON snapshots; twelve newest files are retained."""
import copy
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def encode(value):
    if isinstance(value, (set, tuple)):
        return {"$type": type(value).__name__, "items": [encode(v) for v in value]}
    if isinstance(value, dict):
        return {"$type": "dict", "items": [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    return value


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if isinstance(value, dict):
        kind, items = value["$type"], value["items"]
        if kind == "dict": return {decode(k): decode(v) for k, v in items}
        if kind == "set": return set(map(decode, items))
        if kind == "tuple": return tuple(map(decode, items))
        raise ValueError("Unsupported snapshot type")
    return value


# Key order of save files written before the modular refactor. Features now create their
# attributes in their own reset handlers, so attribute order no longer matches it. snapshot()
# writes these keys in this order, then every other saved attribute in alphabetical order.
SAVE_KEY_ORDER = (
    "rowan_stage", "rowan_greeted", "rowan_dialogue", "rowan_submit_open", "_menu_stack", "sleep_until",
    "pending_visual_completion", "shop_page", "_pickaxe_hits", "inventory_page", "inventory_page_count", "day",
    "current_location", "current_page", "paused", "day_ended", "resources", "research_levels",
    "unlocked_plot_count", "farm_plots", "seed_select_plot_id", "drag_tool", "drag_target_ids",
    "detail_plot_id", "care_mode", "care_targets", "care_dragging", "care_collected_ids", "care_visible_until",
    "harvest_plot_id", "harvest_targets", "harvest_dragging", "harvest_collected_ids", "selected_recipe_id",
    "selected_ingredients", "cooking_dragging", "cooking_path_samples", "cooking_visible_until",
    "cooking_progress_index", "cooking_stage_index", "cooking_last_progress_at", "cooking_resume_marker",
    "active_buff", "hover_object_id", "last_hover_state", "location_detail_spoken", "last_pointer",
    "pointer_pressed", "time_total_cells", "time_used_cells", "mine_rocks", "fishing_last_catch",
    "fishing_attempts", "rod_casts", "rod_catches", "fishing_target", "npc_visits", "dialogue",
    "activity_counts", "activity_serial", "recent_activity", "npc_reactions", "activity_history_complete",
    "flower_seeds", "houseplant", "flower_watering", "flower_contact_at",
)


class SaveMixin:
    def snapshot(self):
        names = [k for k in vars(self)
                 if k not in self._static_fields and k not in {"_static_fields", "_load_return", "_save_slots"}]
        known = set(names)
        ordered = [k for k in SAVE_KEY_ORDER if k in known] + sorted(known.difference(SAVE_KEY_ORDER))
        state = {k: copy.deepcopy(getattr(self, k)) for k in ordered}
        state.update(self.registry.save_transient)
        state["random_state"] = random.getstate()
        now = time.monotonic()
        for key in ("sleep_until", "cooking_last_progress_at"):
            if state.get(key) is not None: state[key] -= now
        for key in ("care_visible_until", "cooking_visible_until"):
            state[key] = {k: v-now for k, v in state.get(key, {}).items()}
        if state.get("pending_visual_completion"):
            deadline, kind = state["pending_visual_completion"]
            state["pending_visual_completion"] = (deadline-now, kind)
        # A physical held gesture cannot safely survive a restart.
        for key in ("pointer_pressed", "care_dragging", "harvest_dragging", "cooking_dragging"):
            state[key] = False
        state["drag_tool"] = None
        state["hover_object_id"] = None
        return state

    def restore_snapshot(self, state):
        state = copy.deepcopy(state)
        state.setdefault("_menu_stack", [])
        # Validate structure against a fresh engine before mutating the live game.
        previous_rng = random.getstate()
        try:
            fresh = type(self)(self.config, save_dir=self.save_dir)
        finally:
            random.setstate(previous_rng)
        for migrate in self.registry.save_migrations:
            migrate(state, fresh)
        for key in self.registry.save_defaults:
            state.setdefault(key, copy.deepcopy(getattr(fresh,key)))
        state.update(self.registry.save_transient)
        expected = set(fresh.snapshot())
        if set(state) != expected: raise ValueError("Incompatible save")
        if any(type(state[k]) is not type(v) and not (type(v) in (int, float) and type(state[k]) in (int, float))
               for k, v in fresh.snapshot().items()
               if v is not None and k not in {"pending_visual_completion", "sleep_until", "cooking_last_progress_at"}):
            raise ValueError("Invalid save state")
        rng = state.pop("random_state")
        random.Random().setstate(rng)
        now = time.monotonic()
        for key in ("sleep_until", "cooking_last_progress_at"):
            if state.get(key) is not None: state[key] += now
        for key in ("care_visible_until", "cooking_visible_until"):
            state[key] = {k: v+now for k, v in state[key].items()}
        if state.get("pending_visual_completion"):
            deadline, kind = state["pending_visual_completion"]
            state["pending_visual_completion"] = (deadline+now, kind)
        fresh.__dict__.update(state)
        fresh.render()
        random.setstate(rng)
        self.__dict__.update(state)
        self._load_return = None
        self.render()

    def list_saves(self):
        slots = []
        for path in sorted(self.save_dir.glob("save_*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("version") != 1: continue
                slots.append({"id": path.stem, "day": int(data["day"]), "created": data["created"]})
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return slots[:12]

    def save_game(self):
        state = self._load_return if self.current_page == "load_game" else self.snapshot()
        stamp = datetime.now(timezone.utc)
        name = "save_" + stamp.strftime("%Y%m%dT%H%M%S%f") + "_" + uuid4().hex[:8]
        try:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            target = self.save_dir / (name + ".json")
            temp = self.save_dir / (name + ".tmp")
            data = {"version": 1, "created": stamp.isoformat(), "day": state["day"], "state": encode(state)}
            temp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            os.replace(temp, target)
            for old in sorted(self.save_dir.glob("save_*.json"), reverse=True)[12:]: old.unlink()
        except (OSError, ValueError, TypeError):
            return self.response(tts="Could not save the game.", sfx="error")
        if self.current_page == "load_game":
            self._save_slots = self.list_saves()
            self.render()
        self.pointer_pressed = False
        self.care_dragging = self.harvest_dragging = self.cooking_dragging = False
        self.drag_tool = None
        return self.response(tts="Game saved.", sfx="saved")

    def open_load_game(self):
        if self.current_page != "load_game": self._load_return = self.snapshot()
        self._save_slots = self.list_saves()
        self.current_page = "load_game"
        self.paused = False
        self.day_ended = False
        self.sleep_until = None
        self.pending_visual_completion = None
        self.pointer_pressed = False
        self.clear_hover()
        self.render()
        return self.response(tts="Choose a save." if self._save_slots else "No saved games.", sfx="open_page")

    def close_load_game(self):
        if self._load_return is not None: self.restore_snapshot(self._load_return)
        self._menu_stack.clear()
        return self.return_to_scene()

    def load_game(self, slot_id):
        if self.current_page != "load_game" or slot_id not in {s["id"] for s in self._save_slots}:
            return self.response(tts="Save unavailable.", sfx="error")
        try:
            data = json.loads((self.save_dir / (slot_id + ".json")).read_text(encoding="utf-8"))
            if data["version"] != 1: raise ValueError("Save version")
            self.restore_snapshot(decode(data["state"]))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return self.response(tts="Could not load this save.", sfx="error")
        return self.response(tts=f"Game loaded. Day {self.day}. {self.get_page_name(self.current_page)}.", sfx="loaded")

    def get_load_objects(self):
        objects = []
        for i, slot in enumerate(self._save_slots):
            objects.append({"id": slot["id"], "type": "save_slot", "x": 8+14*(i%4), "y": 5+10*(i//4),
                            "width": 12, "height": 8, "hit_width": 12, "hit_height": 8,
                            "label": f"Save {i+1}", "tts": f"Save {i+1}. Day {slot['day']}. {slot['created'][:16].replace('T', ' ')} UTC.",
                            "action": "load_slot:"+slot["id"]})
        objects.append(self.back_arrow("load_back", "Back", "close_load"))
        return objects

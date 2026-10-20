"""Rowan advice and recent-activity reactions alongside the village tutorial."""
import json
from pathlib import Path

NPCS = json.loads((Path(__file__).with_name("npc_config.json")).read_text(encoding="utf-8"))


class NpcMixin:
    def reset_npcs(self):
        self.npc_visits = {}
        self.dialogue = None
        self.activity_counts = {}
        self.activity_serial = 0
        self.recent_activity = None
        self.npc_reactions = {}
        self.activity_history_complete = True

    def record_activity(self, kind, item="", count=1):
        self.activity_serial += 1
        self.activity_counts[kind] = self.activity_counts.get(kind, 0) + 1
        self.recent_activity = {"id": self.activity_serial, "kind": kind, "item": item,
                                "count": count, "day": self.day,
                                "first": self.activity_history_complete and self.activity_counts[kind] == 1}

    def recent_reaction(self, npc_id):
        event = self.recent_activity
        if not event or event["id"] <= self.npc_reactions.get(npc_id, 0):
            return ""
        reactions = NPCS[npc_id].get("reactions", {})
        key = ("first_" if event["first"] else "") + event["kind"]
        template = reactions.get(key) or reactions.get(event["kind"])
        if not template:
            return ""
        self.npc_reactions[npc_id] = event["id"]
        return template.format(item=event["item"], count=event["count"])

    def show_rowan(self, text, page="rowan_dialogue", events=None):
        reaction = self.recent_reaction("shopkeeper")
        if reaction:
            text += " " + reaction
        result = super().show_rowan(text, page, events)
        result["speech_profile"] = NPCS["shopkeeper"]["voice_profile"]
        result["priority"] = "dialogue"
        return result

    def current_dialogue(self):
        if self.current_page == "npc_dialogue" and self.dialogue:
            return {**self.dialogue, "speaker": self.dialogue["name"]}
        if self.current_page in ("town", "rowan_submit") and self.rowan_dialogue:
            return {"npc_id": "shopkeeper", "speaker": "Rowan", "name": "Rowan",
                    "text": self.rowan_dialogue, "profile": "shopkeeper", "channel": "quest"}
        return None

    def rowan_advice(self, topic):
        npc = NPCS["shopkeeper"]
        if topic == "fishing":
            return npc["fishing"]["with_rod" if self.resources.get("fishing_rod") else "without_rod"]
        plots = [plot for plot in self.farm_plots.values() if plot.get("seed_id")]
        condition = ("ready" if any(plot.get("mature") for plot in plots)
                     else "needs_water" if any(not plot.get("watered") for plot in plots)
                     else "growing" if plots else "empty")
        return npc["farming"][condition]

    def next_rowan_advice(self):
        visits = self.npc_visits.get("tutorial_advice", 0)
        self.npc_visits["tutorial_advice"] = visits + 1
        return self.rowan_advice("fishing" if visits % 2 == 0 else "farming")

    def get_dialogue_objects(self):
        if not self.dialogue:
            return [self.back_arrow("dialogue_exit", "Back to village", "return_scene")]
        topics = [("farming", "Farming", 15, 9), ("fishing", "Fishing", 43, 9),
                  ("trade", "Open shop", 15, 25), ("goodbye", "Goodbye", 43, 25)]
        return [{"id": "dialogue_" + topic, "type": "npc_topic", "x": x, "y": y,
                 "width": 20, "height": 10, "hit_width": 22, "hit_height": 12,
                 "label": label, "tts": label, "action": "npc:shopkeeper:" + topic}
                for topic, label, x, y in topics] + [self.back_arrow("dialogue_back", "Back to village", "return_scene")]

    def npc_action(self, npc_id, topic):
        if (npc_id not in NPCS or self.current_location != "town"
                or self.current_page not in ("town", "shop_choice", "npc_dialogue")
                or self.sleep_until is not None or self.day_ended or self.paused):
            return self.response()
        self.dialogue = None
        return self.talk_rowan()

"""Rowan's advice, one-time reactions to recent results, and the activity log behind them.

Engine attributes (save format): npc_visits, dialogue, activity_counts, activity_serial,
recent_activity, npc_reactions, activity_history_complete.
Listens to the `activity` event; talking goes through the village quest (engine.talk_rowan()).
"""
from visionpad.config import load_config
from visionpad.core import order
from visionpad.core.registry import Feature

NPCS = load_config("npc")


class Npc(Feature):
    name = "npc"

    def register(self, reg):
        reg.owns("npc_visits", "dialogue", "activity_counts", "activity_serial", "recent_activity",
                 "npc_reactions", "activity_history_complete")
        reg.page("npc_dialogue", name="Conversation", objects=self.dialogue_objects)
        reg.action("npc:", self.action, before_night_guard=True)
        reg.renderer("npc_marker", lambda obj: self.engine.draw_shop_npc({**obj, "type": "shop_npc"}))
        reg.renderer("npc_topic", lambda obj: self.engine.dotpad.draw_box(obj["x"], obj["y"], obj["width"], obj["height"]))
        reg.state("dialogue", self.current_dialogue)
        reg.on("reset", self.reset, order=order.Reset.NPC)
        reg.on("activity", self.record_activity)
        reg.save_fields(defaults=("npc_visits", "dialogue", "activity_counts", "activity_serial",
                                  "recent_activity", "npc_reactions"),
                        migrate=self.migrate)
        reg.expose("npc_action", self.npc_action)
        reg.expose("record_activity", self.record_activity)
        reg.expose("recent_reaction", self.recent_reaction)
        reg.expose("rowan_advice", self.rowan_advice)
        reg.expose("next_rowan_advice", self.next_rowan_advice)
        reg.expose("npc_voice_profile", lambda npc_id: NPCS[npc_id]["voice_profile"])

    def reset(self):
        e = self.engine
        e.npc_visits = {}
        e.dialogue = None
        e.activity_counts = {}
        e.activity_serial = 0
        e.recent_activity = None
        e.npc_reactions = {}
        e.activity_history_complete = True

    @staticmethod
    def migrate(state, fresh):
        # Historical saves cannot prove whether a harvest/catch was the first ever.
        state.setdefault('activity_history_complete', False)
        if state.get('current_page') == 'npc_dialogue':
            state['dialogue'] = None
            state['current_page'] = state['current_location'] = 'town'

    def record_activity(self, kind, item="", count=1):
        e = self.engine
        e.activity_serial += 1
        e.activity_counts[kind] = e.activity_counts.get(kind, 0) + 1
        e.recent_activity = {"id": e.activity_serial, "kind": kind, "item": item,
                             "count": count, "day": e.day,
                             "first": e.activity_history_complete and e.activity_counts[kind] == 1}

    def recent_reaction(self, npc_id):
        e = self.engine
        event = e.recent_activity
        if not event or event["id"] <= e.npc_reactions.get(npc_id, 0):
            return ""
        reactions = NPCS[npc_id].get("reactions", {})
        key = ("first_" if event["first"] else "") + event["kind"]
        template = reactions.get(key) or reactions.get(event["kind"])
        if not template:
            return ""
        e.npc_reactions[npc_id] = event["id"]
        return template.format(item=event["item"], count=event["count"])

    def current_dialogue(self):
        e = self.engine
        if e.current_page == "npc_dialogue" and e.dialogue:
            return {**e.dialogue, "speaker": e.dialogue["name"]}
        if e.current_page in ("town", "rowan_submit") and e.rowan_dialogue:
            return {"npc_id": "shopkeeper", "speaker": "Rowan", "name": "Rowan",
                    "text": e.rowan_dialogue, "profile": "shopkeeper", "channel": "quest"}
        return None

    def rowan_advice(self, topic):
        e = self.engine
        npc = NPCS["shopkeeper"]
        if topic == "fishing":
            return npc["fishing"]["with_rod" if e.resources.get("fishing_rod") else "without_rod"]
        plots = [plot for plot in e.farm_plots.values() if plot.get("seed_id")]
        condition = ("ready" if any(plot.get("mature") for plot in plots)
                     else "needs_water" if any(not plot.get("watered") for plot in plots)
                     else "growing" if plots else "empty")
        return npc["farming"][condition]

    def next_rowan_advice(self):
        e = self.engine
        visits = e.npc_visits.get("tutorial_advice", 0)
        e.npc_visits["tutorial_advice"] = visits + 1
        return self.rowan_advice("fishing" if visits % 2 == 0 else "farming")

    def dialogue_objects(self):
        e = self.engine
        if not e.dialogue:
            return [e.back_arrow("dialogue_exit", "Back to village", "return_scene")]
        topics = [("farming", "Farming", 15, 9), ("fishing", "Fishing", 43, 9),
                  ("trade", "Open shop", 15, 25), ("goodbye", "Goodbye", 43, 25)]
        return [{"id": "dialogue_" + topic, "type": "npc_topic", "x": x, "y": y,
                 "width": 20, "height": 10, "hit_width": 22, "hit_height": 12,
                 "label": label, "tts": label, "action": "npc:shopkeeper:" + topic}
                for topic, label, x, y in topics] + [e.back_arrow("dialogue_back", "Back to village", "return_scene")]

    def action(self, arg, obj):
        parts = arg.split(":")
        return self.npc_action(parts[0], parts[1]) if len(parts) == 2 else self.engine.response()

    def npc_action(self, npc_id, topic):
        e = self.engine
        if (npc_id not in NPCS or e.current_location != "town"
                or e.current_page not in ("town", "shop_choice", "npc_dialogue")
                or e.sleep_until is not None or e.day_ended or e.paused):
            return e.response()
        e.dialogue = None
        return e.talk_rowan()

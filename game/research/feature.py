"""Research upgrades bought at home: seed recovery, farm expansion and mineral discovery.

Engine attributes (save format): research_levels, unlocked_plot_count.
Shared state written: resources (coin, copper, stone, iron), current_page; spends time.
"""
from engine.core import order
from engine.core.registry import Feature
from engine.display.icons import IconRenderer

RESEARCH_SYMBOLS = {'seed_return': 'seed', 'field_expand': 'tool', 'mineral_luck': 'mineral'}


class Research(Feature):
    name = "research"

    def register(self, reg):
        reg.owns("research_levels", "unlocked_plot_count")
        reg.page("research", objects=self.page_objects, icon_grid=True)
        reg.action("open_research", self.open)
        reg.action("research:", self.buy)
        reg.icon("research", pattern=self.icon_pattern)
        reg.object_tts("research", self.object_tts)
        reg.hover_sfx("research", "hover_research")
        reg.state("research_levels", lambda: dict(self.engine.research_levels))
        reg.state("unlocked_plot_count", lambda: self.engine.unlocked_plot_count)
        reg.on("reset", self.reset, order=order.Reset.RESEARCH)

    def reset(self):
        e = self.engine
        research = e.config.get("research", {})
        expansion = research.get("field_expansion", {})
        e.research_levels = {"seed_return": 0, "mineral_luck": 0}
        e.unlocked_plot_count = int(expansion.get("initial_plot_count", 2))

    @staticmethod
    def icon_pattern(obj):
        symbol = RESEARCH_SYMBOLS.get(obj.get('research_kind'), 'chest')
        return IconRenderer.PATTERNS.get(symbol, IconRenderer.PATTERNS['material'])

    @staticmethod
    def object_tts(obj):
        """Short hover: the label plus the structured cost fields that drive the research icon."""
        label = str(obj.get("label") or "Object").strip()
        costs = obj.get("display_quantities") or []
        info = [f"{item.get('required')} {item.get('label', item.get('item', ''))}"
                for item in costs if item.get("required") is not None]
        return f"{label}, {', '.join(info)}." if info else label

    def page_objects(self):
        e = self.engine
        objects = []
        coin = int(e.resources.get("coin", 0))
        seed_cfg = e.config.get("research", {}).get("seed_return", {})
        level = int(e.research_levels.get("seed_return", 0))
        max_level = int(seed_cfg.get("max_level", 2))
        costs = list(seed_cfg.get("costs", []))

        if level >= max_level:
            seed_tts = f"Seed recovery. Level {level}. Maximum level."
            seed_action = ""
        else:
            cost = int(costs[level]) if level < len(costs) else 999999
            copper_cost = int(seed_cfg.get("copper_costs", [3, 6])[level])
            seed_tts = f"Seed recovery, level {level}. Next level:  {cost} gold, Copper {copper_cost} required"
            seed_action = "research:seed_return"

        objects.append({
            "id": "research_seed_return", "type": "research", "research_kind": "seed_return",
            "x": 19, "y": 18, "width": 18, "height": 12, "hit_width": 20, "hit_height": 14,
            "label": "Seed recovery", "tts": seed_tts, "action": seed_action
        })

        expand_cfg = e.config.get("research", {}).get("field_expansion", {})
        all_plots = e.config.get("farm", {}).get("plots", [])
        costs = list(expand_cfg.get("costs", []))
        initial = int(expand_cfg.get("initial_plot_count", 2))
        expansion_index = max(0, e.unlocked_plot_count - initial)
        if e.unlocked_plot_count >= len(all_plots):
            expand_tts = f"Farm expansion. Plots: {e.unlocked_plot_count} "
            expand_action = ""
        else:
            cost = int(costs[expansion_index]) if expansion_index < len(costs) else 999999
            material_cost = int(expand_cfg.get("stone_costs", [5, 10])[expansion_index])
            expand_tts = f"Plot {e.unlocked_plot_count}. {cost} gold, Stone {material_cost} to add a plot. Gold: {coin} gold"
            expand_action = "research:field_expand"

        objects.append({
            "id": "research_field_expand", "type": "research", "research_kind": "field_expand",
            "x": 41, "y": 18, "width": 18, "height": 12, "hit_width": 20, "hit_height": 14,
            "label": "Farm expansion", "tts": expand_tts, "action": expand_action
        })
        for kind, label, mineral in [("mineral_luck", "Mineral discovery", "iron")]:
            cfg = e.config.get("research", {}).get(kind, {})
            level = e.research_levels.get(kind, 0)
            action = "" if level >= int(cfg.get("max_level", 2)) else f"research:{kind}"
            text = f"{label}. Level {level}. Maximum level." if not action else f"{label}. Level {level + 1}. Requires {cfg.get('costs', [20, 40])[level]} gold, {e.MINERAL_LABELS[mineral]} {cfg.get(mineral + '_costs', [3, 6])[level]} required"
            objects.append({"id": f"research_{kind}", "type": "research", "research_kind": kind, "label": label, "tts": text, "action": action})
        for i, obj in enumerate(objects):
            obj.update(x=8+15*(i%3), y=6+12*(i//3), width=12, height=8, hit_width=12, hit_height=8)
            kind = obj["research_kind"]
            key = "field_expansion" if kind == "field_expand" else kind
            cfg = e.config.get("research", {}).get(key, {})
            index = expansion_index if kind == "field_expand" else e.research_levels.get(kind, 0)
            material = {"seed_return": "copper", "field_expand": "stone", "mineral_luck": "iron"}[kind]
            obj["display_quantities"] = []
            if obj.get("action"):
                costs = cfg.get("costs", [])
                materials = cfg.get(material + "_costs", [3, 6] if material != "stone" else [5, 10])
                for resource, required in [("coin", costs[index] if index < len(costs) else 999999),
                                           (material, materials[index])]:
                    obj["display_quantities"].append({"item": resource, "label": "Gold" if resource == "coin" else resource.title(),
                                                    "required": int(required), "owned": int(e.resources.get(resource, 0))})
        objects.append(e.back_arrow("research_back", "Back home", "return_scene"))
        return objects

    def open(self, arg=None, obj=None):
        e = self.engine
        if e.day_ended:
            return e.night_only_response()
        e.set_page("research")
        e.clear_hover()
        e.render()
        return e.response(tts="Research.", sfx="open_page")

    def buy(self, research_kind, obj=None):
        e = self.engine
        if research_kind == "mineral_luck":
            return self.buy_mineral(research_kind)
        if research_kind == "seed_return":
            cfg = e.config.get("research", {}).get("seed_return", {})
            level = int(e.research_levels.get("seed_return", 0))
            max_level = int(cfg.get("max_level", 2))
            costs = list(cfg.get("costs", []))
            if level >= max_level:
                return e.response(tts="Seed recovery at maximum level.", sfx="error")
            cost = int(costs[level]) if level < len(costs) else 999999
            copper_cost = int(cfg.get("copper_costs", [3, 6])[level])
            if e.resources["copper"] < copper_cost:
                return e.response(tts=f"Copper {copper_cost} required", sfx="error")
            if int(e.resources.get("coin", 0)) < cost:
                return e.response(tts=f"Not enough gold. Need {cost}.", sfx="error")
            e.add_resource("coin", -cost)
            e.add_resource("copper", -copper_cost)
            e.research_levels["seed_return"] = level + 1
            result = e.consume_time("research")
            text = f"Seed recovery level {level + 1}. Gold spent: {cost}."
            if result["night"]:
                return e.night_response(text, sound_events=[{"kind": "one_shot", "sound": "coin"}] if cost > 0 else [])
            e.render()
            return e.response(tts=text, sfx="research", sound_events=[{"kind": "one_shot", "sound": "coin"}] if cost > 0 else [])

        if research_kind == "field_expand":
            cfg = e.config.get("research", {}).get("field_expansion", {})
            plots = e.config.get("farm", {}).get("plots", [])
            initial = int(cfg.get("initial_plot_count", 2))
            costs = list(cfg.get("costs", []))
            if e.unlocked_plot_count >= len(plots):
                return e.response(tts="All plots unlocked.", sfx="error")
            index = max(0, e.unlocked_plot_count - initial)
            cost = int(costs[index]) if index < len(costs) else 999999
            material_cost = int(cfg.get("stone_costs", [5, 10])[index])
            if e.resources["stone"] < material_cost:
                return e.response(tts=f"Stone {material_cost} required", sfx="error")
            if int(e.resources.get("coin", 0)) < cost:
                return e.response(tts=f"Not enough gold. Need {cost}.", sfx="error")
            e.add_resource("coin", -cost)
            e.add_resource("stone", -material_cost)
            e.unlocked_plot_count += 1
            result = e.consume_time("research")
            text = f"Farm expanded. Plots: {e.unlocked_plot_count}. Gold spent: {cost}."
            if result["night"]:
                return e.night_response(text, sound_events=[{"kind": "one_shot", "sound": "coin"}] if cost > 0 else [])
            e.render()
            return e.response(tts=text, sfx="research", sound_events=[{"kind": "one_shot", "sound": "coin"}] if cost > 0 else [])
        return e.response()

    def buy_mineral(self, kind):
        e = self.engine
        if kind != "mineral_luck":
            return e.response(tts="Research unavailable.", sfx="error")
        cfg = e.config.get("research", {}).get(kind, {})
        level = e.research_levels.get(kind, 0)
        maximum = int(cfg.get("max_level", 2))
        if level >= maximum:
            return e.response(tts="Maximum research level.", sfx="error")
        mineral = "iron"
        costs, materials = cfg.get("costs", [20, 40]), cfg.get(f"{mineral}_costs", [3, 6])
        cost, material_cost = int(costs[level]), int(materials[level])
        if e.resources["coin"] < cost or e.resources[mineral] < material_cost:
            return e.response(tts=f"Not enough materials. Need {cost} gold, {e.MINERAL_LABELS[mineral]} {material_cost} required", sfx="error")
        e.add_resource("coin", -cost)
        e.add_resource(mineral, -material_cost)
        e.research_levels[kind] = level + 1
        text = f"Mineral discovery level {level + 1} complete."
        result = e.consume_time("research")
        events = [{"kind": "one_shot", "sound": "coin"}]
        if result["night"]:
            return e.night_response(text, sound_events=events)
        e.clear_hover()
        e.render()
        return e.response(tts=text, sound_events=events)

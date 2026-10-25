"""F1 map: compressed location nodes and paths; selecting a node travels there.

Owns no engine attributes. Shared state written: current_page (open), via
return_to_scene/travel_to in core.
"""
from engine.core.registry import Feature


class Minimap(Feature):
    name = "minimap"

    def register(self, reg):
        reg.page("minimap", objects=self.page_objects, menu_text=lambda: 'Map. Select a place.',
                 navigate=self.navigate)
        reg.renderer("node", self.draw_node)
        reg.renderer("route", self.draw_route)
        reg.hit_test("route", self.route_contains)
        reg.object_tts("node", self.label_only)
        reg.object_tts("route", self.label_only)
        reg.hover_sfx("node", "hover_node")
        reg.hover_sfx("route", "hover_route")

    @staticmethod
    def label_only(obj):
        """A map location or path has only a name in standard hover."""
        return str(obj.get("label") or "Object").strip()

    def page_objects(self):
        e = self.engine
        cfg = e.config.get("minimap", {})
        locations = [dict(o) for o in cfg.get("locations", [])]
        if not locations: return []
        tx = e.compress_axis([(o["x"]-3,o["x"]+3) for o in locations])
        ty = e.compress_axis([(o["y"]-3,o["y"]+3) for o in locations])
        objects = []
        for route in cfg.get("routes", []):
            obj = dict(route)
            obj.update(type="route", x1=round(tx(route["x1"])), x2=round(tx(route["x2"])),
                       y1=round(ty(route["y1"])), y2=round(ty(route["y2"])),
                       label="Path", tts="Path", hit_radius=1)
            objects.append(obj)
        current = next((o for o in locations if o.get("location")==e.current_location), None)
        for source in locations:
            obj = dict(source)
            location = obj["location"]
            label = e.get_page_name(location)
            here = location == e.current_location
            direction = e.get_relative_direction(current, source) if current and not here else ""
            obj.update(type="node", x=round(tx(source["x"])), y=round(ty(source["y"])),
                       width=7, height=7, hit_width=7, hit_height=7, current=here,
                       label=label, tts=label+(". You are here." if here else (f". {direction}." if direction else ".")),
                       action=f"travel:{location}")
            objects.append(obj)
        return objects

    def navigate(self, direction):
        """Left or Right closes the map and returns to the current region."""
        e = self.engine
        if e.paused: return e.response(tts='Resume first.')
        if e.sleep_until is not None: return e.response(tts='Sleeping. Please wait.')
        e._menu_stack.clear()
        return e.return_to_scene()

    def draw_node(self, obj):
        e = self.engine
        if obj.get("current"):
            e.draw_filled_square(obj["x"], obj["y"], 7)
        else:
            e.dotpad.draw_box(obj["x"], obj["y"], 7, 7)

    def route_contains(self, obj, x, y):
        distance = self.engine.point_to_segment_distance(x, y, obj["x1"], obj["y1"], obj["x2"], obj["y2"])
        return distance <= float(obj.get("hit_radius", 3.0))

    def draw_route(self, obj):
        self.engine.dotpad.draw_line(obj["x1"], obj["y1"], obj["x2"], obj["y2"])

    def open(self):
        """Unused before the split as well (F1 opens the map through toggle_menu); kept for parity."""
        e = self.engine
        if e.day_ended:
            return e.night_only_response()
        e.set_page("minimap")
        e.seed_select_plot_id = None
        e.leave_activities()
        e.clear_hover()
        e.render()
        return e.response(tts="Map.", sfx="open_page")

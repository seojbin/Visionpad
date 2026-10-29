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
        tx = e.compress_axis([(o["x"]-3,o["x"]+3) for o in locations], max_gap=6)
        ty = e.compress_axis([(o["y"]-3,o["y"]+3) for o in locations])
        # Keep the compressed topology, but anchor Home at the pad centre.
        home = next((o for o in locations if o.get("location") == "home"), locations[0])
        offset_x = e.dotpad.width // 2 - round(tx(home["x"]))
        offset_y = e.dotpad.height // 2 - round(ty(home["y"]))
        objects = []
        for route in cfg.get("routes", []):
            obj = dict(route)
            obj.update(type="route", x1=round(tx(route["x1"])) + offset_x, x2=round(tx(route["x2"])) + offset_x,
                       y1=round(ty(route["y1"])) + offset_y, y2=round(ty(route["y2"])) + offset_y,
                       label="Path", tts="Path", hit_radius=1)
            objects.append(obj)
        current = next((o for o in locations if o.get("location")==e.current_location), None)
        for source in locations:
            obj = dict(source)
            location = obj["location"]
            label = e.get_page_name(location)
            here = location == e.current_location
            direction = e.get_relative_direction(current, source) if current and not here else ""
            obj.update(type="node", x=round(tx(source["x"])) + offset_x, y=round(ty(source["y"])) + offset_y,
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
        # Exact seven-dot bounds for both empty and filled nodes. Clear paths
        # beneath the node, leaving connections outside its frame intact.
        left, top = round(obj['x'])-3, round(obj['y'])-3
        for dy in range(7):
            for dx in range(7):
                raised = obj.get('current') or dx in (0,6) or dy in (0,6)
                e.dotpad.set_dot(left+dx,top+dy,int(bool(raised)))

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

"""F1 map: compressed location nodes and paths; selecting a node travels there.

Owns no engine attributes. Shared state written: current_page (open), via
return_to_scene/travel_to in core.
"""
from engine.core.registry import Feature
from engine.display.tactile import MIN_GAP


class Minimap(Feature):
    name = "minimap"

    def register(self, reg):
        reg.slot("minimap.objects", "Extra objects on the F1 map (for example the Guide button). "
                                    "Provider returns a list of objects placed clear of the location nodes.")
        reg.page("minimap", objects=self.page_objects, navigate=self.navigate,
                 menu_text=lambda: 'Map. Select a place.' + (' The guide is at the top left.' if self.engine.registry.collect("minimap.objects") else ''))
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
        self.clear_route_ends(objects)
        return objects + self.engine.registry.collect("minimap.objects")

    @staticmethod
    def clear_route_ends(objects, gap=MIN_GAP):
        """Shorten each path so it stops `gap` lowered pins before a node frame instead of running into it.

        Tactile design rules (README.md): a line never touches a symbol; the reader feels the node's
        whole frame and then a short break before the path continues.
        """
        boxes = [(o["x"] - 3 - gap, o["y"] - 3 - gap, o["x"] + 3 + gap, o["y"] + 3 + gap)
                 for o in objects if o.get("type") == "node"]

        def inside(x, y):
            return any(left <= x <= right and top <= y <= bottom for left, top, right, bottom in boxes)

        for route in (o for o in objects if o.get("type") == "route"):
            x1, y1, x2, y2 = route["x1"], route["y1"], route["x2"], route["y2"]
            sx, sy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
            while (x1, y1) != (x2, y2) and inside(x1, y1):
                x1, y1 = x1 + sx, y1 + sy
            while (x1, y1) != (x2, y2) and inside(x2, y2):
                x2, y2 = x2 - sx, y2 - sy
            route.update(x1=x1, y1=y1, x2=x2, y2=y2)

    def navigate(self, direction):
        """Left or Right closes the map and returns to the current region."""
        e = self.engine
        if e.paused: return e.response(tts='Resume first.')
        if e.sleep_until is not None: return e.response(tts='Sleeping. Please wait.')
        e._menu_stack.clear()
        return e.return_to_scene()

    def draw_node(self, obj):
        e = self.engine
        # Exact seven-dot frame. The current place ("you are here") adds a small solid 3x3 mark in the
        # centre instead of filling the whole node (large filled shapes are hard to read by touch).
        left, top = round(obj['x'])-3, round(obj['y'])-3
        for dy in range(7):
            for dx in range(7):
                frame = dx in (0,6) or dy in (0,6)
                mark = obj.get('current') and 2 <= dx <= 4 and 2 <= dy <= 4
                e.dotpad.set_dot(left+dx,top+dy,int(bool(frame or mark)))

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

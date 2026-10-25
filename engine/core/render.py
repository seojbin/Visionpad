"""Dot-pad rendering: the page loop over registered renderers and shared drawing primitives."""
import math


class Rendering:
    def render(self):
        self.dotpad.clear()
        if self.sleep_until is not None:
            self.timepad.clear()
            return
        for obj in self.get_objects():
            if self.icons.draw(obj):
                continue
            obj_type = obj.get("type")
            renderer = self.registry.renderers.get(obj_type)
            if renderer:
                renderer(obj)
            elif obj_type == "save_slot":
                self.dotpad.draw_box(obj["x"], obj["y"], obj["width"], obj["height"])
                self.dotpad.draw_box(obj["x"], obj["y"], 4, 4)
            elif obj_type == "arrow":
                self.draw_triangle(obj["x"], obj["y"], obj["direction"], obj.get("size", 2))
            elif obj_type == "box":
                self.dotpad.draw_box(obj["x"], obj["y"], obj.get("width", 6), obj.get("height", 5))

        scene = self.registry.page_hook(self.current_page, "scene")
        if scene:
            scene()
        self.draw_time_bar()

    def draw_solid_pattern(self, cx, cy, rows):
        """Centered pattern: '1' raises a dot, '0' clears it, any other character leaves it."""
        pad = self.dotpad
        w, h = len(rows[0]), len(rows)
        for r_idx, row in enumerate(rows):
            for c_idx, ch in enumerate(row):
                px = cx + c_idx - w // 2
                py = cy + r_idx - h // 2
                if ch == '1':
                    pad.set_dot(px, py, 1)
                elif ch == '0':
                    pad.set_dot(px, py, 0)

    @staticmethod
    def compress_axis(intervals, margin=2, max_gap=8):
        merged = []
        for low, high in sorted(intervals):
            if merged and low <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], high)
            else:
                merged.append([low, high])
        if not merged:
            return lambda value: value
        anchors = []
        target = margin
        previous_high = None
        for low, high in merged:
            if previous_high is not None:
                target += min(max_gap, low-previous_high)
            anchors.append((low, target))
            target += high-low
            anchors.append((high, target))
            previous_high = high
        def transform(value):
            if value <= anchors[0][0]: return value-anchors[0][0]+anchors[0][1]
            for (a, ta), (b, tb) in zip(anchors, anchors[1:]):
                if a <= value <= b and b > a:
                    return ta+(value-a)*(tb-ta)/(b-a)
            return value-anchors[-1][0]+anchors[-1][1]
        return transform

    def spatial_objects(self, objects):
        copied = [dict(o) for o in objects]
        if not copied: return copied
        def dims(o):
            if o.get("type") == "arrow":
                return (5,9) if o.get("direction") in ("left","right") else (9,5)
            return o.get("width",10), o.get("height",8)
        tx = self.compress_axis([(o["x"]-dims(o)[0]//2, o["x"]+(dims(o)[0]-1)//2) for o in copied], max_gap=5)
        ty = self.compress_axis([(o["y"]-dims(o)[1]//2, o["y"]+(dims(o)[1]-1)//2) for o in copied], max_gap=5)
        for o in copied:
            w,h=dims(o)
            o.update(x=round(tx(o["x"])), y=round(ty(o["y"])), hit_width=w, hit_height=h)
        return copied

    def back_arrow(self, object_id, label, action):
        return {
            "id": object_id, "type": "arrow", "x": 6, "y": 35,
            "direction": "left", "size": 2, "hit_width": 11, "hit_height": 9,
            "label": label, "tts": f"{label}.", "action": action
        }

    def get_relative_direction(self, origin, target):
        if origin is None:
            return ""
        dx = float(target["x"]) - float(origin["x"])
        dy = float(target["y"]) - float(origin["y"])
        if abs(dx) > 4 and abs(dy) > 4:
            horizontal = "right" if dx > 0 else "left"
            vertical = "down" if dy > 0 else "up"
            return f"{horizontal} {vertical}"
        if abs(dx) >= abs(dy):
            return "right" if dx > 0 else "left" if dx < 0 else ""
        return "down" if dy > 0 else "up" if dy < 0 else ""

    def draw_triangle(self, x, y, direction, size=2):
        points = {(0,row) for row in range(9)}
        points.update((4-abs(row-4),row) for row in range(9))
        if direction == "left": points={(4-col,row) for col,row in points}
        elif direction == "up": points={(row,4-col) for col,row in points}
        elif direction == "down": points={(row,col) for col,row in points}
        elif direction != "right": raise ValueError("Unknown triangle direction")
        w,h = (5,9) if direction in ("left","right") else (9,5)
        for col,row in points:
            self.dotpad.set_dot(round(x)-w//2+col, round(y)-h//2+row)

    def draw_filled_square(self, x, y, size=4):
        left, top = round(x)-size//2, round(y)-size//2
        for yy in range(top, top+size):
            for xx in range(left, left+size): self.dotpad.set_dot(xx, yy)

    def draw_icon_pattern(self, x, y, rows):
        if not rows:
            return
        width, height = max(map(len, rows)), len(rows)
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                if value == "1":
                    self.dotpad.set_dot(int(x) + column - width // 2, int(y) + row_index - height // 2)

    def point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        nx, ny = x1 + t * dx, y1 + t * dy
        return ((px - nx) ** 2 + (py - ny) ** 2) ** 0.5

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

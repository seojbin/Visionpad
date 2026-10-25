"""Tactile drawing for farm plots, plot details and the care minigame."""
import math


class FarmDrawing:
    def draw_plot(self, obj):
        e = self.engine
        pad = e.dotpad
        cx, cy = round(obj["x"]), round(obj["y"])
        rx, ry = int(obj.get("width", 16)) // 2 - 1, int(obj.get("height", 14)) // 2 - 1
        pad.draw_box(cx, cy, 2 * rx, 2 * ry)

        state = e.farm_plots.get(obj["id"], self.new_plot_state())
        seed_id = state.get("seed_id")

        if not seed_id:
            for dy in (-3, 0, 3):
                for dx in range(-rx + 2, rx - 1, 2):
                    pad.set_dot(cx + dx, cy + dy)
            return

        if state.get("watered"):
            pad.draw_line(cx - rx + 1, cy + ry - 1, cx + rx - 1, cy + ry - 1)
        if state.get("fertilized"):
            pad.set_dot(cx - rx + 2, cy - ry + 2)
            pad.set_dot(cx + rx - 2, cy - ry + 2)

        growth = int(state.get("growth", 0))
        mature = bool(state.get("mature"))

        if mature:
            mature_patterns = {
                "tomato": (
                    "001010100",
                    "011111110",
                    "111101111",
                    "111000111",
                    "111101111",
                    "111111111",
                    "011111110",
                ),
                "carrot": (
                    "101010101",
                    "011111110",
                    "001111100",
                    "011111110",
                    "001111100",
                    "000111000",
                    "000010000",
                ),
                "potato": (
                    "011100110",
                    "111111111",
                    "110111011",
                    "011111110",
                    "111101111",
                    "111111111",
                    "011001110",
                ),
            }
            e.draw_icon_pattern(cx, cy, mature_patterns.get(seed_id, mature_patterns["tomato"]))
            return

        if growth <= 0:
            sprout_patterns = {
                "tomato": ("00100", "01110", "00100"),
                "carrot": ("10101", "01110", "00100"),
                "potato": ("01100", "11110", "00110"),
            }
            e.draw_icon_pattern(cx, cy + 1, sprout_patterns.get(seed_id, ("010", "111", "010")))
        else:
            mid_patterns = {
                "tomato": (
                    "0101010",
                    "1111111",
                    "0011100",
                    "0111110",
                    "0001000",
                ),
                "carrot": (
                    "1010101",
                    "0111110",
                    "0011100",
                    "0011100",
                    "0001000",
                ),
                "potato": (
                    "0011100",
                    "0111110",
                    "1110111",
                    "0111110",
                    "0110110",
                ),
            }
            e.draw_icon_pattern(cx, cy, mid_patterns.get(seed_id, mid_patterns["tomato"]))

    @staticmethod
    def plot_bounds(obj):
        width, height = int(obj.get("width", 10)), int(obj.get("height", 8))
        return round(obj["x"])-width//2, round(obj["y"])-height//2, width, height

    def draw_plot_progress(self, obj, state):
        e = self.engine
        if state["seed_id"] is None: return
        needed = max(1, int(e.get_seed_config(state["seed_id"]).get("growth_days", 3)))
        ratio = 1.0 if state["mature"] else max(0.0, min(1.0, float(state["growth"]) / needed))
        left, top, width, height = self.plot_bounds(obj)
        rows = min(height-2, math.ceil((height-2)*ratio))
        for y in range(top+height-1-rows, top+height-1):
            for x in range(left+1, left+width-1): e.dotpad.set_dot(x, y)

    def draw_watering_can(self, obj):
        e = self.engine
        e.icons.draw(obj)

    def draw_fertilizer(self, obj):
        e = self.engine
        e.icons.draw(obj)

    def draw_seed(self, obj):
        e = self.engine
        e.icons.draw(obj)

    def draw_crop_symbol(self, x, y, seed_id):
        e = self.engine
        patterns = {
            "tomato": ["00100", "01010", "10001", "10001", "01110"],
            "carrot": ["10101", "01110", "01010", "00100", "00100"],
            "potato": ["11000", "10110", "01101", "00101", "00010"]
        }
        rows = patterns.get(seed_id, ["00100", "01110", "00100", "00000", "00000"])
        for j, row in enumerate(rows):
            for i, raised in enumerate(row):
                if raised == "1":
                    e.dotpad.set_dot(x + i - 2, y + j - 2)

    def draw_detail_field(self, obj):
        e = self.engine
        x, y = int(obj["x"]), int(obj["y"])
        width, height = int(obj.get("width", 44)), int(obj.get("height", 18))
        e.dotpad.draw_box(x, y, width, height)
        plot_id = e.detail_plot_id
        state = e.farm_plots.get(plot_id) if plot_id else None
        if not state or state.get("seed_id") is None:
            return
        if state.get("mature"):
            for dx, dy in [(-8, 1), (-4, -2), (0, 2), (5, -1), (9, 2)]:
                for ox, oy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                    e.dotpad.set_dot(x + dx + ox, y + dy + oy)
        else:
            e.dotpad.set_dot(x, y)
            if state.get("watered"):
                e.dotpad.draw_line(x - 8, y + 5, x + 8, y + 5)
            if state.get("fertilized"):
                e.dotpad.set_dot(x - 10, y - 5)
                e.dotpad.set_dot(x + 10, y - 5)

    def draw_detail_gauge(self, obj):
        e = self.engine
        plot_id = e.detail_plot_id
        state = e.farm_plots.get(plot_id) if plot_id else None
        if not state or state.get("seed_id") is None:
            return
        needed = max(1, int(e.get_seed_config(state["seed_id"]).get("growth_days", 3)))
        growth = needed if state.get("mature") else min(needed, int(state.get("growth", 0)))
        x1 = obj["x"] - obj["width"] // 2
        x2 = x1 + obj["width"] - 1
        y1 = obj["y"] - obj["height"] // 2
        y2 = y1 + obj["height"] - 1
        e.dotpad.draw_line(x1, y1, x2, y1)
        e.dotpad.draw_line(x2, y1, x2, y2)
        e.dotpad.draw_line(x2, y2, x1, y2)
        e.dotpad.draw_line(x1, y2, x1, y1)
        inner_width = x2 - x1 - 1
        fill = int(round(inner_width * growth / needed))
        for x in range(x1 + 1, x1 + 1 + fill):
            for y in range(y1 + 1, y2):
                e.dotpad.set_dot(x, y)

    def draw_care_button(self, obj):
        e = self.engine
        e.icons.draw(obj)

    def draw_care_target(self, obj):
        e = self.engine
        x, y = int(obj["x"]), int(obj["y"])
        if obj.get("care_kind") == "water":
            e.dotpad.set_dot(x, y - 1)
            e.dotpad.set_dot(x - 1, y)
            e.dotpad.set_dot(x, y)
            e.dotpad.set_dot(x + 1, y)
            e.dotpad.set_dot(x, y + 1)
        else:
            e.dotpad.set_dot(x - 1, y - 1)
            e.dotpad.set_dot(x + 1, y - 1)
            e.dotpad.set_dot(x - 1, y + 1)
            e.dotpad.set_dot(x + 1, y + 1)

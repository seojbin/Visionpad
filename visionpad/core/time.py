"""Action time, night, sleep and the morning transition; the lower time panel."""
import time


class TimeAndSleep:
    def get_action_cost(self, action_name):
        if action_name == "travel":
            return 0
        defaults = {"plant": 2, "water": 2, "fertilize": 2, "harvest": 3,
                    "research": 3, "cook": 3, "mine": 2}
        configured = self.config.get("time", {}).get("action_costs", {})
        return max(defaults.get(action_name, 0), int(configured.get(action_name, 0)))

    def get_time_cells(self):
        return max(0, min(self.time_total_cells, self.time_used_cells))

    def time_text(self):
        used = self.get_time_cells()
        remaining = max(0, self.time_total_cells - used)
        if self.day_ended:
            return "Night. Select the bed."
        return f"Activity: {remaining} hours left"

    def consume_time(self, action_name):
        cost = max(0, self.get_action_cost(action_name))
        if self.day_ended:
            return {"cost": 0, "night": True}

        multiplier = self.buff_multiplier_for("time_slow")
        if 0 < multiplier < 1:
            remaining = float(self.active_buff["remaining_ticks"])
            covered = min(cost, remaining / multiplier)
            cost = covered * multiplier + (cost - covered)
        self.time_used_cells = min(self.time_total_cells, self.time_used_cells + cost)
        self.tick_buff(cost)

        if self.time_used_cells >= self.time_total_cells:
            self.enter_night()
            return {"cost": cost, "night": True}

        return {"cost": cost, "night": False}

    def enter_night(self):
        self.day_ended = True
        self.current_location = "home"
        self.current_page = "home"
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.leave_activities()
        self.pointer_pressed = False
        self.clear_hover()
        self.render()

    def night_response(self, prefix=None, sound_events=None):
        narration = "Night. Home now. Select the bed."
        if prefix:
            narration = f"{prefix}. {narration}"
        return self.response(tts=narration, sfx="day_end", sound_events=sound_events)

    def next_day(self):
        if self.sleep_until is not None:
            return self.response()
        self.sleep_until = time.monotonic() + self.sleep_blackout_seconds
        self.pointer_pressed = False
        self.leave_activities()
        self.clear_hover()
        self.render()
        return self.response(tts="Sleeping.", sound_events=[{"kind": "one_shot", "sound": "sleep"}])

    def finish_sleep(self):
        notes = self.registry.run("end_of_day")
        self.sleep_until = None

        self.day += 1
        self.registry.run("start_of_day")
        self.time_used_cells = 0
        self.day_ended = False
        self.current_location = "home"
        self.current_page = "home"
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.leave_activities()
        self.clear_hover()
        self.render()

        text = f"Day {self.day}. Morning."
        for note in notes:
            text += f". {note}"
        return self.response(tts=text, sfx="morning")

    def lower_panel_state(self):
        if self.sleep_until is not None:
            return {"mode": "blank", "label": "Sleeping"}
        panel = self.registry.page_hook(self.current_page, "panel")
        page, pages, braille = panel() if panel else (0, 1, None)
        if pages > 1:
            return {"mode": "pages", "page": page + 1, "pages": pages,
                    "label": f"Page {page + 1} of {pages}"}
        if braille:
            return {"mode": "braille", "label": braille}
        return {"mode": "time", "label": "Activity time"}

    def draw_time_bar(self):
        self.timepad.clear()
        panel = self.lower_panel_state()
        if panel["mode"] == "blank":
            return
        if panel["mode"] == "pages":
            start = (panel["page"] - 1) * self.timepad.width // panel["pages"]
            end = panel["page"] * self.timepad.width // panel["pages"]
            for x in range(start, max(start + 1, end)):
                for y in range(self.timepad.height):
                    self.timepad.set_dot(x, y)
            return
        if panel["mode"] == "braille":
            letters = {'s': (2,3,4), 'h': (1,2,5), 'o': (1,3,5),
                       'p': (1,2,3,4), 'b': (1,2), 'u': (1,3,6),
                       'y': (1,3,4,5,6), 'e': (1,5), 'l': (1,2,3)}
            positions = {1:(0,0), 2:(0,1), 3:(0,2), 4:(1,0), 5:(1,1), 6:(1,2)}
            for cell, char in enumerate(panel['label']):
                for dot in letters[char]:
                    x, y = positions[dot]
                    self.timepad.set_dot(cell * 2 + x, y)
            return
        bar = self.config.get("time", {}).get("bar", {})
        cell_width = int(bar.get("cell_width", 2))
        cell_height = int(bar.get("cell_height", 4))
        filled_columns = int(self.get_time_cells() * cell_width)
        for x in range(filled_columns):
            for dy in range(cell_height):
                self.timepad.set_dot(x, dy)

    def night_only_response(self):
        return self.response(tts="Night. Select the bed.", sfx="error")

    def defer_visual_completion(self, kind, visible_until):
        deadline = max(visible_until.values(), default=0)
        if time.monotonic() >= deadline:
            return False
        self.pending_visual_completion = (deadline, kind)
        return True

    def visual_tick(self):
        if self.current_page == "load_game": return self.response()
        if self.sleep_until is not None:
            if time.monotonic() >= self.sleep_until:
                return self.finish_sleep()
            return self.response()
        if not self.paused and self.pending_visual_completion:
            deadline, kind = self.pending_visual_completion
            if time.monotonic() >= deadline:
                self.pending_visual_completion = None
                return self.registry.visual_completions[kind]()
        return self.response()

"""Pointer, key and action dispatch: core checks first, then feature hooks from the registry."""


class InputDispatch:
    def object_contains(self, obj, x, y):
        contains = self.registry.hit_tests.get(obj.get("type"))
        if contains:
            return contains(obj, x, y)
        half_width = obj.get("hit_width", obj.get("width", 8)) / 2
        half_height = obj.get("hit_height", obj.get("height", 8)) / 2
        return abs(x - obj["x"]) <= half_width and abs(y - obj["y"]) <= half_height

    def find_object(self, x, y):
        objects = self.get_objects()
        priority_types = ("care_target", "harvest_crop", "care_button", "growth_gauge", "plot", "seed", "ingredient", "recipe", "shop_item", "research", "node", "plot_detail_field")
        for obj_type in priority_types:
            for obj in objects:
                if obj.get("type") == obj_type and self.object_contains(obj, x, y):
                    return obj
        for obj in objects:
            if obj.get("type") != "route" and self.object_contains(obj, x, y):
                return obj
        for obj in objects:
            if obj.get("type") == "route" and self.object_contains(obj, x, y):
                return obj
        return None

    def get_location_detail(self):
        loc = self.current_page
        detail = self.registry.page_hook(loc, "detail")
        if detail:
            return detail()
        return f"{self.get_page_name(loc)}."

    def get_object_tts(self, obj, detail=False):
        """Short hover: one target's name and its price/quantity only.

        Detailed inspection (Shift/hand gesture) is a separate read-only mode.
        Never derive the brief description by splitting verbose TTS sentences:
        prices, counts and actions may be buried in those sentences.
        """
        kind = obj.get("type")
        label = str(obj.get("label") or "Object").strip()
        if detail:
            return obj.get("tts") or label

        describe = self.registry.tts.get(kind)
        if describe:
            return describe(obj)

        # A map location, transition, building or navigation control has only
        # a name in standard hover, regardless of its verbose TTS.
        if kind == "arrow":
            return label

        count = obj.get("count")
        if count is not None:
            return f"{label}, {count}."
        if obj.get("price") is not None:
            return f"{label}, {obj['price']} gold."
        return label

    def get_hover_sfx(self, obj):
        if obj.get("hover_sfx"):
            return obj["hover_sfx"]
        if obj.get("type") in self.registry.hover_sounds:
            return self.registry.hover_sounds[obj["type"]]
        return "hover_navigation" if obj.get("type") == "arrow" else "hover_object"

    def minigame_input(self, x, y, step):
        """Pointer input on a tracing minigame page. Blocked while paused, at night, asleep or while a
        step finishes; otherwise step(px, py, x, y) gets the previous and the current point."""
        if self.paused or self.day_ended or self.sleep_until is not None or self.pending_visual_completion:
            self.last_pointer=(x,y)
            return self.response()
        px,py=self.last_pointer
        self.last_pointer=(x,y)
        if px is None or py is None: px,py=x,y
        return step(px, py, x, y)

    def minigame_release(self, x, y):
        self.pointer_pressed=False
        return self.response()

    def release_pointer(self):
        """Drop the pointer and any held drag (menus, save, pause, release command)."""
        self.pointer_pressed = False
        self.registry.run("release_drag")
        self.drag_tool = None

    def leave_activities(self):
        self.registry.run("leave_activity")

    def page_pointer(self, kind, x, y):
        """Raw pointer input for a feature-owned page; None lets the core handler continue."""
        handler = self.registry.pointer(self.current_page, kind)
        return handler(x, y) if handler else None

    def pointer_move(self, x, y):
        result = self.page_pointer("move", x, y)
        if result is not None:
            return result
        if self.current_page in ('water_minigame','fertilizer_minigame'):
            return self.move_minigame(x,y)
        if self.sleep_until is not None:
            return self.response()

        self.last_pointer = (x, y)
        if self.paused:
            return self.response()

        is_pointing = False  # Press/click does not double as detailed inspection.
        obj = self.find_object(x, y)

        if obj is None:
            self.hover_object_id = None
            self.last_hover_state = (None, is_pointing)
            if is_pointing and not getattr(self, 'location_detail_spoken', False):
                self.location_detail_spoken = True
                return self.response(tts=self.get_location_detail())
            return self.response()

        object_id = obj["id"]
        current_state = (object_id, is_pointing)

        if current_state != getattr(self, 'last_hover_state', (None, False)):
            self.last_hover_state = current_state
            self.hover_object_id = object_id
            tts_text = self.get_object_tts(obj, detail=is_pointing)
            return self.response(tts=tts_text, sfx=self.get_hover_sfx(obj))

        return self.response()

    def pointer_down(self, x, y):
        result = self.page_pointer("down", x, y)
        if result is not None:
            return result
        if self.sleep_until is not None:
            return self.response()
        if self.pending_visual_completion:
            return self.response()

        self.location_detail_spoken = False
        self.last_hover_state = (None, True)

        single_press = self.registry.page_hook(self.current_page, "single_press")
        if single_press and self.pointer_pressed:
            return self.response()

        self.pointer_pressed = True
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()

        press = self.registry.page_hook(self.current_page, "press")
        if press:
            return press(x, y)

        obj = self.find_object(x, y)
        if obj is None:
            return self.response()
        action = obj.get("action", "")
        return self.perform_action(action, obj)

    def pointer_drag(self, x, y):
        result = self.page_pointer("drag", x, y)
        if result is not None:
            return result
        if self.sleep_until is not None:
            return self.response()
        if self.pending_visual_completion:
            return self.response()

        previous_x, previous_y = self.last_pointer
        self.last_pointer = (x, y)
        if self.paused:
            return self.response()

        if self.drag_tool is None:
            return self.pointer_move(x, y)
        drop = self.registry.drag_tools.get(self.drag_tool)
        return drop(x, y) if drop else self.response()

    def pointer_up(self, x, y):
        result = self.page_pointer("up", x, y)
        if result is not None:
            return result
        if self.sleep_until is not None:
            return self.response()

        self.location_detail_spoken = False
        self.last_hover_state = (None, False)

        if self.paused:
            self.release_pointer()
            return self.response()

        final = self.pointer_drag(x, y) if self.pointer_pressed else None
        self.pointer_pressed = False
        self.last_pointer = (x, y)

        if final and (final.get("sfx") in ("cooking_success", "cooking_step", "cooking_wait", "day_end")):
            final["state"] = self.get_state()
            return final

        self.drag_tool = None
        self.drag_target_ids.clear()
        result = self.response()

        if final:
            result["sound_events"] = final.get("sound_events", []) + result.get("sound_events", [])
        return result

    def perform_action(self, action, obj):
        before = (self.current_page, self.current_location, self.inventory_page, self.shop_page)
        result = self._perform_action(action, obj)
        after = (self.current_page, self.current_location, self.inventory_page, self.shop_page)
        if obj.get("type") == "arrow" and before != after:
            result.setdefault("sound_events", []).append({"kind": "one_shot", "sound": "step", "direction": obj.get("direction")})
        return result

    def _perform_action(self, action, obj):
        owned = self.registry.action_for(action, before_night_guard=True)
        if owned:
            handler, arg = owned
            return handler(arg, obj)
        if action == "close_load": return self.close_load_game()
        if action.startswith("load_slot:"): return self.load_game(action.split(":", 1)[1])
        if self.day_ended and action != "rest":
            return self.night_only_response()
        owned = self.registry.action_for(action, before_night_guard=False)
        if owned:
            handler, arg = owned
            return handler(arg, obj)
        if action.startswith("travel:"):
            return self.travel_to(action.split(":", 1)[1])
        if action == "return_scene":
            return self.return_to_scene()
        if action.startswith("inspect:"):
            return self.response(tts=self.get_object_tts(obj))
        if action == "rest":
            return self.next_day()
        return self.response(tts=self.get_object_tts(obj))

    def travel_to(self, location):
        self.registry.run("before_navigation")
        if self.day_ended:
            return self.night_only_response()
        if location not in ("home", "farm", "town", "mine", "fishing", "pasture"):
            return self.response(tts="Location unavailable.")
        self._menu_stack.clear()
        self.registry.run("close_dialogue")
        changed = location != self.current_location
        self.current_location = location
        self.current_page = location
        self.seed_select_plot_id = None
        self.leave_activities()
        self.clear_hover()
        if changed:
            result = self.consume_time("travel")
            if result["night"]:
                return self.night_response()
        self.render()
        name = self.get_page_name(location)
        arrival = self.registry.page_hook(location, "arrival")
        text = arrival() if arrival else None
        if text:
            return self.response(tts=text, sfx="travel")
        return self.response(tts=f"{name}", sfx="travel")

    def navigate_key(self, direction):
        if self.current_page == 'load_game':
            if self.paused: return self.response(tts='Resume first.')
            if self.sleep_until is not None: return self.response(tts='Sleeping. Please wait.')
            return self.close_load_game()
        navigate = self.registry.page_hook(self.current_page, "navigate")
        if navigate:
            result = navigate(direction)
            if result is not None:
                return result
        return super().navigate_key(direction)

    def return_to_scene(self):
        self.registry.run("before_navigation")
        self.pointer_pressed = False
        self.current_page = "home" if self.day_ended else self.current_location
        self.seed_select_plot_id = None
        self.drag_tool = None
        self.drag_target_ids.clear()
        self.leave_activities()
        self.clear_hover()
        self.render()
        return self.response(tts=f"{self.get_page_name(self.current_location)}.", sfx="open_page")

    def handle_command(self, command):
        command = str(command).lower().strip()
        command = {"f1":"minimap", "f2":"resources", "f3":"load", "f3_long":"save",
                   "f4":"click", "arrowleft":"left", "arrowright":"right"}.get(command, command)
        if command == "save":
            return self.save_game()
        if command == "load": return self.toggle_menu("load_game")
        if command == "minimap": return self.toggle_menu("minimap")
        if command == "resources": return self.toggle_menu("inventory")
        if command in ("left", "right"): return self.navigate_key(command)
        if command == "release":
            self.release_pointer()
            return self.response()
        if command in ("click", "pause"):
            x, y = self.last_pointer
            if x is None or y is None:
                return self.response(tts="Move to an item first.")
            result = self.pointer_down(x, y)
            self.pointer_pressed = False
            result["state"] = self.get_state()
            return result
        return self.response()

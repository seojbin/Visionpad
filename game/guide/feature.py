"""Guide: a replayable tutorial reached from the F1 map. Topic buttons explain touch, selection,
sweeping, keys and the screen layout; the symbol key shows every shared tactile symbol with its name.

Why (README.md, "Tactile design rules" and "Learning support"): a map scene needs more learning than a
row of buttons, so the game offers a key (legend) for its symbols and a tutorial the player can open
at any time and repeat without consequences. Nothing here spends time, items or gold.

Engine attributes (save format): none. The symbol-key page number is part of the page id
(guide_symbols_1 to guide_symbols_4), so the guide adds nothing to saves.
Declares no slot; contributes the "Guide" button to the minimap's minimap.objects slot.
"""
from engine.core.registry import Feature
from engine.display.icons import SYMBOLS

# (id, label, short hover text, full text read on selection)
TOPICS = (
    ("touch", "Touch and listen",
     "Touch and listen.",
     "Touch and listen. Move your finger or the pointer slowly over the pad. When you reach an object you "
     "hear its name. Objects are raised outlines with a gap around them, so follow the outline to feel its "
     "shape. Hold Shift to hear a longer description without doing anything."),
    ("select", "Select",
     "Select.",
     "Select. While you hear an object, click, or press Enter, Space or F4 to use it. Only things that "
     "speak can be selected. Selecting a place on the map takes you there."),
    ("sweep", "Sweep tasks",
     "Sweep tasks.",
     "Sweep tasks. Watering, fertilizing, harvesting, cooking and shearing are done by moving over the "
     "raised targets. Each target you pass disappears. You do not need to hold a click, and there is no "
     "time limit."),
    ("keys", "Keys",
     "Keys.",
     "Keys. F1 opens the map, F2 the inventory, and pressing the same key again returns. A short press of "
     "F3 opens the save list; hold F3 to save. The left and right arrows travel between places, go back, "
     "or turn a page."),
    ("layout", "Screen layout",
     "Screen layout.",
     "Screen layout. The top row holds up to four framed buttons. Under the double line is a map of the "
     "place with the same things drawn as outlines. Small solid triangles at the edges are exits to "
     "other places. In the village, the roads have two edge lines; follow them to the exits."),
    ("symbols", "Symbol key",
     "Symbol key. Select to feel every symbol.",
     None),
)

# Symbol key: (symbol, name, description). Shapes come from engine/display/icons.py SYMBOLS.
SYMBOL_KEY = (
    ("seed", "Seed", "a small plus. Seeds."),
    ("crop", "Crop", "a sprout on a stem. Crops and harvesting."),
    ("fish", "Fish", "a fish outline with a tail on the right. Fish."),
    ("mineral", "Mineral", "a diamond outline. Stone, copper, iron and diamonds."),
    ("tool", "Tool", "a hammer: a bar on a handle. Pickaxe, rod, fertilizer and other tools."),
    ("water", "Water", "a drop outline. Watering."),
    ("coin", "Gold", "a ring with a dot in the middle. Gold and selling."),
    ("bag", "Shop bag", "a box with two handles. The shop and buying."),
    ("person", "Person", "a small head above shoulders. Rowan and other people."),
    ("bed", "Bed", "a headboard and a mattress. Sleep."),
    ("pot", "Pot", "a pot with a lid and a knob on top. The kitchen and cooking."),
    ("page", "Page", "a page with a folded corner. Research, the calendar, saves and this guide."),
    ("arrow_up", "Arrow", "a small solid triangle. It points to where it leads: up, down, left or right."),
    ("check", "Check", "a tick. Selected or done."),
    ("food", "Food", "two nested frames with nothing inside. Food you can eat from the inventory."),
    ("material", "Item", "an empty frame. Other items; listen for the name."),
    ("animal_cat", "Cat", "two pointed ears and a raised tail. Select to feel the large drawing."),
    ("animal_dog", "Dog", "a long snout and a floppy ear. Select to feel the large drawing."),
    ("animal_chicken", "Chicken", "a comb on the head and a beak. Select to feel the large drawing."),
    ("animal_sheep", "Sheep", "a round woolly body. Select to feel the large drawing."),
)
# Large drawings in the animal gallery: what to feel for, read when the drawing opens.
ANIMALS = (
    ("cat", "Cat", "Cat, side view facing right. Two tall pointed ears on a round head, slim legs, and a "
                   "long tail curling up behind. The body has a dotted fur texture you can stroke."),
    ("dog", "Dog", "Dog, side view facing right. A long snout, one floppy ear hanging below the head, "
                   "thick legs and a short raised tail. The body has a dotted fur texture."),
    ("chicken", "Chicken", "Chicken, side view. A comb on top of the head, a pointed beak, a round body "
                           "with wing lines, and two thin legs."),
    ("sheep", "Sheep", "Sheep with grown wool, side view. A big round filled body, a small head and four "
                       "short legs. In the pasture, a shorn sheep shows a dotted texture instead."),
)
# Four symbols per page, one theme per page, so a page never shows more than five different symbols
# (BANA 2010 §3.2.2) and each theme is learned on its own.
PER_PAGE = 4
PAGE_TITLES = ("Things you grow and find", "Tools and trade", "Places and people", "Signs", "Animals")


class Guide(Feature):
    name = "guide"

    def register(self, reg):
        reg.page("guide", name="Guide", objects=self.topic_objects, icon_grid=True, navigate=self.navigate,
                 detail=lambda: "Guide. Six topics. Select one to hear it. Left goes back.")
        for index in range(self.page_count()):
            reg.page(self.page_id(index), name="Symbol key", objects=lambda i=index: self.symbol_objects(i),
                     icon_grid=True, navigate=lambda direction, i=index: self.navigate_symbols(i, direction),
                     panel=lambda i=index: (i, self.page_count(), None),
                     detail=lambda: "Symbol key. Touch a symbol to hear its name and shape.")
        for index, (species, label, _) in enumerate(ANIMALS):
            reg.page(f"guide_animal_{species}", name=label, objects=lambda i=index: self.animal_objects(i),
                     scene=lambda i=index: self.draw_animal(i),
                     navigate=lambda direction, i=index: self.navigate_animals(i, direction),
                     detail=lambda text=ANIMALS[index][2]: text)
        reg.action("guide_animal:", lambda arg, obj: self.open_animal(arg), before_night_guard=True)
        reg.action("guide_animal_next", lambda arg, obj: self.next_animal(), before_night_guard=True)
        reg.action("guide_page_animals", lambda arg, obj: self.navigate_animals(0, "left"), before_night_guard=True)
        reg.object_tts("guide_animal", lambda obj: obj.get("tts", ""))
        reg.action("guide_open", lambda arg, obj: self.open(), before_night_guard=True)
        reg.action("guide_topic:", lambda arg, obj: self.topic(arg), before_night_guard=True)
        reg.action("guide_symbols", lambda arg, obj: self.open_symbols(), before_night_guard=True)
        reg.action("guide_symbol:", lambda arg, obj: self.symbol(arg), before_night_guard=True)
        reg.action("guide_page:", lambda arg, obj: self.turn_page(int(arg)), before_night_guard=True)
        reg.icon("guide_button", symbol=lambda obj: "page")
        reg.icon("guide_topic", symbol=lambda obj: "check" if obj.get("topic") == "symbols" else "material")
        reg.icon("guide_symbol", pattern=self.symbol_rows,
                 symbol=lambda obj: "food" if obj.get("symbol") == "food" else obj.get("symbol"))
        reg.object_tts("guide_button", lambda obj: obj.get("tts", "Guide."))
        reg.object_tts("guide_topic", lambda obj: obj.get("tts", ""))
        reg.object_tts("guide_symbol", lambda obj: obj.get("tts", ""))
        reg.hover_sfx("guide_button", "hover_resource")
        reg.hover_sfx("guide_topic", "hover_resource")
        reg.hover_sfx("guide_symbol", "hover_resource")
        reg.contribute("minimap.objects", self.map_button)

    @staticmethod
    def page_id(index):
        return f"guide_symbols_{index + 1}"

    def page_index(self):
        """Index of the symbol-key page on screen, or None."""
        ids = [self.page_id(i) for i in range(self.page_count())]
        page = self.engine.current_page
        return ids.index(page) if page in ids else None

    # ---- objects ----

    @staticmethod
    def map_button():
        """The Guide button in the free top-left corner of the F1 map."""
        return [dict(id="map_guide", type="guide_button", x=8, y=6, width=12, height=10, hit_width=10,
                     hit_height=8, label="Guide", tts="Guide. Learn the symbols and controls.",
                     action="guide_open")]

    def topic_objects(self):
        e = self.engine
        objects = []
        for topic_id, label, short, _ in TOPICS:
            action = "guide_symbols" if topic_id == "symbols" else f"guide_topic:{topic_id}"
            objects.append(dict(id=f"guide_{topic_id}", type="guide_topic", topic=topic_id,
                                label=label, tts=short, action=action))
        objects.append(e.back_arrow("guide_back", "Back", "return_scene"))
        return objects

    @staticmethod
    def page_count():
        return (len(SYMBOL_KEY) + PER_PAGE - 1) // PER_PAGE

    def symbol_objects(self, page):
        e = self.engine
        objects = []
        for symbol, name, description in SYMBOL_KEY[page * PER_PAGE:(page + 1) * PER_PAGE]:
            objects.append(dict(id=f"guide_symbol_{symbol}", type="guide_symbol", symbol=symbol,
                                label=name, tts=f"{name}.", description=description,
                                action=f"guide_symbol:{symbol}"))
        if page > 0:
            objects.append(dict(id="guide_page_left", type="arrow", direction="left", x=9, y=35,
                                label="Previous page", tts="Previous page", action="guide_page:-1"))
        else:
            objects.append(e.back_arrow("guide_symbols_back", "Back to guide", "guide_open"))
        if page < self.page_count() - 1:
            objects.append(dict(id="guide_page_right", type="arrow", direction="right", x=51, y=35,
                                label="Next page", tts="Next page", action="guide_page:1"))
        return objects

    @staticmethod
    def symbol_rows(obj):
        symbol = obj.get("symbol") or ""
        if symbol.startswith("animal_"):
            return tuple(Guide.animal_icon(symbol[len("animal_"):]))
        return tuple(SYMBOLS.get(symbol) or ())

    @staticmethod
    def animal_icon(species):
        if species in ("cat", "dog"):
            from game.pets.patterns import ICON_PATTERNS
        else:
            from game.pasture.feature import ICON_PATTERNS
        return ICON_PATTERNS[species]

    @staticmethod
    def animal_drawing(species):
        """The same large drawing the pet or pasture page shows (solid limbs, textured body)."""
        from engine.display.tactile import close_gaps, fur_rows
        if species in ("cat", "dog"):
            from game.pets.shapes import drawing
            return drawing(species, "standing")
        from game.pasture.feature import DETAIL_PATTERNS
        return DETAIL_PATTERNS[species] if species == "sheep" else fur_rows(close_gaps(DETAIL_PATTERNS[species]))

    def animal_objects(self, index):
        e = self.engine
        species, label, text = ANIMALS[index]
        rows = self.animal_drawing(species)
        objects = [dict(id=f"guide_animal_body_{species}", type="guide_animal", skip_grid=True, x=30, y=22,
                        width=len(rows[0]), height=len(rows), hit_width=len(rows[0]), hit_height=len(rows),
                        label=label, tts=f"{label}.", action=f"guide_animal:{species}",
                        filled_by_design=species == "sheep")]
        objects.append(e.back_arrow("guide_animal_back", "Back to the symbol key", "guide_page_animals"))
        if index < len(ANIMALS) - 1:
            objects.append(dict(id="guide_animal_next", type="arrow", direction="right", x=51, y=35,
                                label="Next animal", tts="Next animal", action="guide_animal_next"))
        return objects

    def draw_animal(self, index):
        self.engine.draw_icon_pattern(30, 22, self.animal_drawing(ANIMALS[index][0]))

    # ---- actions ----

    def show(self, page, tts):
        e = self.engine
        e._menu_stack.clear()
        e.release_pointer()
        e.leave_activities()
        e.set_page(page)
        e.clear_hover()
        e.render()
        return e.response(tts=tts, sfx="open_page")

    def open(self):
        e = self.engine
        if e.sleep_until is not None:
            return e.response(tts="Sleeping. Please wait.")
        return self.show("guide", "Guide. Six topics in the top rows. Touch one to hear it, select it to "
                                  "learn more. The last one is the symbol key. Press left to go back.")

    def topic(self, topic_id):
        text = next((full for tid, _, _, full in TOPICS if tid == topic_id and full), None)
        if text is None:
            return self.engine.response()
        return self.engine.response(tts=text)

    def open_symbols(self):
        return self.show(self.page_id(0), f"Symbol key, page 1 of {self.page_count()}: {PAGE_TITLES[0]}. "
                                          "Touch each symbol to hear its name, select it to hear its shape "
                                          "and meaning. Right turns the page.")

    def open_animal(self, species):
        entry = next((a for a in ANIMALS if a[0] == species), None)
        if entry is None:
            return self.engine.response()
        if self.engine.current_page == f"guide_animal_{species}":
            return self.engine.response(tts=entry[2])
        return self.show(f"guide_animal_{species}", entry[2] + " Left goes back, right shows the next animal.")

    def next_animal(self):
        page = self.engine.current_page
        index = next((i for i, a in enumerate(ANIMALS) if page == f"guide_animal_{a[0]}"), None)
        return self.navigate_animals(index, "right") if index is not None else self.engine.response()

    def navigate_animals(self, index, direction):
        if direction == "right" and index < len(ANIMALS) - 1:
            return self.open_animal(ANIMALS[index + 1][0])
        if direction == "left" and index > 0:
            return self.open_animal(ANIMALS[index - 1][0])
        return self.show(self.page_id(self.page_count() - 1), f"Symbol key, page {self.page_count()} of "
                                                              f"{self.page_count()}. Animals.")

    def symbol(self, symbol):
        if symbol.startswith("animal_"):
            return self.open_animal(symbol[len("animal_"):])
        entry = next((s for s in SYMBOL_KEY if s[0] == symbol), None)
        if entry is None:
            return self.engine.response()
        return self.engine.response(tts=f"{entry[1]}: {entry[2]}")

    def turn_page(self, delta):
        e = self.engine
        current = self.page_index()
        if current is None:
            return e.response()
        page = max(0, min(current + delta, self.page_count() - 1))
        e.set_page(self.page_id(page))
        e.clear_hover()
        e.render()
        title = PAGE_TITLES[page] if page < len(PAGE_TITLES) else ""
        return e.response(tts=f"Page {page + 1} of {self.page_count()}. {title}.", sfx="open_page")

    # ---- keys ----

    def navigate(self, direction):
        """Either arrow leaves the guide for the current region."""
        e = self.engine
        e._menu_stack.clear()
        return e.return_to_scene()

    def navigate_symbols(self, index, direction):
        """Arrows turn pages; past the first page Left returns to the topics, past the last Right does too."""
        delta = -1 if direction == "left" else 1
        if 0 <= index + delta < self.page_count():
            return self.turn_page(delta)
        return self.open()

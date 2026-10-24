"""Home: the bed, research chest and kitchen, the home scene, and the roads to the farm and village.

Owns no engine attributes. Declares the home slots other features fill (flowers adds its pot).
Uses engine.can_craft_recipe() (cooking) for the kitchen's recipe count. Resting ("rest") is core
time/sleep.
"""
from visionpad.core.registry import Feature


class Home(Feature):
    name = "home"

    def register(self, reg):
        reg.slot("home.objects", "Extra tactile objects on the home page (daytime only). Provider returns a list of objects.")
        reg.slot("home.scene_objects", "Home scene hitboxes, inserted after the kitchen and before the roads (daytime only).")
        reg.slot("home.scene", "Drawing on the home scene after the furniture (daytime only). Provider draws, returns None.")
        reg.page("home", objects=self.page_objects, scene=self.draw_scene, icon_grid=True,
                 detail=lambda: "Home. Bed, Research, Kitchen, and Flower pot.")
        reg.icon("bed", layout_order=0)
        reg.icon("chest", layout_order=1)
        reg.icon("stove", layout_order=2)
        reg.hover_sfx("bed", "hover_bed")
        reg.hover_sfx("chest", "hover_chest")
        reg.hover_sfx("stove", "hover_stove")
        reg.object_tts("home_hitbox", lambda obj: str(obj.get("label") or "Object").strip())

    def page_objects(self):
        e = self.engine
        objects = []
        for obj in e.config.get("home", {}).get("objects", []):
            copied = dict(obj)
            if e.day_ended and copied.get("id") != "home_bed":
                continue
            if e.day_ended and copied.get("id") == "home_bed":
                copied["tts"] = "Bed. Sleep until morning."
            if copied.get("id") == "home_stove" and not e.day_ended:
                craftable = sum(
                    1 for rid in e.config.get("recipes", {})
                    if e.can_craft_recipe(rid)
                )
                copied["tts"] = f"Kitchen. Available recipes: {craftable}."
            objects.append(copied)

        if not e.day_ended:
            objects.extend(e.registry.collect("home.objects"))
        return objects + self.scene_objects()

    def scene_objects(self):
        e = self.engine
        bed_item = dict(id='home_scene_bed', type='home_hitbox', skip_grid=True,
                        x=13, y=19, width=9, height=9, hit_width=11, hit_height=10,
                        label='Bed', tts='Bed. Sleep until morning.', action='rest')
        if e.day_ended:
            return [bed_item]
        craftable = sum(1 for rid in e.config.get("recipes", {}) if e.can_craft_recipe(rid))
        return [
            bed_item,
            dict(id='home_scene_chest', type='home_hitbox', skip_grid=True,
                 x=30, y=19, width=11, height=8, hit_width=12, hit_height=9,
                 label='Research', tts='Research. Choose an upgrade.', action='open_research'),
            dict(id='home_scene_stove', type='home_hitbox', skip_grid=True,
                 x=46, y=19, width=11, height=8, hit_width=12, hit_height=9,
                 label='Kitchen', tts=f'Kitchen. Available recipes: {craftable}.', action='open_recipes'),
            *e.registry.collect("home.scene_objects"),
            dict(id='home_road_farm', type='home_hitbox', skip_grid=True,
                 x=2, y=26, width=5, height=7, hit_width=7, hit_height=9,
                 label='Farm', tts='Farm. Go west.', action='travel:farm'),
            dict(id='home_road_town', type='home_hitbox', skip_grid=True,
                 x=57, y=26, width=5, height=7, hit_width=7, hit_height=9,
                 label='Village', tts='Village. Go east.', action='travel:town'),
        ]

    def draw_scene(self):
        e = self.engine
        pad = e.dotpad
        pad.draw_line(0, 12, pad.width - 1, 12)
        pad.draw_line(0, 13, pad.width - 1, 13)

        pad.draw_line(4, 39, 55, 39)
        for y in range(13, 40):
            if not (24 <= y <= 28):
                pad.set_dot(4, y)
                pad.set_dot(55, y)
        for dx in (3, 4, 5):
            pad.set_dot(dx, 23)
            pad.set_dot(dx, 29)
        for dx in (54, 55, 56):
            pad.set_dot(dx, 23)
            pad.set_dot(dx, 29)

        e.draw_icon_pattern(1, 26, (
            '001',
            '011',
            '111',
            '011',
            '001',
        ))
        e.draw_icon_pattern(58, 26, (
            '100',
            '110',
            '111',
            '110',
            '100',
        ))

        draw_solid_pattern = e.draw_solid_pattern

        draw_solid_pattern(13, 19, (
            '111111111',
            '110000011',
            '110111011',
            '111111111',
            '100000001',
            '111111111',
            '110111011',
            '111111111',
            '111111111',
        ))

        if e.day_ended:
            return

        draw_solid_pattern(30, 19, (
            '..1111111..',
            '11111011111',
            '11001010011',
            '11111111111',
            '10000000001',
            '11111111111',
            '11001110011',
            '11111111111',
        ))

        draw_solid_pattern(46, 19, (
            '....11111..',
            '...1110111.',
            '11111111111',
            '10001101011',
            '11111111111',
            '11011100011',
            '11011100011',
            '11111111111',
        ))
        e.registry.draw_slot("home.scene")

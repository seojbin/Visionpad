"""Render the main pages and check them against the tactile design rules (engine/display/tactile.py).

    python engine/tools/tactile_audit.py            # list problems per page
    python engine/tools/tactile_audit.py --show     # also print every page as dots (# raised, . lowered)
    python engine/tools/tactile_audit.py --png DIR  # also save every page as a picture, with and without object boxes

Uses a temporary save folder; never touches real saves. The shared test
engine/tests/python/display/test_tactile_rules.py runs the same scenarios.
"""
import argparse
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.config import load_config
from engine.core.engine import GameEngine
from engine.display import tactile

# Objects that must stand alone: every selectable shape on a map scene and every framed icon.
ISOLATED_TYPES = frozenset((
    "home_hitbox", "town_hitbox", "shop_hitbox", "animal_hitbox", "node", "plot", "farm_hitbox", "pasture_exit",
    "guide_animal",
))
# Pages whose task is to raise or clear a field of targets (minigames) may show solid areas.
# The mine keeps its filled rocks with damage patterns (owner decision: the filled rock and its cracks
# read better than an outline there).
SOLID_PAGES = frozenset(("mine", "water_minigame", "fertilizer_minigame", "harvest", "cooking", "shearing", "egg_collect"))


class PageMissing(Exception):
    """The scenario's page is not registered in this checkout."""


def _owned_animals(e):
    pets = e.registry.features["pets"]
    pets.adopt("cat")
    pets.adopt("dog")
    for kind in ("chicken", "sheep"):
        e.pasture_animals[kind]["owned"] = True


def scenarios():
    """(name, setup(engine)) pairs; each setup leaves the engine on the page to check."""
    def page(name, before=None):
        def setup(e):
            if name not in e.registry.pages and name != "load_game":
                raise PageMissing(name)
            if before:
                before(e)
            e.set_page(name)
            if name in ("home", "town", "farm", "mine", "fishing", "pasture"):
                e.current_location = name
        return setup

    def night(e):
        e.day_ended = True
        e.current_location = "home"
        e.set_page("home")

    def planted(e):
        e.farm_plots["plot_1"].update(seed_id="tomato", growth=2, watered=True)

    def pet_detail(e):
        _owned_animals(e)
        e.pet_selected = e.pets[0]["id"]
        e.set_page("pet_detail")

    def animal_detail(e):
        _owned_animals(e)
        e.pasture_selected = "sheep"
        e.set_page("animal_detail")

    def stocked(e):
        r = e.resources
        r["coin"] = 500
        r["fertilizer"] = 3
        for group in ("seeds", "crops", "foods"):
            for key in list(r[group])[:4]:
                r[group][key] = 2
        for mineral in ("stone", "copper", "iron", "diamond"):
            r[mineral] = 2
        r["pickaxe"] = 1

    def inventory_page(index):
        def setup(e):
            stocked(e)
            e.set_page("inventory")
            for _ in range(index):
                e.perform_action("inventory_page:1", {})
        return setup

    def plot(e):
        planted(e)
        e.current_location = "farm"
        e.perform_action("open_plot_detail:plot_1", {})

    def symbol_page(index):
        def setup(e):
            page_id = f"guide_symbols_{index + 1}"
            if page_id not in e.registry.pages:
                raise PageMissing(page_id)
            e.set_page(page_id)
        return setup

    def flower(stage, page_name):
        def setup(e):
            if "flower_detail" not in e.registry.pages:
                raise PageMissing("flower_detail")
            e.houseplant.update(species=e.houseplant.get("species") or "sunflower", stage=stage)
            e.set_page(page_name)
            e.current_location = "home"
        return setup

    def via(page_name, *steps):
        """Reach a page the way the game does (a sequence of actions); skip it if the game refuses."""
        def setup(e):
            if page_name not in e.registry.pages:
                raise PageMissing(page_name)
            for step in steps:
                if callable(step):
                    step(e)
                else:
                    e.perform_action(step, {})
            if e.current_page != page_name:
                raise PageMissing(page_name)
        return setup

    def at(location):
        def setup(e):
            e.current_location = location
            e.set_page(location)
        return setup

    def mature(e):
        e.farm_plots["plot_1"].update(seed_id="tomato", growth=9, watered=True, mature=True)

    def watered(e):
        planted(e)
        e.resources["fertilizer"] = 3

    def ready(kind):
        def setup(e):
            _owned_animals(e)
            e.pasture_animals[kind]["ready"] = True
            e.pasture_selected = kind
            e.current_location = "pasture"
            e.set_page("animal_detail")
        return setup

    def cooking_ready(e):
        e.current_location = "home"
        e.set_page("home")
        recipes = e.config.get("recipes", {})
        cooking = e.registry.features["cooking"]
        for rid, cfg in recipes.items():
            if cfg.get("quest_only") or cfg.get("seafood") or cfg.get("hidden_recipe") or len(cfg.get("ingredients", {})) < 2:
                continue
            for seed_id, needed in cfg["ingredients"].items():
                e.resources.setdefault("crops", {})[seed_id] = int(needed) + 1
            if cooking.can_craft(rid):
                e.perform_action("open_recipes", {})
                e.perform_action(f"select_recipe:{rid}", {})
                for seed_id in cfg["ingredients"]:
                    e.perform_action(f"toggle_ingredient:{seed_id}", {})
                e.perform_action("start_cooking", {})
                return

    def home_with_pet(e):
        _owned_animals(e)
        e.set_page("home")

    return [
        ("home", page("home")),
        ("home with a pet", home_with_pet),
        ("home at night", night),
        ("village", page("town")),
        ("farm", page("farm", planted)),
        ("map", page("minimap")),
        ("map from the village", lambda e: (setattr(e, "current_location", "town"), e.set_page("minimap"))),
        ("mine", page("mine")),
        ("fishing lake", page("fishing")),
        ("shop", page("shop_choice")),
        ("shop: buy", page("shop_buy")),
        ("shop: sell", page("shop_sell")),
        ("shop: tools", page("shop_tools")),
        ("inventory", page("inventory")),
        *[(f"inventory page {i + 1} (stocked)", inventory_page(i)) for i in range(2)],
        ("plot detail", plot),
        ("shop: buy (stocked)", page("shop_buy", stocked)),
        ("shop: sell (stocked)", page("shop_sell", stocked)),
        ("research", page("research")),
        ("recipes", page("recipe_select")),
        ("pets", page("pets", _owned_animals)),
        ("pet detail", pet_detail),
        ("pasture", page("pasture", _owned_animals)),
        ("animal detail", animal_detail),
        *[(f"flower pot ({stage})", flower(stage, "flower_detail")) for stage in ("sprout", "stem", "flower", "withered")],
        ("home with a flower", flower("flower", "home")),
        ("water minigame", via("water_minigame", lambda e: (planted(e), e.farm_plots["plot_1"].update(watered=False)),
                               at("farm"), "start_care:water:plot_1")),
        ("fertilizer minigame", via("fertilizer_minigame", watered, at("farm"), "start_care:fertilizer:plot_1")),
        ("harvest", via("harvest", mature, at("farm"), "start_harvest:plot_1")),
        ("cooking", via("cooking", cooking_ready)),
        ("egg collecting", via("egg_collect", ready("chicken"), "animal:gather")),
        ("shearing", via("shearing", ready("sheep"), "animal:shear")),
        ("Rowan", via("rowan_dialogue", at("town"), "talk_rowan")),
        ("guide", page("guide")),
        *[(f"guide: symbols page {i + 1}", symbol_page(i)) for i in range(5)],
        *[(f"guide: animal {k}", page(f"guide_animal_{k}")) for k in ("cat", "dog", "chicken", "sheep")],
    ]


def every_page_scenarios(covered):
    """Every registered page not already in scenarios(), opened with owned animals and stocked items,
    so a page added later is checked too."""
    with tempfile.TemporaryDirectory() as tmp:
        pages = sorted(GameEngine(load_config("game"), save_dir=tmp).registry.pages)

    def opener(name):
        def setup(e):
            _owned_animals(e)
            e.set_page(name)
        return setup
    return [(f"page {name}", opener(name)) for name in pages if name not in covered]


def all_scenarios():
    named = scenarios()
    covered = set()
    with tempfile.TemporaryDirectory() as tmp:
        for _, setup in named:
            e = GameEngine(load_config("game"), save_dir=tmp)
            try:
                setup(e)
            except PageMissing:
                continue
            covered.add(e.current_page)
    return named + every_page_scenarios(covered)


def icon_symbols(e, objects):
    """Distinct symbol drawings among the framed icons on the page (the frame alone does not count)."""
    found = set()
    for obj in objects:
        if obj.get("type") not in e.icons.types:
            continue
        skip = e.registry.icon_skips.get(obj.get("type"))
        if skip and skip(obj):
            continue
        spec = e.icons.spec(obj)
        if spec.frame == "double_rectangle":
            found.add(("double frame",))
            continue
        rows = tuple(spec.pattern or e.icons.PATTERNS.get(spec.symbol, ()))
        if rows:
            found.add(rows)
    return found


def check(e):
    with tactile.SymbolTrace(e) as trace:
        e.render()
    objects = e.get_objects()
    allow_solid = e.current_page in SOLID_PAGES
    problems = tactile.audit(e.dotpad.to_list(), objects, ISOLATED_TYPES | ICON_TYPES(e),
                             allow_solid=allow_solid, fill_types=ISOLATED_TYPES)
    problems.extend(trace.contacts(e.dotpad.to_list()))
    symbols = icon_symbols(e, objects)
    if len(symbols) > tactile.MAX_SYMBOLS_PER_PAGE:
        problems.append(f"{len(symbols)} different icon symbols on one page (at most {tactile.MAX_SYMBOLS_PER_PAGE})")
    return problems


def ICON_TYPES(e):
    """Framed icons must stand alone too (their frame plus one lowered pin)."""
    return frozenset(e.icons.types)


def write_png(path, matrix, cell=12, boxes=()):
    """Save a page as a picture of the pins (raised: large light dot; lowered: small dark dot), using
    only the standard library. `boxes` are object boxes (left, top, right, bottom) outlined in blue,
    so a reviewer can see where each selectable area is."""
    import struct
    import zlib

    height, width = len(matrix), len(matrix[0]) if matrix else 0
    w, h = width * cell, height * cell
    background, raised, lowered, box_colour = (44, 48, 44), (240, 236, 222), (90, 96, 90), (80, 150, 230)
    pixels = [[background] * w for _ in range(h)]
    r_big, r_small, c = cell * 0.36, cell * 0.09, (cell - 1) / 2
    for y in range(height):
        for x in range(width):
            radius, colour = (r_big, raised) if matrix[y][x] else (r_small, lowered)
            for py in range(cell):
                for px in range(cell):
                    if (px - c) ** 2 + (py - c) ** 2 <= radius ** 2:
                        pixels[y * cell + py][x * cell + px] = colour
    for left, top, right, bottom in boxes:
        x1, y1 = max(0, left * cell), max(0, top * cell)
        x2, y2 = min(w - 1, (right + 1) * cell - 1), min(h - 1, (bottom + 1) * cell - 1)
        for px in range(x1, x2 + 1):
            pixels[y1][px] = pixels[y2][px] = box_colour
        for py in range(y1, y2 + 1):
            pixels[py][x1] = pixels[py][x2] = box_colour
    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in pixels)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def run(show=False, out=print, png_dir=None):
    total = 0
    if png_dir:
        Path(png_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for number, (name, setup) in enumerate(all_scenarios(), 1):
            e = GameEngine(load_config("game"), save_dir=tmp)
            try:
                setup(e)
            except PageMissing:
                continue  # page not registered in this checkout
            problems = check(e)
            total += len(problems)
            out(f"{name} ({e.current_page}): {'ok' if not problems else f'{len(problems)} problem(s)'}")
            for problem in problems:
                out(f"    - {problem}")
            if show:
                for row in e.dotpad.to_list():
                    out("    " + "".join("#" if v else "." for v in row))
            if png_dir:
                slug = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
                boxes = [tactile.object_box(o) for o in e.get_objects()
                         if o.get("x") is not None and not o.get("skip_grid_box")]
                write_png(Path(png_dir) / f"{number:02d}_{slug}.png", e.dotpad.to_list())
                write_png(Path(png_dir) / f"{number:02d}_{slug}_boxes.png", e.dotpad.to_list(), boxes=boxes)
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--show", action="store_true", help="print each page as dots")
    parser.add_argument("--png", metavar="DIR", help="also save each page as a picture of the pins (for a visual dot review)")
    args = parser.parse_args()
    total = run(args.show, png_dir=args.png)
    print(f"{total} problem(s).")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())

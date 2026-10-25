# game

One folder per feature. A task for feature X edits only `game/X/` (see `AGENTS.md`). Shared code is in `engine/`.

| Feature | What it is |
|---|---|
| `home` | Home page: bed, research chest, kitchen, roads to farm and village |
| `farming` | Plots, planting, watering and fertilizing (care minigame), overnight growth |
| `harvest` | Harvest minigame, yield and seed recovery |
| `cooking` | Recipes, ingredients, traced cooking minigame, eating food |
| `seafood` | Fish as ingredients, graded fish dishes and their effects |
| `fishing` | The lake: sound-guided casting, rod wear, fish prices |
| `mining` | Daily rocks, pickaxe wear, mineral loot and prices |
| `research` | Upgrades bought at home |
| `shop` | Counter, buy and sell pages, payment |
| `village` | Town square, Rowan's tutorial quest, weekly market |
| `npc` | Rowan's voice, advice and reactions to recent results |
| `inventory` | F2 item pages |
| `minimap` | F1 map |
| `flowers` | The houseplant at home |

Each feature README is a table of what it owns (engine attributes = save format), its pages, actions, events, slots, config keys, the engine API it uses and its tests. Keep it current: `engine/tools/run_tests.py --feature X` runs `game/X/tests/` plus the shared test files named in its Tests row.

## A feature's folder

| File | Contents |
|---|---|
| `__init__.py` | `from game.<name>.feature import <Class> as Feature` |
| `feature.py` | The `Feature` subclass (more modules if needed, e.g. farming's `care.py`, `market.py`, `drawing.py`) |
| `README.md` | The ownership table |
| `client.js` | Optional. What the game page shows for this feature's pages, registered with `DotdewPages.register({...})` (task texts, status lines, hidden object types, empty-list help) or `DotdewPages.every(ms, fn)` |
| `audio/`, `assets/` | Optional. Sounds and texture sheets, served at `/static/features/<name>/audio/` and `/assets/` |
| `tests/` | Optional. `test_*.py` (needs `__init__.py`), `test_*.cjs`, `test_*.mjs` |

## Adding a feature: example

```python
# game/greenhouse/feature.py
from engine.core import order
from engine.core.registry import Feature


class Greenhouse(Feature):
    name = "greenhouse"

    def register(self, reg):
        reg.owns("greenhouse_level")                         # engine attribute; its name is part of the save format
        reg.save_fields(defaults=("greenhouse_level",))      # older saves get the default
        reg.page("greenhouse", objects=self.page_objects, icon_grid=True)
        reg.action("greenhouse:upgrade", self.upgrade)       # actions after the night guard by default
        reg.state("greenhouse_level", lambda: self.engine.greenhouse_level)
        reg.on("reset", self.reset, order=order.DEFAULT)

    def reset(self):
        self.engine.greenhouse_level = 0

    def page_objects(self):
        return [self.engine.back_arrow()]

    def upgrade(self, arg, obj):
        e = self.engine
        e.greenhouse_level += 1
        return e.response(tts=f"Greenhouse level {e.greenhouse_level}.")
```

Then add `"greenhouse"` to `ENABLED` in `game/__init__.py` (approval: it changes the registration order every feature shares). Things other features or the engine must know go through **events** (`reg.on`, `registry.run`; list in `engine/core/registry.py` `EVENTS`) and **slots** (`reg.slot`, `reg.contribute`, e.g. `inventory.items`, `shop.buy_items`, `home.objects`). Use `reg.expose(name, fn)` only for methods tests or tools call on the engine, or for features that already depend on each other; every exposed name is listed in `engine/tests/python/core/test_registry.py`. A browser `client.js` also needs one script tag in `engine/web/game.html`, and a new sound needs entries in `engine/web/core/game-audio.js` and `engine/launcher/check_setup.py` (all engine changes, so approval).

## Gameplay

Values are the current `engine/config/game.json` settings.

**Locations.** Home (sleep, research, cook) ↔ Farm (plant, water, fertilize, harvest) and Home ↔ Village (shop, Rowan) ↔ Mine (rocks) ↔ Fishing lake. Crops are sold or cooked, minerals traded or spent on research, food eaten from the inventory for an effect.

**Time and sleep.** Time passes only when an activity finishes: each day has 20 ticks; travel 0, planting/watering/fertilizing 2, harvesting/research/cooking 3, a broken rock 2, a cast 2 (`time.action_costs`). When the day runs out the player returns home. Sleep turns the tactile panels off briefly and pauses music; the sleep sound plays to its end into the next morning. The pad shows a lower time panel, the companion a thin orange bar.

**Farming.** Select a plot for its detail screen: empty plots take seeds; planted plots show growth, water and fertilizer. Watering and fertilizing are press-and-drag target minigames; you can continue over the remaining targets until done. Watered crops grow overnight; fertilizer advances growth immediately. On the farm a plot fills from the bottom as it grows.

**Harvest.** Every target must be collected. Yield is the crop's base amount times the active food effect (no score multiplier); seed recovery uses the crop's chance or its research level. A blooming houseplant adds a bonus.

**Cooking and food.** Choose a recipe, select all ingredients, then trace the chopping path and the second path in order; ingredients and time are spent only when both are done. There is no time limit; a marker shows where to resume, and traced sections fade after a delay. One food effect is active at a time; eating another replaces it.

| Food | Ingredients | Effect | Duration |
|---|---|---|---|
| Tomato carrot stew | Tomato, carrot | Harvest boost | 6 hours |
| Potato tomato soup | Potato, tomato | Pickaxe protection | 10 hours |
| Vegetable fritters | Potato, carrot | Time saving | 10 hours |

Fish dishes: see `game/seafood/README.md`.

**Shop and inventory.** The shop sells seeds, fertilizer, a pickaxe (one at a time), a fishing rod and some minerals, and buys crops, food, fish and minerals. Prices change by weekday (`game/village/README.md`). Inventory shows owned items only, twelve per page, gold and food first; tactile frames mark food with an oval, gold with a diamond, other items with rectangles and category symbols.

**Mining and research.** Up to seven rocks a day; a rock takes three hits and its inner dots thin out with damage while the outline stays. Rocks drop stone, copper, iron or diamonds. Pickaxe durability is hidden; a broken tool plays the shared destroy sound.

| Research | Materials | Effect |
|---|---|---|
| Seed recovery | Gold, copper | Better seed recovery |
| Farm expansion | Gold, stone | Two to six plots |
| Mineral luck | Gold, iron | Better drops and bonus quantities |

## Planned work and evaluation

User testing (not yet done) will look at comprehension and enjoyment, the workload of tactile and spoken information, and the usability and accuracy of hand gestures, with about six to eight visually impaired participants (task completion, time, errors, comprehension, workload, gesture accuracy). Planned: better calibration, jitter and occlusion handling for tracking, separating exploration from action input, lower input and render latency on older laptops, more NPC dialogue, and ranching, music activities, quests and crafting. The design assumes usable hearing and hand control.

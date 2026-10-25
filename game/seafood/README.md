# Seafood

Fish as cooking ingredients, graded seafood dishes, and the food effects they grant (rare finds, double loot, better sale prices).

| Item | Value |
|---|---|
| Code | `feature.py` (`Seafood`) |
| Pages / actions | none of its own; works inside cooking's `ingredient_select` page (`toggle_ingredient:fish:<id>`) |
| Owned engine attributes | none |
| Shared attributes written | `selected_ingredients` (cooking, paired), `pointer_pressed`, `current_page`/`current_location` (after a dish), `resources` crops/fish (via `add_resource`) and foods; spends time with `consume_time("cook")` |
| Shared attributes read | `selected_recipe_id`, `active_buff`, `resources` |
| Events | emits `activity` ("cooking") |
| Saves | Migration: retired `fried_fish_high` becomes `fried_fish_medium`; an active seafood effect adopts the current recipe strength |
| Engine API provided | to cooking (paired): `selected_fish`, `seafood_ready`, `seafood_ingredient_objects`, `toggle_fish`, `finish_seafood` |
| Engine API used | `fishing_config` (fishing), `open_cooking_minigame`, `clear_cooking` (cooking, paired); `loot_amount` (core effects), `get_recipe_config` (core) |
| Config | `engine/config/game.json` → seafood entries in `recipes` (`seafood`, `allowed_fish`, `fish_required`, `quality_effects`) |
| Slots | none |
| Client (web) | none (no `game/seafood/` folder; the game page shows its pages with the shared defaults); fish textures belong to fishing |
| Tests | `engine/tests/python/audio/test_gameplay_audio.py` (cooking reaction) |
| Note | Seafood dishes grant food effects (rare finds, double loot, better sales); the modifiers that apply them are in `engine/core/effects.py`. |

## Gameplay

In the ingredient screen choose one owned fish and the vegetable; cooking starts when both are selected and uses them only after both paths are traced. Each dish accepts only its `allowed_fish`:

| Dish | Vegetable | Fish (grade) | Effect (low / medium / high) |
|---|---|---|---|
| Grilled fish | Potato | mackerel (low), carp (medium), salmon (high) | Rare finds (iron, diamonds, high-grade fish) ×1.5 / ×2 / ×3 for 12 / 14 / 16 ticks |
| Fish stew | Tomato | sardine (low), catfish (medium), rainbow trout (high) | Sale prices +25 / +50 / +80 % (rounded down) for 3 / 4 / 5 sales; failed sales and purchases use no charge |
| Fried fish | Carrot | bass (low), flounder (medium); no high variant | 30 / 60 % chance to double crops, recovered seeds, minerals, fish or dishes for 12 / 14 ticks (not purchases or sale gold) |

Dish names say Simple / Ordinary / Luxurious; descriptions show the effect and its remaining hours or sales, never the multipliers. One food effect is active at a time. Preparation and second-stage paths come from `cooking_methods.gestures` (fish preparation, grilling, stirring, frying), referenced by `method` in each recipe's `gesture_steps`. Older saves: high-grade fried fish becomes the medium variant, and an active seafood effect takes the current strength without resetting its remaining time or exceeding the new sale count.

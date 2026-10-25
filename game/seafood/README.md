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
| Tests | `tests/python/audio/test_gameplay_audio.py` (cooking reaction) |
| Note | Seafood dishes grant food effects (rare finds, double loot, better sales); the modifiers that apply them are in `engine/core/effects.py`. |

# Seafood

Fish as cooking ingredients, graded seafood dishes, and the food effects they grant (rare finds, double loot, better sale prices).

| Item | Value |
|---|---|
| Code | `feature.py` (`Seafood`) |
| Pages / actions | none of its own; works inside cooking's `ingredient_select` page (`toggle_ingredient:fish:<id>`) |
| Owned engine attributes | none |
| Shared attributes written | `selected_ingredients`, `pointer_pressed`, `active_buff` (sale uses), `current_page`/`current_location` (after a dish), `resources` crops/fish (via `add_resource`) and foods; spends time with `consume_time("cook")` |
| Shared attributes read | `selected_recipe_id`, `active_buff`, `resources` |
| Events | emits `activity` ("cooking") |
| Saves | Migration: retired `fried_fish_high` becomes `fried_fish_medium`; an active seafood effect adopts the current recipe strength |
| Engine API provided | to cooking (core, paired): `selected_fish`, `seafood_ready`, `seafood_ingredient_objects`, `toggle_fish`, `finish_seafood`; food-effect modifiers: `boost_rare_weights` (mining, fishing), `loot_amount` (mining, fishing, harvest, cooking), `sale_price` (village market), `consume_sale` (core shop) |
| Engine API used | `fishing_config` (fishing), `get_recipe_config`, `open_cooking_minigame`, `clear_cooking` (cooking, core) |
| Config | `config/game.json` → seafood entries in `recipes` (`seafood`, `allowed_fish`, `fish_required`, `quality_effects`) |
| Tests | `tests/python/audio/test_gameplay_audio.py` (cooking reaction) |
| Note | The food-effect modifiers act on `active_buff`, which belongs to cooking; they are planned to move to cooking when it is extracted. |

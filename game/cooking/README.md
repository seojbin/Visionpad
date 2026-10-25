# Cooking

Recipes, ingredient selection, the traced cutting/stirring minigame (with fading trace, resume marker and deferred step completion), and eating food to start a food effect.

| Item | Value |
|---|---|
| Code | `feature.py` (`Cooking`); food effects themselves live in `engine/core/effects.py` (shared) |
| Pages | `recipe_select`, `ingredient_select` (icon grid, location texts), `cooking` (live page: re-rendered on every state read; path drawn as the page scene; raw pointer move/press/drag trace through `engine.minigame_input`) |
| Actions (after the night guard) | `open_recipes`, `select_recipe:<id>`, `toggle_ingredient:<seed>` (fish keys go to seafood), `start_cooking`, `use_food:<recipe>` |
| Object types | `recipe` (food frame), `ingredient` (check mark when selected), `cooking_start` (icons, hover sounds) |
| Owned engine attributes (save format) | `selected_recipe_id`, `selected_ingredients`, `cooking_dragging`, `cooking_path_samples`, `cooking_visible_until`, `cooking_progress_index`, `cooking_stage_index`, `cooking_last_progress_at`, `cooking_resume_marker` |
| Shared attributes written | `resources` crops (via `add_resource`) and foods, `current_page` (via `set_page`), `current_location`, `last_pointer`, `pointer_pressed`, `pending_visual_completion`; `active_buff` through `start_food_effect` (core); spends time with `consume_time("cook")` |
| Events | `reset` (`Reset.COOKING`), `leave_activity` (`LeaveActivity.COOKING`), `release_drag`, `before_state` (resume marker); emits `activity` ("cooking") |
| Visual completion | `cooking`: the next step (or the dish) once the last traced dots have faded |
| Slots contributed | `inventory.items` (`InventoryItems.COOKING`), `shop.sell_items` (`ShopSellItems.COOKING`); sells `food` |
| State / spectator keys | `cooking` / `path` |
| Saves | `cooking_dragging` is saved as False; `cooking_last_progress_at` and `cooking_visible_until` are saved relative to the save time |
| Engine API provided | `can_craft_recipe` (home kitchen count), `open_cooking_minigame`, `clear_cooking` (seafood, paired), `finish_cooking_success`, `use_food`, `get_cooking_gesture` (tests, tools) |
| Engine API used | from seafood (paired): `seafood_ready`, `seafood_ingredient_objects`, `toggle_fish`, `selected_fish`, `finish_seafood`; from fishing: `get_fish_price`, `fishing_config` (seafood dish prices) |
| Config | `engine/config/game.json` → `recipes.*`, `cooking_methods.gestures`, `interaction.cooking.*` |
| Client (web) | `game/cooking/client.js` (task text for `ingredient_select`/`cooking`, stage progress, empty-list help, debug status line); sounds `game/cooking/audio/cut.mp3`, `cook.mp3` |
| Tests | `tests/python/audio/test_sound_events.py`, `tests/python/audio/test_gameplay_audio.py`, `tests/python/audio/test_audio_flow.py`, `tests/js/audio/test_guidance.cjs` |
| Note | `fail_or_continue` and `draw_recipe_icon` were unreachable before the split (the minigame branch returned first); kept for parity. |

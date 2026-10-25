# Farming

Farm plots: planting from the seed page, watering and fertilizing (care minigame, or a held drag tool), overnight growth and the morning "ready to harvest" note, and farming items in the inventory and shop.

| Item | Value |
|---|---|
| Code | `feature.py` (`Farming`: registration, plots, planting, growth), `care.py` (care minigame), `market.py` (inventory and shop rows, seed/fertilizer buying, crop selling), `drawing.py` (tactile plot drawings) |
| Pages | `farm`, `plot_detail` (icon grid for care buttons only, scene lines, gauge/field layout), `seed_select` (icon grid), `water_minigame` / `fertilizer_minigame` (live pages; raw pointer through `engine.minigame_input`; target guidance) |
| Actions (after the night guard) | `open_plot_detail:<plot>`, `open_seed_select:<plot>`, `plant:<plot>:<seed>`, `start_care:<water|fertilizer>:<plot>`, `drag_tool:<water|fertilizer>` |
| Drag tools | `water`, `fertilizer`: dropping on a plot waters or fertilizes it once per hold. No object currently offers a drag tool (unreachable before the split too, except through the pointer path). |
| Object types | `plot`, `plot_detail_field`, `growth_gauge`, `care_field`, `care_target` (renderers); `seed`, `care_button`, `watering_can`, `fertilizer` (icons; flowers' page reuses `care_button`); hover speech for plots and seeds; hover sounds |
| Owned engine attributes (save format) | `farm_plots`, `seed_select_plot_id`, `detail_plot_id`, `care_mode`, `care_targets`, `care_dragging`, `care_collected_ids`, `care_visible_until` |
| Shared attributes written | `resources` seeds/fertilizer/crops/coin, `current_page` (via `set_page`), `current_location`, `last_pointer`, `pending_visual_completion`; core input state `drag_tool`, `drag_target_ids` while a tool is held; spends time |
| Written by other code | core navigation resets `seed_select_plot_id` (travel, return to scene, night, morning, map/inventory `open`); harvest resets a plot and `detail_plot_id` (paired) |
| Events | `reset` (`Reset.FARMING`), `end_of_day` (`EndOfDay.FARMING`, returns the morning note), `leave_activity` (`LeaveActivity.FARMING`), `release_drag` |
| Visual completion | `care`: applies water/fertilizer once the last covered targets have faded |
| Slots contributed | `inventory.items` (`InventoryItems.FARMING`), `shop.buy_items` (`ShopBuyItems.FARMING`), `shop.sell_items` (`ShopSellItems.FARMING`); shop kinds `seed`, `fertilizer` (buy), `crop` (sell) |
| State keys | `farm_plots`, `seed_select_plot_id`, `plot_detail_id`, `care`; spectator `plots`, `care_targets` |
| Saves | `care_dragging` saved as False; `care_visible_until` saved relative to the save time |
| Engine API provided | `new_plot_state`, `get_effective_seed_return_chance`, `clear_care` (harvest, paired); `get_fertilizer_price` (mining pickaxe price); `get_unlocked_plot_defs`, `open_plot_detail`, `plant_seed`, `start_care_minigame`, `finish_care_minigame` (tests, tools) |
| Engine API used | `clear_harvest`, `get_harvest_base_yield` (harvest, paired); `market_price` (village); `get_seed_config`, `get_seed_label`, `draw_icon_pattern`, `object_contains` (core) |
| Config | `config/game.json` → `farm.*`, `seeds.*`, `care_minigame.*`, `fertilizer.*`, `research.seed_return.*`, `time.action_costs.*` |
| Client (web) | `web/features/farming/client.js` (farm task text, plot detail and care coverage text, hides `care_target`/`care_field` from the object list, status line); sounds `web/features/farming/audio/water.mp3`, `soil.mp3` |
| Tests | `tests/python/audio/test_sound_events.py`, `tests/python/audio/test_team_audio.py`, `tests/python/audio/test_audio_flow.py`, `tests/python/saves/test_save_compat.py` (plot state) |

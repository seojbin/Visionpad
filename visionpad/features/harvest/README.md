# Harvest

The crop-collecting minigame on a mature plot: drag across the crop targets, then yield (with food boosts and the flower bonus) and seed recovery.

| Item | Value |
|---|---|
| Code | `feature.py` (`Harvest`) |
| Pages | `harvest` (raw pointer move/press/drag collect through `engine.minigame_input`; target-sound guidance) |
| Actions (after the night guard) | `start_harvest:<plot>` |
| Object types | `harvest_field` (box), `harvest_crop` (cross); hover sounds |
| Owned engine attributes (save format) | `harvest_plot_id`, `harvest_targets`, `harvest_dragging`, `harvest_collected_ids` |
| Shared attributes written | `farm_plots[plot]` reset and `detail_plot_id` cleared after a harvest (farming, paired); `resources` crops/seeds; `current_page` (via `set_page`), `current_location`, `last_pointer`; spends time with `consume_time("harvest")` |
| Shared attributes read | `config`, `farm_plots`, `research_levels` (via seed recovery chance), `active_buff` (via core effects) |
| Events | `reset` (`Reset.HARVEST`), `leave_activity` (`LeaveActivity.HARVEST`), `release_drag`; emits `activity` ("harvest") |
| Slot declared | `harvest.bonus` (flowers contributes while blooming) |
| State / spectator keys | `harvest` / `harvest_targets` |
| Saves | `harvest_dragging` is saved as False |
| Engine API provided | `start_harvest_minigame`, `finish_harvest_minigame` (tests, tools), `clear_harvest`, `get_harvest_base_yield` (farming, paired) |
| Engine API used | `new_plot_state`, `get_effective_seed_return_chance` (farming), `loot_amount`, `buff_multiplier_for` (core effects) |
| Config | `config/game.json` → `harvest_minigame.*`, `seeds.*.yield`, `time.action_costs.harvest` |
| Tests | `tests/python/audio/test_gameplay_audio.py`, `tests/python/audio/test_sound_events.py`, `tests/python/audio/test_team_audio.py` |
| Note | `press` and `collect_point` were unreachable before the split (presses always went to the minigame handler); kept for parity. |

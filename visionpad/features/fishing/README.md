# Fishing

The lake: a hidden target that moves after every cast and each morning, distance zones, rarity rolls, rod wear and breakage, and fish/rod prices.

| Item | Value |
|---|---|
| Code | `feature.py` (`Fishing`) |
| Pages | `fishing` (lake outline drawn as the page scene; a press casts; single press per hold; arrival and location texts) |
| Actions | none; casting is the page's `press` hook |
| Owned engine attributes (save format) | `fishing_target`, `fishing_last_catch`, `fishing_attempts`, `rod_casts`, `rod_catches` |
| Resource keys created | `resources["fishing_rod"]`, `resources["fish"]` |
| Shared attributes written | `resources["coin"]` (via `add_resource`); spends time with `consume_time("fish")` |
| Shared attributes read | `config`, `current_page`, `paused`, `day_ended`, `sleep_until`, `dotpad` |
| Events | `reset` (`Reset.FISHING`, after the mine), `start_of_day` (`StartOfDay.FISHING`, before the mine); emits `activity` ("fishing", "fishing_miss", "tool_broken") |
| Slots contributed | `inventory.items` (`InventoryItems.FISHING`) |
| Shop | buys `fishing_rod` (market priced). The rod buy row and the fish sell branch are still in the core shop until shop is extracted. |
| State key | `fishing` |
| Saves | Defaults for all five attributes; older saves get `fishing_rod: 0` and an empty `fish` bag |
| Engine API provided | `fishing_config()` (seafood, cooking/shop in core), `cast_fishing(x, y)` (tests), `get_rod_price()`, `get_fish_price(fish_id)` (core shop) |
| Engine API used | `get_mineral_price` (mining), `boost_rare_weights`, `loot_amount` (seafood), `market_price` (village), `item_destroyed_event` (core) |
| Config | `config/game.json` → `fishing.*`, `resources.fishing_rod`, `resources.fish`, `time.action_costs.fish` |
| Tests | `tests/python/audio/test_gameplay_audio.py`, `tests/python/audio/test_sound_events.py`; JS `tests/js/audio/test_fishing_audio.cjs` (client sounds) |

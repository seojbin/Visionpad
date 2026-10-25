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
| Shop | `fishing_rod` (buy) and `fish` (sell), market priced. Rows in `shop.buy_items` (`ShopBuyItems.FISHING`) and `shop.sell_items` (`ShopSellItems.FISHING`). |
| State key | `fishing` |
| Saves | Defaults for all five attributes; older saves get `fishing_rod: 0` and an empty `fish` bag |
| Engine API provided | `fishing_config()` (seafood; cooking in core), `cast_fishing(x, y)` (tests), `get_fish_price(fish_id)` (shop, for seafood dish prices) |
| Engine API used | `get_mineral_price` (mining), `boost_rare_weights`, `loot_amount` (seafood), `market_price` (village), `item_destroyed_event` (core) |
| Config | `config/game.json` → `fishing.*`, `resources.fishing_rod`, `resources.fish`, `time.action_costs.fish` |
| Client (web) | `web/features/fishing/client.js` (lake task text with and without a rod, empty-list help); sound `web/features/fishing/audio/splash.mp3`; texture `web/features/fishing/assets/items2.png` (fish and fish dishes). The lake sonar is still in `web/core/game-audio.js` (FOLLOWUPS F16) |
| Tests | `tests/python/audio/test_gameplay_audio.py`, `tests/python/audio/test_sound_events.py`, `tests/js/audio/test_fishing_audio.cjs` (client sounds) |

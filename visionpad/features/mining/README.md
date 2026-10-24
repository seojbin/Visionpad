# Mining

Daily rocks at the mine, pickaxe wear and breakage, mineral loot (with mineral-discovery research and food effects), and mineral prices.

| Item | Value |
|---|---|
| Code | `feature.py` (`Mining`) |
| Pages | `mine` (single press per hold; target-sound guidance; arrival and location texts) |
| Actions | `mine_hit:<rock_id>` (after the night guard) |
| Object types | `mine_rock` (renderer, exact rectangle hit test) |
| Owned engine attributes (save format) | `mine_rocks`, `_pickaxe_hits` |
| Shared attributes written | `resources` minerals (via `add_resource`), `resources["pickaxe"]` (set to 0/1), `resources["coin"]` (via `add_resource`), `hover_object_id`; spends time with `consume_time("mine")` |
| Shared attributes read | `config`, `day`, `current_page`, `paused`, `day_ended`, `research_levels["mineral_luck"]`, `MINERAL_LABELS` |
| Events | `reset` (`Reset.MINING`, before fishing's random draws), `start_of_day` (`StartOfDay.MINING`, after fishing); emits `activity` ("mining", "tool_broken") |
| Slots contributed | `inventory.items` (`InventoryItems.MINING`) |
| Shop | buys `pickaxe` and `mineral` items (market priced). Buy rows and the mineral sell branch are still in the core shop until shop is extracted. |
| Spectator key | `rocks` |
| Engine API provided | `get_mineral_price(mineral, buying=False)` (core shop, seafood), `hit_mine_rock(rock_id)` (tests) |
| Engine API used | `market_price` (village), `boost_rare_weights`, `loot_amount` (seafood), `buff_multiplier_for` (cooking, core), `get_pickaxe_price` (core shop), `item_destroyed_event` (core) |
| Config | `config/game.json` → `mine.*`, `research.mineral_luck.*`, `time.action_costs.mine` |
| Tests | `tests/python/audio/test_gameplay_audio.py` (rock guidance, tool break) |
| Note | `draw_item` was unused before the split (AUDIT.md §2.4); kept for parity. |

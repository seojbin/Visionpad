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
| Config | `engine/config/game.json` → `fishing.*`, `resources.fishing_rod`, `resources.fish`, `time.action_costs.fish` |
| Client (web) | `game/fishing/client.js` (lake task text with and without a rod, empty-list help); sound `game/fishing/audio/splash.mp3`; texture `engine/web/spectator/assets/items2.png` (fish and fish dishes). The lake sonar is still in `engine/web/core/game-audio.js` (follow-up F16) |
| Tests | `engine/tests/python/audio/test_gameplay_audio.py`, `engine/tests/python/audio/test_sound_events.py`, `game/fishing/tests/test_fishing_audio.cjs` (client sounds) |

## Gameplay

The lake is open without a rod; casting needs one (100 gold, `fishing.rod_price`, one at a time). Move the pointer or tracked finger towards the looping water sound, then press inside the tactile lake outline: each valid cast costs `time.action_costs.fish` (2 ticks), hit or miss, and moves the target. Holding or dragging does not cast again; pressing outside the lake costs nothing. Use stereo headphones: the sound is placed relative to the pointer with HRTF and gets louder near the target (`interaction.audio.fishing`: gain 0.12–0.85, `distance_scale` 40, `tts_multiplier` 1, music at 0.2 with the basic track).

Zones: near (`near_radius` 4), middle (a circle of 1/6 of the pad area, `middle_area_fraction`), far. Miss/low/medium/high weights are far 30/40/20/10, middle 10/30/40/20, near 10/20/30/40; species within a grade are equally likely.

| Grade (name shown on dishes) | Fish | Sell price |
|---|---|---|
| low (Simple) | Sardine, Mackerel, Bass | 24 |
| medium (Ordinary) | Carp, Catfish, Flounder | 27 |
| high (Luxurious) | Salmon, Rainbow trout | 36 |

Rarity is never spoken. A catch plays splash; a high-grade catch plays splash and shine together; a miss plays neither. Four successful catches are safe, then the break chance rises by 10 points per catch (`rod_safe_catches`, `rod_break_increment`); misses do not wear the rod, a doubled catch counts once, and the breaking cast keeps its catch (plus the destroy sound). The companion shows the lake from `scene3.png`, fish from `assets/items2.png` and the equipped rod while one is owned. Saves from before fishing get an empty fish bag, no rod and zero rod use.

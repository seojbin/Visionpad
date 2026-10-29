# Pasture

The pasture is west of the farm. New games start without animals. Buy one chicken (100 gold) and one sheep (250 gold) from Shop → Tools. Existing saves keep their owned animals. Upper icons and moving animals both open animal care. The companion is read-only.

Move back and forth over the animal in its detail view to pet it. Moving contact accumulates for 3 seconds and silently awards affection once per day. Holding still does not count. There is no Pet button, progress percentage or spoken completion announcement. The animal main call plays once when the daily affection award is granted, alongside the brush work sound. Not petting causes no affection loss. **Feed** consumes the shared animal feed bought at the shop for 30 gold. Animals graze without feed, but can escape if neglected. Eggs take 1–2 days (80% / 20%); wool takes 2–4 days with equal weights. Feed shortens a cycle by one day; if tomorrow is already the collection day, it shortens the next cycle instead. Ready products remain until collected. Select **Collect eggs**, then click the raised, diagonally textured egg in the collection view. For wool, select **Shear wool** (or the ready sheep) and move over the fleece without holding a button. The action buttons remain visible when products are not ready. Each completed collection costs 3 activity ticks. Shearing completes at 75% coverage by default.

The three visible states are Indifferent, Recognizes you and Seems happy. The internal thresholds and penalties below are developer settings, not spoken instructions. Eggs yield 1, or 2 with 20% probability; wool yields 2–5 bundles. Each egg production rolls once and adds 1–2 eggs to the nest, capped at 3. A new 1–2 day cycle runs while the nest has room. Wool stays ready without further production until collected. Saved quantities never reroll on load. Collecting eggs empties the nest and starts a fresh cycle. Affection still controls the visible mood and escape grace, but no longer multiplies production.

| Area | Implementation |
|---|---|
| Code | `game/pasture/feature.py` |
| Pages | `pasture`, `animal_detail`, `egg_collect`, `shearing` |
| Actions | `animal:open:<kind>`, `animal:feed`, `animal:gather`, `animal:collect`, `animal:shear`, `animal:cancel` |
| Object types | `animal_icon`, `animal_care`, `animal_hitbox`, `egg_target` |
| Owned engine attributes | `pasture_animals`, `pasture_goods`, `pasture_selected`, `pasture_sheared`, `pasture_move_at`, `pasture_stroke`, `pasture_morning_id` |
| Shared attributes written/read | Page through `set_page`; gold through resource methods; pointer position; day, pause, sleep and night state |
| Events | reset, end_of_day, start_of_day, before_state, before_navigation, leave_activity, release_drag |
| Slots | inventory.items, shop.buy_items, shop.sell_items |
| State keys | pasture: public animal status, positions, collection state, audio timing; no numeric affection |
| Saves | Animals, production timers, queued feed bonus, goods, pet/feed dates and partial shearing persist. Pointer strokes and animation clocks reset. Old saves receive animals at their current day. |
| Engine API provided/used | Provided: none. Used: back_arrow, set_page, clear_hover, render, response, resource, add_resource, market_price, point_to_segment_distance, draw_icon_pattern |
| Config | `engine/config/game.json` → pasture: animals.days/product/price/buy_price/wait_days/wait_weights/double_egg_chance/ready_capacity/yield_range, escape_grace_days, escape_increment, shear_success_ratio, feed_price, breath_seconds, move_seconds, move_interval_seconds, flip_interval_multipliers, shear_radius, pet_seconds, pet_contact_gap_seconds, pet_points, collect_points, feed_grace_days, collection_grace_days, unfed_penalty, uncollected_penalty, audio |
| Client (web) | `engine/web/core/game-audio.js` schedules calls; `engine/web/core/game.js` refreshes moving animals; companion viewer and asset catalog render animals and fleece. Audio files live in `game/pasture/audio/`. |
| Tests | `game/pasture/tests/test_production.py`, `game/pasture/tests/test_interaction_fixes.py`, `game/pasture/tests/test_purchase_escape.py`, `game/pasture/tests/test_pasture.py`, `game/pasture/tests/test_animal_audio.cjs`, `engine/tests/python/saves/test_save_compat.py` |

Developer defaults: each stage is 100 points (maximum 299); pet +10 once per day, collection +30. After four days without feed, each subsequent morning subtracts 20. After two days with uncollected products, each subsequent morning subtracts 30. These losses do not destroy an existing product. Shared animal feed costs 30; eggs sell for 70 and wool for 100 before market/food modifiers. Petting and feeding do not spend activity time. Completed egg/wool collection uses time.action_costs.animal_collect (3).

Routine calls use the uploaded 5-second interval and 1.0 gain; detail pages use only the selected animal. Entering care and completing interactions use the main call at 1.3. A chicken morning call is scheduled 2.5 seconds after the new day arrives. Pause/mute cancels pending calls. No new TTS voice model is required.

## Escape and ownership

At each new day, escape probability is `min(1, max(0, days_without_feed - grace) * 0.1)`. Grace is 1/2/3 days for the three affection levels, evaluated before that morning's affection losses. Existing affection decay remains in place. Escape removes the animal and uncollected products, clears pending shearing, and adds a short morning notice without revealing the probability. It can be repurchased, starting a fresh production cycle and affection state. Owned animals alone appear on the map and produce calls. No chicken means no morning call.

The uploaded ICON_PATTERNS, SCENE_PATTERNS and DETAIL_PATTERNS are retained. Decorative tactile grass marks were removed; the existing companion background and sprite sheets remain. Shearing uses `game/pasture/audio/cut.mp3` under a distinct `shear` sound ID, so cooking's cut recording is unchanged.

Petting uses `audio/brush.mp3` as an independent work sound at gain 2.5, including during speech. It stops on idle, leaving the animal, pause or page change. Only completed daily pet awards are saved; unfinished contact time resets when animal care is reopened.

Owned animals move independently at random 3–5 second intervals. Their facing flips every randomly sampled movement interval multiplied by a random 3–5 factor (9–25 seconds). Both the tactile scene and companion mirror the same saved facing flag; menu icons and detail graphics stay fixed. Pausing or leaving the pasture resets animation deadlines.

The ready egg in animal care can also be collected directly with one click. Legacy chicken/sheep feed counts merge into animal_feed on load. Escaped animals are named in the short pasture arrival message until repurchased. Animal care graphics bob upward by one dot every 1.5 seconds, matching the companion; buttons and the egg stay fixed. Shop animal icons reuse the same padded chicken/sheep patterns as pasture icons.

Shearing erases individual raised dots within a circular swept brush, not 5×5 tiles. Completion counts erased fleece dots only; progress uses the existing pasture_sheared save field with a dots_v1 marker in sheep state. Old tile progress is converted on load. The companion uses the same per-dot mask. Ready counts are hidden from short/detailed speech and companion status; collection announces the actual awarded quantity without appending mood. Successful feeding plays feed.mp3 at one_shot_gain.feed=1.8 alongside the animal main call.

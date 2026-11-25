# Pets

Home → Care → Pets. Use dog/cat adoption vouchers in the inventory, then choose one of 12 species-specific names. The voucher is consumed only after confirmation. Each pet has a persistent ID, name and pitch. Up to twelve pets can live together. Existing pet names are excluded and checked again at confirmation. Care retains the home scene below Back / Plants / Pets. The active pet replaces the pet house. Only Change pet inside detail opens the owned-pet selector; empty slots are hidden. Home routines rotate through all owned pets. A detail page plays only the selected pet's routine.

The detail page has four actions: Give something, Receive, Change pet, Let pet go. Give something opens normal feed, special feed and (only when sick) medicine. Feed uses shared animal feed once per day. Both normal and special feed use the existing feed sound. Move over the animal for two seconds to hear its main call. Further two-second strokes also trigger calls; affection rises only once daily, without a percentage announcement. Special feed adds 60 affection. After two days without feed the pet is hungry; after four it is sick. Medicine cures sickness and restores its feeding date. Pets do not die or escape. Sending a pet to a new family requires a separate confirmation and removes only that individual.

Affection stages are getting to know you / recognizes you / trusts you. At the two higher stages, a healthy, fed pet has a 15% / 30% daily gift chance: crop seeds for dogs, low-tier fish for cats. One gift waits until collected. Select Receive or click the gift beside the animal to collect it. A trusted, healthy, fed pet grants one extra crop per harvest; multiple pets do not stack this bonus. Food buffs remain independent. These defaults are configurable and numerical affection/probabilities are not spoken.

| Area | Implementation |
|---|---|
| Code | `game/pets/feature.py`, `game/pets/patterns.py` (icons; the detail drawings now come from `shapes.py`), `game/pets/shapes.py` (cat and dog at 36 × 24 with the proportions of the original drawings, one silhouette per pose; `TEXTURE` marks the body; `drawing(species, pose, facing_left)` returns the drawing as shown) |
| Pages | care (shows the home scene; Left/Right travel to the farm and the village like on the home page), pets, pet_detail, pet_release, pet_give, pet_names |
| Actions | pet:care/list/home/open/give/feed/treat/medicine/gift/release/release_confirm/detail/name/empty |
| Object types | pet_icon, pet_button, pet_body; the large drawing is shown with `engine.display.tactile.fur_rows` (solid limbs, textured body) |
| Owned engine attributes | pets, pet_next_id, pet_selected, pet_active, pet_contact, pet_pose_until, pet_adoption, pet_motion |
| Shared attributes written/read | pasture_goods.animal_feed, roulette_goods; resources for collected gifts; day, pointer, pause and sleep |
| Events | reset, end_of_day, before_navigation, leave_activity |
| Slots | home.objects, home.scene, home.scene_objects, harvest.bonus |
| State keys | pets: public names, species, stable pitch, status, selected ID and pose, brush bounds, audio settings |
| Saves | Individual pets, gifts, feed/pet dates, affection, health and pitches persist; contact/pose/movement clocks and pending adoption reset; the active pet persists; old saves default to no pets |
| Engine API provided/used | Provided: none. Used: response, render, set_page, clear_hover, back_arrow, draw_icon_pattern; paired roulette calls adopt/selected/sound |
| Config | engine/config/game.json → pets: max_pets, names (12 per species), pitch_values, pet_seconds, contact_gap_seconds, pet_points, feed_points, treat_points, hungry_days, sick_after_days, neglect_points, gift_chances, trusted_harvest_bonus, audio |
| Client (web) | engine/web/core/game-audio.js: same AudioContext, independent brush and calls, saved playback-rate pitches, one routine scheduler; engine/web/core/game.js live detail refresh |
| Tests | game/pets/tests/test_pets.py, game/pets/tests/test_audio.cjs, game/pets/tests/test_speech.cjs The scene is audited by `engine/tests/python/display/test_tactile_rules.py` (gaps, outlines, symbols per page). `game/pets/tests/test_care_navigation.py` covers the Care page arrow keys. |

Pitches 0.88–1.12 alter playback rate, so duration changes slightly too. No duplicate HTMLAudio output is used. Pause, mute, suspension and page departure stop scheduled routines. Sounds are the supplied original MP3 files. The companion uses new pet and supply sprite atlases and a dedicated room background; no generated spectator bundle is modified.

Pets translate every 3–5 seconds without changing direction or pose. Entry and completed care actions choose standing/sitting; the last quarter of activity time and day end show sleeping. Appearance is one of three variants per species, assigned at adoption and saved. Older pets use a stable ID-based variant. Main call gain is 1.8; cat routine gain is 0.8.

The standalone companion uses pets-v3.png (three appearances and sleeping sprites per species, wheel and supplies), pet-items.png (vouchers and gold kits), and pet-room.png. Assets were generated with the built-in image tool: warm farming-game pixel art, isolated atlas cells, no text, transparent sprites; the room is an empty cream rug in a wooden room. Registration is in visual-assets.json; display.js is unchanged.

Petting feedback: every two seconds of valid movement over the animal emits its main call and resets the feedback timer. Affection still increases only once per animal per day. Configure `pets.pet_seconds` or `pasture.pet_seconds`; default 2 seconds. Standing still does not count as petting.

Petting release update: two seconds arms a response but does not emit a call while stroking. Leaving the body or remaining motionless for 0.5 seconds completes one session and triggers one main call. Affection increases only on the first qualifying session per animal per day. Idle completion is polled through before_state; transient feedback IDs prevent repeated playback of the same state. Pausing or leaving the page cancels an unfinished session.

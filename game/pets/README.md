# Pets

Home → Care → Pets. Use dog/cat adoption vouchers in the inventory, then choose one of 12 species-specific names. The voucher is consumed only after confirmation. Each pet has a persistent ID, name and pitch. Up to six pets, including duplicates, can live together. Care lists six pet slots. Selecting an owned slot brings that pet out and opens its detail page. Home has a pet house beside the flower area and shows the active pet in the lower-left area. Home routines rotate through all owned pets. A detail page plays only the selected pet's routine.

The detail page has four actions: Give something, Receive, Change pet, Let pet go. Give something opens normal feed, special feed and (only when sick) medicine. Feed uses shared animal feed once per day. Both normal and special feed use the existing feed sound. Move over the animal for three seconds to pet it; affection rises once daily, with a main call and no percentage announcement. Special feed adds 60 affection. After two days without feed the pet is hungry; after four it is sick. Medicine cures sickness and restores its feeding date. Pets do not die or escape. Sending a pet to a new family requires a separate confirmation and removes only that individual.

Affection stages are getting to know you / recognizes you / trusts you. At the two higher stages, a healthy, fed pet has a 15% / 30% daily gift chance: crop seeds for dogs, low-tier fish for cats. One gift waits until collected. Select Receive or click the gift beside the animal to collect it. A trusted, healthy, fed pet grants one extra crop per harvest; multiple pets do not stack this bonus. Food buffs remain independent. These defaults are configurable and numerical affection/probabilities are not spoken.

| Area | Implementation |
|---|---|
| Code | `game/pets/feature.py`, `game/pets/patterns.py` |
| Pages | care, pets, pet_detail, pet_release, pet_give, pet_names |
| Actions | pet:care/list/home/open/give/feed/treat/medicine/gift/release/release_confirm/detail/name/empty |
| Object types | pet_icon, pet_button, pet_body |
| Owned engine attributes | pets, pet_next_id, pet_selected, pet_active, pet_contact, pet_pose_until, pet_adoption, pet_motion |
| Shared attributes written/read | pasture_goods.animal_feed, roulette_goods; resources for collected gifts; day, pointer, pause and sleep |
| Events | reset, end_of_day, before_navigation, leave_activity |
| Slots | home.objects, home.scene, home.scene_objects, harvest.bonus |
| State keys | pets: public names, species, stable pitch, status, selected ID and pose, brush bounds, audio settings |
| Saves | Individual pets, gifts, feed/pet dates, affection, health and pitches persist; contact/pose/movement clocks and pending adoption reset; the active pet persists; old saves default to no pets |
| Engine API provided/used | Provided: none. Used: response, render, set_page, clear_hover, back_arrow, draw_icon_pattern; paired roulette calls adopt/selected/sound |
| Config | engine/config/game.json → pets: max_pets, names (12 per species), pitch_values, pet_seconds, contact_gap_seconds, pet_points, feed_points, treat_points, hungry_days, sick_after_days, neglect_points, gift_chances, trusted_harvest_bonus, audio |
| Client (web) | engine/web/core/game-audio.js: same AudioContext, independent brush and calls, saved playback-rate pitches, one routine scheduler; engine/web/core/game.js live detail refresh |
| Tests | game/pets/tests/test_pets.py, game/pets/tests/test_audio.cjs, game/pets/tests/test_speech.cjs |

Pitches 0.88–1.12 alter playback rate, so duration changes slightly too. No duplicate HTMLAudio output is used. Pause, mute, suspension and page departure stop scheduled routines. Sounds are the supplied original MP3 files. New companion pages use the existing tactile fallback pending dedicated pet art; no generated spectator bundle is modified.

Pets move slightly and choose a random pose every 3–5 seconds. Stroking does not force a pose. Home movement is bounded to the lower-left region; detail movement stays below the action row. Muzzles are shortened without changing the connected body silhouette. Cat routine gain defaults to 0.8; dog routine gain remains 0.35. Adjust pets.audio.cat_routine_gain independently.

The standalone companion viewer adds a pixel pet-house silhouette and a moving active-pet silhouette. New detail pages retain the tactile fallback. The generated display.js remains unchanged.

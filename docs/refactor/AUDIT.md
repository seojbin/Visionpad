# AUDIT — Visionpad (Dotdew Valley) modularization facts

Audited commit: `ea38001` (main, clean tree), 2026-10-24. Nothing in the repo was changed except adding this file.
Environment used: Windows 11, Python 3.12.10 (system, no venv; `fastapi`/`uvicorn`/`piper` NOT installed), Node.js NOT installed.
Static analysis script (AST, self.* reads/writes/calls per method) lived outside the repo; results are reproduced below.

Legend: `R` = reads, `W` = writes (assignment, aug-assign, subscript store, or mutator call such as `.append/.update/.clear/.add/.pop/.setdefault`), `->` = calls a method owned by another feature.

---

## 1. Baseline tests

### 1.1 Commands run

```
python -m unittest discover -p "test_*.py" -v          # HANGS (see test_speech_queue below); killed at 120 s
python -m unittest <module> -v                          # per module, 90 s timeout each
PYTHONUTF8=1 python -m unittest <module> -v             # re-run of modules that failed with UnicodeDecodeError
python -m unittest test_speech_queue.QueueTests.<name>  # per test, 20 s timeout
node --test ...                                         # NOT RUN: node not installed on this machine
```

### 1.2 Environment-caused failures (fix before using any baseline)

| Cause | Effect | Location |
|---|---|---|
| Tests read `game_config.json` with `Path.read_text()` (no `encoding=`). On Windows the locale codec (cp1252 here; cp949 on Korean Windows) fails on byte `0x8d`. | Every engine test in the module errors in `setUp` | `test_gameplay_audio.py:19`, `test_sound_events.py:16`, `test_speech.py:98`, `test_team_audio.py:17`, `test_demo_speech.py:44` (npc_config, passes by luck). Same bug in `build_display.py:5-6` (runtime tool). |
| `fastapi` not installed (no `.venv`) | `test_speech_api` import error (4 tests not collected) | `test_speech_api.py` imports `game_app` |
| Python 3.12 `unittest.assertRaises` calls `traceback.clear_frames()`, which clears the suspended frame of `SpeechQueue.run()` (the worker coroutine is in the exception traceback). Worker dies with `RuntimeError('cannot reuse already awaited coroutine')`; `good.future` never resolves; test has no timeout. | `discover` hangs forever | `test_speech_queue.py:90-95` × `speech_queue.py:71-90`. Reproduced outside unittest by calling `traceback.clear_frames(e.__traceback__)` after `await bad.future`. |
| `test_support.py` contains no TestCase (helper that stubs `dotpad` and loads `game_engine.py` as `display_engine`; nothing imports it) | "Ran 0 tests", exit code 5 when run alone | `test_support.py:1-27` |

### 1.3 Python BASELINE (with `PYTHONUTF8=1`; this is the list the refactor must reproduce)

Totals: 67 collectable tests in 9 modules + 4 uncollectable (`test_speech_api`). Result: **54 ok, 5 FAIL, 3 ERROR, 1 HANG, 4 not collected**.

```
test_audio_flow.AudioFlowTests.test_all_gameplay_milestones_are_reached_by_pointer_and_key_input   ok
test_audio_flow.AudioFlowTests.test_required_action_and_result_sounds_are_present                  ok
test_audio_flow.AudioFlowTests.test_save_and_load_preserve_the_completed_session                   ok
test_demo_speech.DemoSpeechTests.test_failed_line_is_not_reported_as_ready_and_can_retry           ok
test_demo_speech.DemoSpeechTests.test_missing_models_fail_before_generation                        ok
test_demo_speech.DemoSpeechTests.test_repeat_preparation_reuses_audio_and_rate_has_its_own_cache   ok
test_demo_speech.DemoSpeechTests.test_server_preparation_only_calls_speech_endpoints               ok
test_demo_speech.DemoSpeechTests.test_source_lines_are_unique_and_include_exact_npc_branches       ok
test_gameplay_audio.GameplayAudioTests.test_cooking_reaction_is_recorded_only_after_a_dish_is_created ok
test_gameplay_audio.GameplayAudioTests.test_first_fishing_catch_uses_the_actual_fish_name         ok
test_gameplay_audio.GameplayAudioTests.test_guidance_excludes_collected_targets_and_stops_during_pause ok
test_gameplay_audio.GameplayAudioTests.test_mined_rock_disappears_from_guidance_and_hit_progress_is_reported ok
test_gameplay_audio.GameplayAudioTests.test_old_progress_does_not_claim_a_first_ever_harvest       ok
test_gameplay_audio.GameplayAudioTests.test_reaction_is_remembered_across_save_and_dialogue_replay ok
test_gameplay_audio.GameplayAudioTests.test_real_harvest_gets_a_first_reaction_without_extra_resources_or_time FAIL  [A]
test_gameplay_audio.GameplayAudioTests.test_real_tool_break_gets_replacement_advice               ok
test_gameplay_audio.GameplayAudioTests.test_rejected_action_does_not_record_a_success             ok
test_sound_events.ActionSoundTests.test_buying_and_selling_emit_coin_but_rejections_do_not        ok
test_sound_events.ActionSoundTests.test_care_and_harvest_completion_keep_success_feedback         ok
test_sound_events.ActionSoundTests.test_cooking_completion_has_success_feedback                   ok
test_sound_events.ActionSoundTests.test_fishing_miss_and_invalid_cast_have_different_feedback     ok
test_sound_events.ActionSoundTests.test_menus_save_and_load_have_feedback_without_spending_time   ok
test_sound_events.ActionSoundTests.test_travel_and_shop_entry_emit_the_matching_recording_once    ok
test_speech.NpcTests.test_dialogue_is_unavailable_in_other_locations_and_while_paused             ok
test_speech.NpcTests.test_dialogue_topics_do_not_consume_resources_or_time                        FAIL  [A]
test_speech.NpcTests.test_farming_and_fishing_advice_uses_actual_state                            FAIL  [B]
test_speech.NpcTests.test_npc_is_a_selectable_tactile_target                                      ERROR [C] StopIteration
test_speech.NpcTests.test_old_saves_get_npc_defaults_and_current_dialogue_roundtrips              ERROR [B] KeyError 'shopkeeper'
test_speech.NpcTests.test_trade_and_goodbye_leave_dialogue_and_revisit_changes_greeting           FAIL  [B] 'town' != 'shop_choice'
test_speech.SpeechTests.test_corrupt_cache_is_regenerated                                         ok
test_speech.SpeechTests.test_invalid_voice_text_rate_and_path_are_rejected                        ok
test_speech.SpeechTests.test_partial_audio_is_not_cached_and_retry_succeeds                       ok
test_speech.SpeechTests.test_pronunciation_keeps_numbers_and_display_text                         ok
test_speech.SpeechTests.test_repeated_text_reuses_complete_audio                                  ok
test_speech.SpeechTests.test_voice_rate_model_and_pronunciation_change_cache_identity             ok
test_speech_api.*  (4: test_legacy_request_still_generates_speech, test_partial_client_identity_is_rejected_before_generation,
                    test_cancel_route_discards_old_request_but_accepts_current_one, test_generation_error_keeps_503_and_the_queue_can_retry)
                                                                                                  NOT COLLECTED (fastapi missing) — re-baseline inside .venv
test_speech_queue.QueueTests.test_action_overtakes_other_clients_hover_and_background             ok
test_speech_queue.QueueTests.test_active_generation_can_finish_without_delivering_obsolete_audio  ok
test_speech_queue.QueueTests.test_delayed_cancel_does_not_cancel_the_new_sequence                 ok
test_speech_queue.QueueTests.test_failure_does_not_block_the_next_request                         HANG (Python 3.12 clear_frames, see 1.2)
test_speech_queue.QueueTests.test_late_old_request_is_rejected_without_synthesis                  ok (run individually)
test_speech_queue.QueueTests.test_many_obsolete_hovers_never_reach_synthesis                      ok (run individually)
test_speech_queue.QueueTests.test_queue_capacity_is_bounded                                       ok (run individually)
test_startup.SetupChecks.* (5)                                                                    ok
test_startup.StartupTests.* (10)                                                                  ok
test_team_audio.TeamIntegrationTests.test_evaluation_click_command_keeps_selecting_instead_of_pausing ok
test_team_audio.TeamIntegrationTests.test_motion_without_press_still_collects_targets_and_updates_guidance ok
test_team_audio.TeamIntegrationTests.test_pre_audio_quest_save_keeps_its_stage_and_does_not_repeat_soup ok
test_team_audio.TeamIntegrationTests.test_shop_advice_is_selectable_without_advancing_the_quest   ERROR [C] StopIteration
test_team_audio.TeamIntegrationTests.test_tutorial_gifts_and_crop_reward_are_still_granted_once  ok
test_team_audio.TeamIntegrationTests.test_village_has_one_rowan_and_quest_replay_does_not_repeat_gifts FAIL [D] 2 != 1
```

Without `PYTHONUTF8=1` (Windows default): `test_gameplay_audio` 9 ERROR, `test_sound_events` 6 ERROR, `test_speech.NpcTests` 6 ERROR, `test_team_audio` 6 ERROR (all UnicodeDecodeError in setUp).

Failure causes (all are product/test drift, not refactor targets):
- [A] Talking to Rowan now runs the village quest (`NpcMixin.npc_action` → `VillageMixin.talk_rowan`, `game_npc.py:79-85`, `game_village.py:182-202`). Stage `new` grants `resources.foods.rowan_soup += 1`. Tests assert "talking costs nothing" → `rowan_soup` 1 != 0.
- [B] `npc_action(npc_id, topic)` ignores `topic` and always calls `talk_rowan()` (`game_npc.py:84-85`). Topic-based dialogue (greeting/farming/fishing/trade/goodbye, `npc_visits["shopkeeper"]`) no longer exists; `page="npc_dialogue"` is never set anywhere (see 2.4 dead code).
- [C] Shop page no longer contains an object with `id=="rowan"` / `action=="npc:shopkeeper:greeting"` (`get_shop_choice_objects`, `game_engine.py:1343-1361`).
- [D] Town has two objects with `action=="talk_rowan"` (`VillageMixin.rowan_object` `game_village.py:47-50` plus a second one from `town_spatial_objects` `game_village.py:62-80` / `get_town_objects` `game_engine.py:1024-1026`).

### 1.4 README-listed tests that do not exist

README.md:72 explicit list: `test_team_audio test_speech_queue test_speech_api test_gameplay_audio test_speech test_fishing test_sound_events test_audio_flow test_demo_speech test_startup` and `node --test test_speech.cjs test_guidance.cjs test_fishing_audio.cjs test_effects.cjs test_audio_integration.cjs test_hardware.mjs` ("147 tests total").

| Missing | Referenced at | History |
|---|---|---|
| `test_fishing.py` | README.md:72, 343, 357, 367, 377 | Deleted in `641c6f4` (2026-10-22, msg "디스플레이 추가", 109 lines) |
| `test_seafood.py` | README.md:357, 367, 377 | Never in this repo's history (any branch) |
| `test_fishing_polish.py` | README.md:377 | Never in history |
| `test_catch_audio.cjs` | README.md:377 | Never in history |
| `test_village.py` | README.md:414 | Never in history |
| Earlier deletions | — | `6bc3344` (2026-09-15) deleted `test_audio.cjs test_food_effects.py test_game.py test_mine.py test_recipes.py` |

Coverage gap implied: no tests exist for farming care/plant rules, mining, research, shop pricing, inventory paging, flowers, seafood, fishing rules, save migration edge cases, icon layout.

### 1.5 Node tests (NOT RUN — static analysis only; re-run with `node --test` after installing Node)

| File | node:test cases (grep) | Static expectation |
|---|---|---|
| `test_audio_integration.cjs` | 7 | Loads `web/game-audio.js`. Last test spawns `.venv/(Scripts|bin)/python` or `python` with `tools/audio_flow.py --stdout` → needs a working Python env. |
| `test_effects.cjs` | 10 | `web/game-audio.js` only |
| `test_fishing_audio.cjs` | 7 | `web/game-audio.js` only |
| `test_guidance.cjs` | 8 | `web/game-audio.js` only |
| `test_speech.cjs` | 18 | `web/game-speech.js`, `web/game-audio.js` |
| `test_hardware.mjs` | 12 | **Will fail at module link**: imports `BluetoothPad`, `cellsToHex` from `./web/hardware.mjs`, which exports only `packCells, displayPacket, extractPackets, forwardKey, SerialPad` (those two live in `web/bluetooth-pad.mjs`). Also imports `./web/vendor/DotPadSDK-3.0.3.js`, which is gitignored (`.gitignore` `/web/vendor/DotPadSDK-*`) and absent. Test file came from branch `bluetooth-dotpad` unchanged; main's integration split the code differently (`0d90cbf`). |
| `test_tracking_input.mjs` | 0 (top-level asserts) | **Will fail at module link**: imports `TrackingGestureInput` from `web/hardware.mjs`; class was added in `910d6c1` and removed by the Bluetooth integration commit `0d90cbf` 45 minutes later (hardware.mjs now: "This evaluation uses coordinates only"). |

---

## 2. Module map

### 2.1 Python

| Path | Lines | Responsibility | Imports (project) | Imported by |
|---|---|---|---|---|
| `game_app.py` | 163 | FastAPI app: global `engine`, `speech`, `speech_jobs`; routes `/`, `/api/state`, `/api/pointer/{move,down,drag,up}`, `/api/command`, `/api/reset`, `/api/visual-tick`, `/api/speech`, `/api/speech/cancel`, `/api/speech/voices`, `/api/speech/audio/{key}.wav`; mounts `web/` at `/static` | game_engine, game_speech, speech_queue | `launch_game.py` (uvicorn string `game_app:app`), `tools/audio_integration_lab.py`, `test_speech_api.py` |
| `game_engine.py` | 3465 | `GameEngine(FlowerMixin, NpcMixin, VillageMixin, SeafoodMixin, FishingMixin, KeypadUI, SaveMixin)`; all core + farming/harvest/cooking/shop/mining/research/inventory/minimap/home logic, rendering, input dispatch, state serialization | dotpad, game_saves, game_ui, game_icons, game_fishing, game_seafood, game_village, game_npc, game_flowers, spectator_state | game_app, tools/audio_flow, tools/audio_integration_lab, test_gameplay_audio, test_sound_events, test_speech, test_team_audio, test_support (by file path) |
| `game_flowers.py` | 330 | `FlowerMixin`: houseplant growth, contact watering, `flower_detail` page, flower pot tactile drawing (lines 160-330 are drawing) | — | game_engine |
| `game_village.py` | 229 | `VillageMixin`: Rowan quest state machine, weekly market calendar/pricing, town scene drawing | — | game_engine |
| `game_npc.py` | 85 | `NpcMixin`: activity log + Rowan reactions; wraps `show_rowan` via `super()`; loads `npc_config.json` at import (`NPCS`) | — | game_engine |
| `game_fishing.py` | 117 | `FishingMixin`: lake geometry, cast, rod durability, rod purchase | — | game_engine |
| `game_seafood.py` | 94 | `SeafoodMixin`: fish as cooking ingredients, seafood buffs, loot/sale multipliers used by mining/fishing/shop | — | game_engine |
| `game_ui.py` | 68 | `KeypadUI`: F1/F2 menus (`toggle_menu`), arrow-key navigation; 4 dead draw helpers | — | game_engine |
| `game_saves.py` | 193 | `SaveMixin`: snapshot = `vars(self)` minus `_static_fields`; restore with per-feature migrations; save/load pages | — | game_engine |
| `game_icons.py` | 211 | `IconGrid`, `IconRenderer` (type→symbol; holds engine ref), `IconLayout` (page policy). Contains feature knowledge (`TYPES`, `PAGES`, flower stage patterns, research kinds) | — | game_engine |
| `spectator_state.py` | 58 | `spectator_snapshot(engine, objects)`: public visual payload; reads engine attrs directly | — | game_engine |
| `dotpad.py` | 84 | `DotPad` dot matrix + line/box/triangle raster | — | game_engine (stubbed in test_support) |
| `game_speech.py` | 136 | Piper voice models (`models/piper/*.onnx`), WAV cache `.cache/speech`, `spoken_text()` | — | game_app, test_speech, test_demo_speech, test_speech_api, tools/prepare_demo, tools/prepare_speech, tools/prepare_effects_preview, tools/check_setup (lazy) |
| `speech_queue.py` | 98 | Async single-worker synthesis queue with supersede/priority | — | game_app, test_speech_queue, test_speech_api |
| `launch_game.py` | 139 | Check setup → reuse or spawn uvicorn → optional `tools/prepare_demo.py` → open browser | tools.check_setup | game.bat, start-mac.command, test_startup |
| `build_display.py` | 40 | Concatenate `web/spectator/model.mjs`+`viewer.js` into classic script `display.js` (regex rewrites) | — | manual only |
| `tracking_server.py` | 253 | Camera → hand/ArUco tracking → WebSocket broadcast (port from `tracking_config.json`, fallback 8765) | tracking | tracking_server.bat |
| `tracking_test.py` | 130 | Local OpenCV preview of tracker | tracking | tracking_test.bat |
| `tracking/__init__.py` | 3 | exports `VisionPadTracker` | .core | tracking_server, tracking_test |
| `tracking/core.py` | 504 | `VisionPadTracker` pipeline | .aruco .filters .gesture .hand .mapper; cv2, numpy | tracking/__init__ |
| `tracking/aruco.py` | 187 | ArUco pad detection | cv2, numpy | tracking/core |
| `tracking/hand.py` | 151 | MediaPipe hand landmarks | cv2, mediapipe | tracking/core |
| `tracking/mapper.py` | 222 | Camera→pad homography | cv2, numpy | tracking/core |
| `tracking/gesture.py` | 126 | `PinchGestureDetector` | — | tracking/core |
| `tracking/filters.py` | 31 | `EMAFilter2D` | — | tracking/core |
| `tools/setup_game.py` | 58 | Create `.venv`, pip install, `prepare_speech.py --download`, `check_setup.py --synthesize` | (subprocess) | setup-mac.command, setup-windows.bat, test_startup |
| `tools/check_setup.py` | 133 | Python ≥3.11, package versions, required files, 18 MP3s, voice models, writable dirs | game_speech (lazy, `sys.path` insert) | launch_game, setup_game (subprocess), test_startup |
| `tools/prepare_speech.py` | 101 | Download Piper voices into `models/piper`, build samples | game_speech | setup_game (subprocess) |
| `tools/prepare_demo.py` | 173 | Pre-generate all source-backed speech lines through a running server (default `http://127.0.0.1:8000`) | game_speech, tools.audio_flow, tools.speech_inventory | launch_game `--prepare-demo` (subprocess, passes `--server`), test_demo_speech |
| `tools/audio_flow.py` | 175 | Scripted full-game input run on temp saves; `--stdout` JSON | game_engine | test_audio_flow, test_audio_integration.cjs (subprocess), tools/prepare_demo, tools/audio_integration_lab |
| `tools/audio_integration_lab.py` | 60 | Isolated browser lab on port 8001 | game_app, game_engine, tools.audio_flow; uvicorn, fastapi | manual |
| `tools/prepare_effects_preview.py` | 84 | Effects listening reel (needs numpy, FFmpeg, Node) | game_speech | manual |
| `tools/speech_inventory.py` | 46 | AST scan of speech strings | — | tools/prepare_demo |
| `test_*.py` | — | see §1 | — | — |

All `tools/*.py` use `sys.path.insert(0, ROOT)` (`audio_flow.py:12`, `audio_integration_lab.py:8`, `check_setup.py:93`, `prepare_demo.py:14`, `prepare_effects_preview.py:11`, `prepare_speech.py:12`); no package structure.

### 2.2 Web

| Path | Lines | Responsibility | Loads / imports | Loaded by |
|---|---|---|---|---|
| `web/game.html` | 735 | Whole client: CSS (3-22), markup (22-45), one inline script (46-735) | `/static/game-audio.js`, `game-speech.js`, `game-keys.js`, module `hardware.mjs`, classic `spectator/display.js` | `game_app.py` `/` |
| `web/game-audio.js` | 617 | `GameAudio`, `SOUND_CUES`; BGM, task loops, spatial HRTF, fishing sonar, target guidance | `/static/audio/*.mp3` (list at line 56) | game.html; test_*.cjs (CommonJS guard line 617) |
| `web/game-speech.js` | 200 | `GameSpeech`: fetch `/api/speech`, cancel, replay, hover deferral | — | game.html; test_speech.cjs |
| `web/game-keys.js` | 41 | `GameKeys`: F1-F4/arrows, F3 short=load / long=save | — | game.html; test_hardware.mjs |
| `web/hardware.mjs` | 202 | Web Serial `SerialPad` (USB), lazy Bluetooth button wiring, hand-tracking WebSocket client | dynamic `import('./bluetooth-pad.mjs')` (line 148) | game.html (module) |
| `web/bluetooth-pad.mjs` | 114 | `BluetoothPad` on DotPadSDK; `packCells`, `cellsToHex`, `forwardKey` (duplicates of hardware.mjs exports) | `./vendor/DotPadSDK-3.0.3.js` (absent) | hardware.mjs (dynamic) |
| `web/vendor/package.json` | 1 | `{"type":"module"}` for the manually downloaded SDK | — | — |
| `web/spectator/model.mjs` | 169 | Pure state→visual-layout transforms (`WORLD`, `SCENES`, `TITLES`, `SPRITES`, `plots`, `publicCards`, `snapshot`) | — | viewer.js |
| `web/spectator/viewer.js` | 727 | Canvas renderer of companion window; fetches `scene-objects.json`, `visual-assets.json` | ./model.mjs | demo.html, boot.js |
| `web/spectator/display.js` | 871 | **Generated** by `build_display.py` from model.mjs+viewer.js, but hand-edited: a fresh build differs in 119 lines (both directions: bundle has edits absent from sources, sources have 2026-10-22 edits absent from bundle). Regenerating will lose bundle-only edits. | — | game.html:735, standalone.html |
| `web/spectator/standalone.html` | 11 | Companion popup page | ./display.js | opened by display.js `window.open` |
| `web/spectator/demo.html` | 45 | Fixture preview | ./viewer.js, fixtures.json | manual |
| `web/spectator/boot.js` | 28 | Mount helper | ./viewer.js | **nothing** (orphan) |
| `web/spectator/{scene-objects,visual-assets,fixtures}.json` | — | Scene registry, texture/sprite registry, demo fixtures | — | viewer.js / display.js / demo.html |

### 2.3 game_engine.py method groups (line ranges; groups are interleaved in the file)

| Group | Methods (lines) | Total lines |
|---|---|---|
| core/state | `__init__` 21-57, `prepare_display_config` 60-102, `compact_objects` 104-116, `reset` 118-215, `clear_hover` 226-229, `has_final_consonant` 262-268, `josa` 270-271, `ro_particle` 273-280, `get_page_name` 282-286, `get_layout_objects` 516-568, `get_objects` 570-571, `handle_command` 3112-3134, `resource_summary_text` 3136-3140, `response` 3142-3144, `audio_guidance` 3146-3162, `get_state` 3164-3260, `item_destroyed_event` 3320-3325 | 423 |
| time & sleep | `get_action_cost` 306-312, `get_time_cells` 314-315, `time_text` 317-322, `consume_time` 351-368, `enter_night` 370-382, `night_response` 384-388, `next_day` 390-400, `finish_sleep` 402-440, `lower_panel_state` 442-457, `draw_time_bar` 459-487, `night_only_response` 2291-2292 | 148 |
| rendering primitives | `compress_axis` 1137-1162, `spatial_objects` 1164-1176, `back_arrow` 1485-1490, `get_relative_direction` 1500-1511, `render` 1513-1603, `draw_triangle` 1605-1614, `draw_bed` 1616-1617, `draw_chest` 1619-1620, `draw_stove` 1622-1623, `draw_filled_square` 1663-1666, `draw_icon_pattern` 1674-1681, `defer_visual_completion` 1766-1771, `visual_tick` 1773-1786, `point_to_segment_distance` 1827-1834, `object_contains` 1836-1845, `find_object` 1847-1860, `build_path_samples` 2901-2913 | 241 |
| input dispatch & navigation | `get_location_detail` 1868-1894, `get_object_tts` 1896-1948, `get_hover_sfx` 1950-1964, `move_minigame` 1966-2001, `pointer_move` 2003-2035, `pointer_down` 2037-2100, `pointer_drag` 2102-2156, `pointer_up` 2158-2198, `perform_action` 2200-2206, `_perform_action` 2208-2289, `travel_to` 2294-2326, `navigate_key` 2361-2375, `return_to_scene` 2377-2389 | 474 |
| home | `get_home_objects` 573-591, `flower_scene_bounds` 593-602, `home_spatial_objects` 604-629, `draw_home_scene` 631-758 | 183 |
| farming/plots/care | `new_plot_state` 217-224, `clear_care` 231-240, `get_seed_config` 288-289, `get_seed_label` 291-292, `get_plot_label` 300-304, `get_unlocked_plot_defs` 489-490, `get_farm_objects` 760-798, `draw_plot` 800-888, `get_plot_detail_objects` 890-991, `get_care_minigame_objects` 993-1022, `get_seed_select_objects` 1045-1068, `plot_bounds` 1626-1628, `draw_plot_progress` 1630-1637, `draw_watering_can` 1639-1640, `draw_fertilizer` 1642-1643, `draw_seed` 1645-1646, `draw_crop_symbol` 1648-1658, `draw_plot_detail_field` 1689-1707, `draw_plot_detail_gauge` 1709-1728, `draw_care_button` 1730-1731, `draw_care_target` 1733-1745, `find_farm_plot_at` 1862-1866, `plot_status_text` 2391-2404, `open_plot_detail` 2406-2418, `start_care_minigame` 2420-2457, `collect_care_point` 2459-2467, `collect_care_segment` 2469-2479, `finish_care_minigame` 2481-2529, `open_seed_select` 2531-2546, `plant_seed` 2548-2570, `water_plot` 2572-2588, `apply_fertilizer_bonus` 2590-2600, `fertilize_plot` 2602-2624, `get_effective_seed_return_chance` 2626-2631 | 630 |
| harvest | `clear_harvest` 242-246, `get_harvest_objects` 1271-1296, `draw_harvest_crop` 1747-1750, `start_harvest_minigame` 2684-2700, `collect_harvest_point` 2702-2708, `collect_harvest_segment` 2710-2718, `finish_harvest_minigame` 2720-2767, `get_harvest_base_yield` 3381-3382 | 118 |
| cooking (+ food buffs) | `clear_cooking` 248-260, `get_recipe_config` 294-295, `get_recipe_label` 297-298, `recipe_effect_text` 324-327, `buff_multiplier_for` 329-332, `buff_text` 334-341, `tick_buff` 343-349, `can_craft_recipe` 492-502, `get_recipe_select_objects` 1298-1313, `get_ingredient_select_objects` 1315-1338, `get_cooking_objects` 1340-1341, `recipe_ingredient_text` 1492-1498, `draw_recipe_icon` 1683-1684, `draw_recipe` 1752-1753, `draw_ingredient` 1755-1756, `draw_cooking_start` 1758-1759, `cooking_resume_point` 1761-1764, `update_cooking_marker` 1788-1794, `draw_cooking_path` 1796-1816, `open_recipes` 2769-2781, `select_recipe` 2783-2791, `toggle_ingredient` 2793-2813, `get_cooking_steps` 2815-2820, `get_scaled_cooking_gesture` 2822-2838, `get_cooking_gesture` 2840-2848, `get_cooking_kind` 2850-2851, `get_cooking_stage_label` 2853-2854, `cooking_step_text` 2856-2858, `complete_cooking_step` 2860-2875, `open_cooking_minigame` 2877-2899, `start_cooking_trace` 2915-2932, `advance_cooking_trace` 2934-2961, `fail_or_continue_cooking` 2963-2969, `finish_cooking_success` 2971-2996, `use_food` 2998-3015 | 358 |
| research | `get_research_objects` 1205-1269, `draw_research` 1686-1687, `open_research` 2353-2359, `buy_research` 2633-2682, `buy_mineral_research` 3431-3454 | 148 |
| shop/village trade | `get_food_sell_price` 504-514, `get_town_objects` 1024-1026, `get_shop_choice_objects` 1343-1361, `shop_choice_spatial_objects` 1363-1380, `draw_shop_choice_scene` 1382-1460, `get_shop_buy_objects` 1462-1472, `get_shop_sell_objects` 1474-1483, `draw_shop_npc` 1818-1819, `draw_shop_choice` 1821-1822, `draw_shop_item` 1824-1825, `open_shop` 3017-3025, `return_to_shop_choice` 3027-3032, `open_shop_mode` 3034-3044, `buy_shop_item` 3046-3075, `sell_shop_item` 3077-3110, `get_fertilizer_price` 3264-3266, `get_pickaxe_price` 3268-3269, `build_shop_objects` 3384-3407 | 276 |
| mining | `get_mine_objects` 1028-1043, `draw_resource` 1660-1661, `MINERAL_LABELS` 3262, `get_mineral_price` 3271-3278, `regenerate_mine` 3280-3304, `draw_mine_rock` 3306-3318, `hit_mine_rock` 3327-3379, `buy_mine_item` 3409-3429, `draw_mine_item` 3456-3466 | 149 |
| inventory | `get_inventory_objects` 1070-1134, `open_inventory` 2340-2351 | 77 |
| minimap | `get_minimap_objects` 1178-1203, `draw_node` 1668-1672, `open_minimap` 2328-2338 | 42 |
| save/load hooks | none in engine; all in `game_saves.py`. Engine hooks: `_static_fields` captured at `__init__` line 55; `get_load_objects` registered in page table line 520; `save_game`/`toggle_menu("load_game")` in `handle_command` 3117-3118; `close_load`/`load_slot:` in `_perform_action` 2221-2222 | — |

### 2.4 Dead / unreachable code (verified by reference search over non-test Python)

- Never called: `josa` 270, `ro_particle` 273 (+ `has_final_consonant` 262, only used by josa; Korean particle helpers), `resource_summary_text` 3136, `draw_plot_progress` 1630, `draw_crop_symbol` 1648, `plot_status_text` 2391, `draw_recipe_icon` 1683, `time_text` 317, `draw_mine_item` 3456, `spatial_objects` 1164, `open_minimap` 2328 (F1 uses `toggle_menu`), `game_ui.py` `draw_item_frame` 57, `draw_category` 60, `draw_catalog_item` 64, `draw_facility` 67.
- Unreachable pages (no code sets `current_page` to them): `npc_dialogue` (`get_dialogue_objects` game_npc.py:69-77; `self.dialogue` is only ever set to `None`), `rowan_dialogue` (`show_rowan` sets `town`/`rowan_submit` only), `shop_calendar` (`open_calendar` only speaks). They remain in the page table (game_engine.py:527, 543-545), `game_config.json.pages`, `IconLayout.PAGES`, `visual-assets.json.pages`, `model.mjs TITLES`, and save migrations (game_saves.py:88-95).
- `paused`: only ever set `False` (reset, `open_load_game`) in production code (F4 now maps to `click`, game_engine.py:3115); still read in 21 places (game_engine 13, game_fishing 2, game_flowers 2, game_ui 2, game_npc 1, game_saves 1) and tests set it directly.
- `web/spectator/boot.js` unused; `test_support.py` unused.
- Unused config keys: `care_minigame.success_ratio` (comment game_engine.py:2490-2491 says ignored), `cooking_methods.preparation_methods`, `.finishing_methods`, `.planned_preparation_methods`, `tracking_config.debug.draw_camera`.

---

## 3. Coupling analysis

### 3.1 Per-feature self.* access (static AST; engine groups as in §2.3, mixins by file)

Attributes are listed once: `W` (written, implies read) and `R` (read-only). `core` writes every attribute initialized in `reset()`/`__init__`; those are omitted from other rows only when the feature does not touch them.

**flowers** (`game_flowers.py`)
- W: `current_page, flower_contact_at, flower_seeds, flower_watering, houseplant, last_pointer, resources`
- R: `config, day_ended, dotpad, paused, sleep_until`
- ->: core(`clear_hover, response`), render(`back_arrow, render`), time(`night_only_response`)

**npc** (`game_npc.py`)
- W: `activity_counts, activity_history_complete, activity_serial, dialogue, npc_reactions, npc_visits, recent_activity`
- R: `current_location, current_page, day, day_ended, farm_plots, paused, resources, rowan_dialogue, sleep_until`
- ->: core(`response`), render(`back_arrow`), village(`talk_rowan`); `show_rowan` calls `super().show_rowan` → VillageMixin (MRO-dependent)

**village** (`game_village.py`)
- W: `current_page, hover_object_id, resources, rowan_dialogue, rowan_greeted, rowan_stage, rowan_submit_open`
- R: `config, current_location, day, dotpad, icons`
- ->: core(`clear_hover, response`), farming(`get_seed_label`), npc(`next_rowan_advice, rowan_advice, show_rowan`), render(`back_arrow, draw_icon_pattern, render`), seafood(`sale_price`)

**fishing** (`game_fishing.py`)
- W: `fishing_attempts, fishing_last_catch, fishing_target, resources, rod_casts, rod_catches`
- R: `config, current_page, day_ended, dotpad, paused, sleep_until`
- ->: core(`clear_hover, item_destroyed_event, response`), npc(`record_activity`), render(`back_arrow, render`), seafood(`boost_rare_weights, get_rod_price, loot_amount`), time(`consume_time, night_only_response, night_response`), village(`market_price`)

**seafood** (`game_seafood.py`)
- W: `active_buff, current_location, current_page, pointer_pressed, resources, selected_ingredients`
- R: `selected_recipe_id`
- ->: cooking(`clear_cooking, get_recipe_config, open_cooking_minigame`), core(`clear_hover, response`), fishing(`fishing_config`), mining(`get_mineral_price`), npc(`record_activity`), render(`render`), time(`consume_time, night_response`)

**keypad_ui** (`game_ui.py`)
- W: `_menu_stack, care_dragging, cooking_dragging, current_page, drag_tool, harvest_dragging, inventory_page, pending_visual_completion, pointer_pressed`
- R: `current_location, day_ended, icons, paused, resources, sleep_until`
- ->: core(`clear_hover, get_layout_objects, get_page_name, response`), flowers(`stop_flower_contact`), input(`perform_action, return_to_scene`), render(`render`), saves(`close_load_game, open_load_game`), time(`night_only_response`)

**saves** (`game_saves.py`)
- W: `__dict__` (bulk), `_load_return, _menu_stack, _save_slots, care_dragging, cooking_dragging, current_page, day_ended, drag_tool, harvest_dragging, paused, pending_visual_completion, pointer_pressed, sleep_until`
- R: `_static_fields, config, day, save_dir`; plus by name in `snapshot`/`restore_snapshot`: `flower_contact_at, flower_watering, sleep_until, cooking_last_progress_at, care_visible_until, cooking_visible_until, pending_visual_completion, hover_object_id, fishing_*, rod_*, rowan_*, npc_visits, dialogue, activity_*, recent_activity, npc_reactions, resources.fishing_rod, resources.fish, resources.foods.fried_fish_*, active_buff, flower_seeds, houseplant`
- ->: core(`clear_hover, get_page_name, response`), input(`return_to_scene`), render(`back_arrow, render`)

**time_sleep**
- W: `current_location, current_page, day, day_ended, drag_target_ids, drag_tool, fishing_last_catch, pointer_pressed, seed_select_plot_id, sleep_until, time_used_cells, timepad`
- R: `active_buff, config, farm_plots, inventory_page, inventory_page_count, shop_page, shop_page_count, sleep_blackout_seconds, time_total_cells`
- ->: cooking(`buff_multiplier_for, clear_cooking, tick_buff`), farming(`clear_care, get_seed_config, get_seed_label`), fishing(`new_fishing_target`), flowers(`advance_flowers`), harvest(`clear_harvest`), mining(`regenerate_mine`), core, render

**farming**
- W: `care_collected_ids, care_dragging, care_mode, care_targets, care_visible_until, current_location, current_page, detail_plot_id, farm_plots, last_pointer, pending_visual_completion, resources, seed_select_plot_id`
- R: `config, day_ended, disappear_delay_seconds, dotpad, icons, research_levels, unlocked_plot_count`
- ->: harvest(`clear_harvest, get_harvest_base_yield`), input(`return_to_scene`), time(`consume_time, night_only_response, night_response`), render(`back_arrow, defer_visual_completion, draw_icon_pattern, object_contains, point_to_segment_distance, render`), core

**harvest**
- W: `current_location, current_page, detail_plot_id, farm_plots, harvest_collected_ids, harvest_dragging, harvest_plot_id, harvest_targets, last_pointer, resources`
- R: `config, dotpad`
- ->: cooking(`buff_multiplier_for`), farming(`get_effective_seed_return_chance, get_seed_config, get_seed_label, new_plot_state`), flowers(`flower_harvest_bonus`), input(`return_to_scene`), npc(`record_activity`), seafood(`loot_amount`), time(`consume_time, night_response`), core, render

**cooking**
- W: `active_buff, cooking_dragging, cooking_last_progress_at, cooking_path_samples, cooking_progress_index, cooking_resume_marker, cooking_stage_index, cooking_visible_until, current_location, current_page, last_pointer, pending_visual_completion, pointer_pressed, resources, selected_ingredients, selected_recipe_id`
- R: `config, day_ended, disappear_delay_seconds, dotpad, icon_layout, icons, paused, resume_marker_delay_seconds, stir_scale`
- ->: farming(`get_seed_label`), npc(`record_activity`), seafood(`finish_seafood, loot_amount, seafood_ingredient_objects, seafood_ready, selected_fish, toggle_fish`), time(`consume_time, night_only_response, night_response`), render(`back_arrow, build_path_samples, defer_visual_completion, draw_filled_square, draw_icon_pattern, point_to_segment_distance, render`), core

**research**
- W: `current_page, research_levels, resources, unlocked_plot_count`
- R: `MINERAL_LABELS, config, day_ended, icons`
- ->: time(`consume_time, night_only_response, night_response`), core, render

**shop**
- W: `current_location, current_page, resources, rowan_dialogue, rowan_submit_open, shop_page, shop_page_count`
- R: `MINERAL_LABELS, config, dotpad, flower_seeds, icons`
- ->: cooking(`get_recipe_config, get_recipe_label`), farming(`get_seed_config, get_seed_label`), fishing(`buy_fishing_rod, fishing_config`), flowers(`buy_flower_seed, flower_config`), mining(`buy_mine_item, get_mineral_price`), seafood(`consume_sale, get_fish_price, get_rod_price`), village(`market_price, rowan_object, town_nav_objects, town_spatial_objects`), core, render

**mining**
- W: `_pickaxe_hits, hover_object_id, mine_rocks, resources`
- R: `MINERAL_LABELS, config, current_page, day, day_ended, dotpad, icons, paused, research_levels`
- ->: cooking(`buff_multiplier_for`), npc(`record_activity`), seafood(`boost_rare_weights, loot_amount`), shop(`get_pickaxe_price`), time(`consume_time`), village(`market_price`), core(`item_destroyed_event`), render

**inventory**
- W: `current_page, inventory_page, inventory_page_count, seed_select_plot_id`
- R: `config, day_ended, flower_seeds, inventory_hide_zero_items, inventory_items_per_page, resources`
- ->: cooking(`clear_cooking, recipe_effect_text`), farming(`clear_care`), fishing(`fishing_config`), harvest(`clear_harvest`), time(`night_only_response`), core, render

**minimap**
- W: `current_page, seed_select_plot_id`
- R: `config, current_location, day_ended, dotpad`
- ->: cooking(`clear_cooking`), farming(`clear_care`), harvest(`clear_harvest`), time(`night_only_response`), render(`compress_axis, draw_filled_square, get_relative_direction, render`), core

**home**
- W: —
- R: `config, day_ended, dotpad, houseplant`
- ->: cooking(`can_craft_recipe`), flowers(`flower_description, flower_object`), render(`draw_icon_pattern`)

**input dispatch & navigation**
- W: `_menu_stack, care_dragging, cooking_dragging, current_location, current_page, drag_target_ids, drag_tool, harvest_dragging, hover_object_id, inventory_page, last_hover_state, last_pointer, location_detail_spoken, pointer_pressed, rowan_dialogue, rowan_greeted, rowan_submit_open, seed_select_plot_id, shop_page`
- R: `care_collected_ids, care_mode, care_targets, cooking_path_samples, cooking_progress_index, day_ended, detail_plot_id, farm_plots, flower_watering, harvest_collected_ids, harvest_targets, inventory_page_count, paused, pending_visual_completion, resources, sleep_until`
- ->: every feature (cooking 10 methods, farming 13, harvest 5, shop 5, village 4, flowers 3, research 2, saves 2, fishing/mining/npc/inventory 1 each, time 4)

**rendering primitives**
- W: `dotpad, pending_visual_completion, timepad`
- R: `current_page, icons, paused, sleep_until`
- ->: draw methods of farming(8), cooking(4), shop(4), village(3), mining(2), fishing(`draw_lake`), flowers(`draw_flower_pot`), harvest, home, minimap, research, time(`draw_time_bar`); `visual_tick` 1773-1786 calls feature completions `finish_care_minigame`, `complete_cooking_step`, `finish_sleep`

**core/state**
- W: all attributes initialized in `__init__` 21-57 and `reset` 118-215
- ->: every feature (page getters, `reset_*`, `*_public_state`, cooking state for `get_state`)

**Outside the class, reading engine internals directly**
- `spectator_state.py`: `care_collected_ids, care_targets, care_visible_until, config, cooking_path_samples, cooking_progress_index, cooking_visible_until, farm_plots, get_recipe_config, get_seed_label, get_unlocked_plot_defs, harvest_collected_ids, harvest_targets, mine_rocks, recipe_effect_text, resources`
- `game_icons.IconRenderer`: `engine.dotpad, engine.draw_icon_pattern, engine.houseplant`
- `tools/audio_flow.py`: `care_targets, config, cooking_stage_index, current_page, day, farm_plots, fishing_target, get_cooking_gesture, get_objects, get_unlocked_plot_defs, handle_command, harvest_targets, list_saves, mine_rocks, resources, response, sleep_blackout_seconds, visual_tick`
- Tests (`test_gameplay_audio`, `test_sound_events`, `test_speech`, `test_team_audio`) read/write engine attributes directly (`resources`, `farm_plots`, `paused`, `rowan_stage`, `time_used_cells`, ...). Attribute renames break them.

### 3.2 Dependency matrix (feature → features it calls; core/render/time omitted unless notable)

| Feature | Depends on |
|---|---|
| flowers | time |
| npc | village |
| village | npc, farming, seafood |
| research | time |
| minimap | farming, harvest, cooking (clear_* only), time |
| inventory | farming, harvest, cooking, fishing, time |
| home | flowers, cooking |
| fishing | seafood, npc, village, time |
| mining | seafood, cooking, npc, shop, village, time |
| seafood | cooking, fishing, mining, npc, time |
| harvest | farming, cooking, flowers, npc, seafood, time, input |
| cooking | seafood, farming, npc, time |
| farming | harvest, time, input |
| shop | cooking, farming, fishing, flowers, mining, seafood, village |
| time_sleep | cooking, farming, fishing, flowers, harvest, mining |
| keypad_ui | flowers, saves, input |
| saves | input (+ by-name knowledge of fishing, npc, village, flowers, cooking, seafood state) |
| input | all |
| render | all draw methods |
| core | all |

Cycles: `npc ↔ village`; `seafood ↔ cooking`; `seafood ↔ fishing`; `seafood ↔ mining`; `farming ↔ harvest`; `mining ↔ shop`; `time ↔ {cooking, farming, fishing, flowers, harvest, mining}`.

### 3.3 Shared mutable state written by more than one feature (excluding core init)

| Attribute | Writers | Read-only by |
|---|---|---|
| `resources` | cooking, farming, fishing, flowers, harvest, mining, research, seafood, shop, village | input, inventory, keypad_ui, npc, spectator_state |
| `current_page` | cooking, farming, flowers, harvest, input, inventory, keypad_ui, minimap, research, saves, seafood, shop, time, village | fishing, mining, npc, render |
| `current_location` | cooking, farming, harvest, input, seafood, shop, time | keypad_ui, minimap, npc, village |
| `pointer_pressed` | cooking, input, keypad_ui, saves, seafood, time | — |
| `pending_visual_completion` | cooking, farming, keypad_ui, render, saves | input |
| `last_pointer` | cooking, farming, flowers, harvest, input | — |
| `seed_select_plot_id` | farming, input, inventory, minimap, time | — |
| `drag_tool` | input, keypad_ui, saves, time | — |
| `care_dragging` / `harvest_dragging` / `cooking_dragging` | owner feature + input, keypad_ui, saves | — |
| `_menu_stack` | input, keypad_ui, saves | — |
| `hover_object_id` | input, mining, village | — |
| `inventory_page` | input, inventory, keypad_ui | time |
| `shop_page` | input, shop | time |
| `active_buff` | cooking, seafood | time |
| `selected_ingredients` | cooking, seafood | — |
| `farm_plots` | farming, harvest | input, npc, time, spectator_state |
| `detail_plot_id` | farming, harvest | input |
| `rowan_dialogue`, `rowan_submit_open` | input (`travel_to` 2301-2302), shop, village | npc, core |
| `rowan_greeted` | input (`travel_to` 2324), village | — |
| `fishing_last_catch` | fishing, time | — |
| `day_ended`, `sleep_until` | time, saves | ~12 features |
| `drag_target_ids`, `timepad` | input/time, render/time | — |

Pattern: "leave page" cleanup is duplicated. `clear_care(); clear_harvest(); clear_cooking(); clear_hover()` appears in `travel_to` 2307-2310, `open_minimap` 2332-2335, `open_inventory` 2345-2348, `return_to_scene` 2382-2385. `pointer_pressed = care_dragging = harvest_dragging = cooking_dragging = False; drag_tool = None` appears in `game_ui.py:22-23, 49-50`, `handle_command` 3122-3123, `pointer_up` 2171-2172, `save_game` (game_saves.py:150-152).

### 3.4 Dispatch points every feature must touch today (merge-conflict hotspots)

| # | Hotspot | Location | What a new feature adds |
|---|---|---|---|
| 1 | Page → object getter table | `get_layout_objects` game_engine.py:519-545 | one entry per page |
| 2 | Page display names | `prepare_display_config` 73-79, `get_page_name` 282-286 | name |
| 3 | Object type → draw `if/elif` chain | `render` 1513-1603 (40 branches) + page scene overlays 1590-1602 | branch per type / per page |
| 4 | Action prefix `if` chain | `_perform_action` 2208-2289 (~40 prefixes, order-sensitive; night guard at 2223) | prefix |
| 5 | Pointer handlers' page special-cases | `pointer_move` 2003-2035, `pointer_down` 2037-2100, `pointer_drag` 2102-2156, `pointer_up` 2158-2198, `move_minigame` 1966-2001 (hardcoded page tuples `water_minigame, fertilizer_minigame, harvest, cooking`, `flower_detail`, `fishing`, `mine`) | page branch |
| 6 | Hover TTS / hover SFX | `get_object_tts` 1896-1948, `get_hover_sfx` 1950-1964 | type branch / mapping |
| 7 | State payload | `get_state` 3164-3260 (feature blocks: `fishing`, `flowers`, `calendar`, `dialogue`, `rowan_submission`, `care`, `harvest`, `cooking`, `inventory`, `action_costs`) | key |
| 8 | Audio guidance | `audio_guidance` 3146-3162 | page branch |
| 9 | Reset | `reset` 118-215 (`reset_village` first, `regenerate_mine/reset_fishing/reset_npcs/reset_flowers` at 210-213) | init call / attributes |
| 10 | Day advance | `next_day` 390-400, `finish_sleep` 402-440, `enter_night` 370-382 | daily tick |
| 11 | Page exit cleanup | `travel_to` 2294-2326, `return_to_scene` 2377-2389, `open_inventory`, `toggle_menu` (game_ui.py:7-28) | clear_* call |
| 12 | Save format | `snapshot` = `vars(self)` minus `_static_fields` (game_saves.py:35-54); `restore_snapshot` (56-121) hard-fails if key set differs from a fresh engine and contains per-feature migrations at 66-98 | any new attribute = save schema change + migration line |
| 13 | Icon policy | `IconRenderer.TYPES` game_icons.py:46-49, `spec` 125-149, `IconLayout.PAGES` 191-193, home/town order 204-209 | type / page |
| 14 | Shop catalog | `build_shop_objects` 3384-3407, `buy_shop_item` 3046-3075, `sell_shop_item` 3077-3110 (fish, flowers, rod, minerals, pickaxe all branch here) | item kind |
| 15 | Spectator payload | `spectator_state.py:6-58` | feature fields |
| 16 | Frontend | game.html tasks dict line 304 + per-page status 306-312, `updateStatus` 130-160; `game-audio.js` `backgroundFor` 412-417, `syncFishing` 490-530, guidance 560-616; `model.mjs TITLES/SPRITES`; `viewer.js` per-scene functions (`farm` 145, `mine` 182, `fishing` 204, `flowerDetail` 715, `menus` 514); `visual-assets.json.pages`; `game_config.json.pages` | per-feature UI |
| 17 | `check_setup.py` required-files list 41-45 | omits `game_village.py`, `game_icons.py` (both imported by game_engine) — a copy missing them passes setup check and crashes at import | file names |

MRO-sensitive overrides: `navigate_key` (game_engine.py:2361 → `super()` game_ui.py:39); `show_rowan` (game_npc.py:37 → `super()` game_village.py:170). Base order `FlowerMixin, NpcMixin, VillageMixin, SeafoodMixin, FishingMixin, KeypadUI, SaveMixin` must be preserved or these chains change.

---

## 4. Config and asset ownership

### 4.1 game_config.json (top-level key → reader)

| Key | Reader (file:line) | Feature |
|---|---|---|
| `dotpad` | game_engine.py:40, 2832; game_app (state), game.html, boot.js | core/render |
| `game.start_day` | game_engine.py:130 | core |
| `time` (`total_cells, action_costs, bar`) | game_engine.py:46, 207-208, 311, 481 | time |
| `resources` (starting stock) | game_engine.py:136-149; game_fishing.py:11-12; tools/audio_flow.py:18 | core (per-item: farming/mining/fishing) |
| `pages.*` (labels/tts per page) | game_engine.py:84, 286 | core; includes unreachable `rowan_dialogue, shop_calendar` |
| `fertilizer` (`growth_day_bonus, price`) | game_engine.py:141, 2592, 3265 | farming/shop |
| `shop.fertilizer_price` | game_engine.py:3266 (fallback) | shop |
| `research` (`seed_return, field_expansion, mineral_luck`) | game_engine.py:158, 1208, 1228, 1248, 1257, 2627, 2637, 2660, 3344, 3434 | research (consumed by farming, mining) |
| `seeds` | game_engine.py:85, 142, 151, 289, 1049, 1079-1081, 1465, 1476, 3272; game_village.py:192, 207, 219; spectator_state.py:37 | farming (shared by harvest, cooking, shop, village, inventory) |
| `recipes` (incl. seafood `quality_effects` expanded into `_low/_medium/_high` variants at load, 60-82) | game_engine.py:64-87, 155, 295, 583, 610, 1083, 1299, 1478, 2772; game_saves.py (via `get_recipe_config`) | cooking (+seafood) |
| `home.objects` | game_engine.py:575 | home |
| `farm` (`plots, objects`) | game_engine.py:95, 164, 301, 490, 761, 1229, 2661 | farming |
| `town.objects` | game_engine.py:1025 | shop/village |
| `minimap` (`locations, routes`) | game_engine.py:1179 | minimap |
| `care_minigame` | game_engine.py:1000, 2437, 2461, 2471 (`success_ratio` unused) | farming |
| `harvest_minigame` | game_engine.py:1278, 2688 | harvest |
| `interaction` (`feedback, cooking, inventory, audio, sleep`) | game_engine.py:24-37 (`audio` forwarded to client as `client_settings.audio` → game-audio.js `configure`) ; tools/prepare_effects_preview.py | cross-cutting |
| `mine` | game_engine.py:3269, 3275, 3281, 3310, 3336; tools/audio_flow.py:137 | mining (`pickaxe_price_multiplier` used by shop) |
| `fishing` | game_fishing.py:8 (`fishing_config`), read via it by seafood, shop, inventory | fishing/seafood |
| `cooking_methods` (`gestures` used; `preparation_methods, finishing_methods, planned_preparation_methods` unused) | game_engine.py:2819 | cooking |
| `rowan` (`seed_gift_each, vegetable_reward_gold`) | game_village.py:184, 222, 224; test_team_audio | village |
| `weekly_market` | game_village.py:15, 21, 28 | village (prices used by shop, mining, fishing) |
| `flowers` | game_flowers.py:8 (`flower_config`; `sprout_days`/`stem_days` read dynamically at 128 as `stage+'_days'`) | flowers (seed price used by shop) |

### 4.2 Other configs

- `npc_config.json` (`shopkeeper.{name, role, voice_profile, greeting, return_greeting, goodbye, reactions.*, farming.*, fishing.*}`): loaded at import `game_npc.py:5`; used `recent_reaction` 25-35 (`reactions`), `show_rowan` 42 (`voice_profile`), `rowan_advice` 54-62 (`farming`, `fishing`). `greeting/return_greeting/goodbye` are only used by tests/tools (`test_demo_speech.py:44`, `tools/prepare_demo.py`) since topic dialogue is gone.
- `speech_config.json` (`language, pronunciation_version, profiles.{system,shopkeeper}, samples`): `game_speech.py:78-120`; `tools/check_setup.py:56-97`; `tools/prepare_demo.py:37`; `tools/prepare_speech.py:84`.
- `tracking_config.json` (`camera, aruco, pad, calibration, hand, gesture, smoothing, websocket, debug`): `tracking_server.py:28-65`, `tracking_test.py:23-60`, `tracking/core.py:19-32` → sub-objects passed to `aruco.py`, `mapper.py`, `hand.py`, `gesture.py`, `filters.py`. `debug.draw_camera` unused. `websocket.port`=8765 must match `game.html` default `ws://127.0.0.1:8765`.

### 4.3 Assets by feature

Audio (`web/audio/`, 18 MP3, 4.2 MB total; list hardcoded in `game-audio.js:56` and `tools/check_setup.py:13-15`; meaning per sound in `docs/audio/SOUND_MAP.md`):

| Feature | Files (bytes) |
|---|---|
| shared BGM | background-basic 1,413,538; background-minigame 570,096; background-shop 280,032 |
| farming care | water 487,680; soil 202,292 |
| harvest | crop 15,046 |
| cooking | cut 10,560; cook 670,406 |
| mining | pickaxe 37,632; break 16,718; shine 132,096; destroy 38,400 (also tool break) |
| fishing | splash 97,802 |
| shop | coin 20,062 |
| navigation | door 42,364; step 13,374 |
| time | sleep 145,449 |
| shared result | correct 10,560 |

Images (`web/spectator/assets/`, 12 PNG, 21.0 MB total; registry `visual-assets.json.textures`):

| Texture | Bytes | Entries | Feature |
|---|---|---|---|
| scenes.png | 3,697,944 | bg home, farm, town, mine | core scenes |
| scenes2.png | 2,562,871 | bg soil, shop, room, square | farming/shop/home |
| scene3.png | 2,995,323 | bg fishing, kitchen | fishing, cooking |
| facilities.png | 2,048,807 | bed, research, kitchen, store, merchant, counter | home/research/shop |
| items.png | 1,800,828 | 28 objs: crops, seeds, minerals, pickaxe, vegetable dishes, plant stages, research icons | farming/mining/cooking/research |
| items2.png | 1,353,380 | 19 objs: 8 fish + 11 fish dish variants | fishing/seafood |
| items3.png | 1,046,976 | fishing_rod, calendar, shop_calendar, + 7 unused-looking items (bird, coffee_beans, coffee, scissors, animal_feed, kitchen_knife, bug_net) | fishing/village |
| rowan.png | 1,074,851 | rowan, rowan_portrait, fishing_rod_equipped | village/fishing |
| extras.png | 1,020,042 | 1 obj: wood | (wood resource) |
| flower-backgrounds.png | 1,581,977 | 4 flower stage bgs | flowers |
| flower-items.png | 1,656,929 | 5 flower seeds + flower_empty | flowers |
| flower-stages.png | 760,897 | 4 stages | flowers |

`.git` is 57 MB; PNGs are committed directly (no LFS).

---

## 5. Frontend structure

### 5.1 `web/game.html` (735 lines, single file)

| Lines | Content |
|---|---|
| 3-22 | Inline CSS |
| 22-45 | Markup: dot canvas `#dotpad`, `#timepad`, status cards, speech/sound controls, object list, hardware card line 44 (`#usb-button`, `#ble-button`, `#tracking-*`), diagnostics/reset |
| 45 | Script tags: game-audio.js, game-speech.js, game-keys.js |
| 46-89 | DOM handles, global mutable state (`currentState`, pointer vars, `flowerMouseInside`), `new GameAudio`, `new GameSpeech`, `new GameKeys` |
| 90-129 | `announce`, `connection`, speech unlock/`speak`, `eventToLogical` |
| 130-160 | `updateStatus` — debug panel; reads `care`, `harvest`, `cooking`, `active_buff` |
| 161-254 | `drawDotMatrix`, inspect/detail mode (`inspectObjectContains`, `findInspectObject`, `paintPointerCursor`, `inspectPointer`, `setDetailMode`) |
| 255-349 | `drawState` — renders state; **feature-specific**: tasks dict line 304 (all pages), care/harvest/cooking/inventory/fishing progress lines 306-312, object list |
| 350-382 | `handleResponse` (speech + sfx + score feedback) |
| 383-469 | Pointer queue/throttle (`queuePointer`, `sendMoveIfPossible`, `sendCommand`, `enqueueRequest`) → `/api/pointer/*`, `/api/command` |
| 470-594 | `loadState`, canvas pointer events (flower contact flag 478-482), keyboard via GameKeys |
| 595-656 | Buttons: TTS test, reset (`/api/reset`), replay (uses `state.dialogue`), stop, Rowan voice test (615), mute, rate, volume, target cues, sfx toggle |
| 657-671 | Focus/visibility → suspend audio, release gesture |
| 672-700 | `window.DotdewInput` API used by hardware.mjs (`state, command, keyDown, keyUp, setDetailMode, move, press, release`) |
| 701-726 | `applyClientSettings`, `refreshDelayedVisuals` → `/api/visual-tick` polling |
| 728-733 | **flower-specific** 100 ms re-send of pointer while watering |
| 735 | module `hardware.mjs?v=20261020-bluetooth-tracking`, `#visual-relay`, `spectator/display.js?v=flowers-2` |

Cache-busting query strings are hand-edited per file (`?v=single-spatial-10`, `?v=team-speech-9`, `?v=evaluation-click-1`, ...).

### 5.2 Shared JS files with feature code

| File | Generic part | Feature-specific part |
|---|---|---|
| `game-audio.js` | channels, unlock, volume, ducking, spatial bus, `cue`/`feedback`, `handle` (377-411), BGM (412-489) | `backgroundFor` page lists (412-417, settings `bgm_shop_pages/bgm_minigame_pages` from config), task loops for care/harvest/cooking in `inputDown/move/pulse/syncWork` (265-376), **fishing sonar** `syncFishing/updateFishingPosition/stopFishing` (490-530; 65 "fishing" mentions), target guidance for care/harvest/mine `syncGuidance/pulseGuidance` (560-616) |
| `game-speech.js` | entire file generic (speech transport) | — |
| `game-keys.js` | entire file generic | — |
| `hardware.mjs` | `packCells`, `displayPacket`, `extractPackets`, `forwardKey`, `SerialPad` (USB; packet layout from eun022/hand_drawing) | Bluetooth button wiring 140-168, hand-tracking WebSocket client 169-202 (coordinates only, manual "Press" button) |
| `bluetooth-pad.mjs` | `BluetoothPad` | duplicates `packCells`/`forwardKey` |
| `spectator/model.mjs` | `WORLD`, `phase`, `scene`, `snapshot` | `TITLES` (Rowan/calendar pages), `SPRITES`, `plots`, `rockRect` (mining), `publicCards` (shop/inventory) |
| `spectator/viewer.js` | asset loading 30-31, `render` 418, `receive` 647, `relay` 685 | `farm` 145, `mine` 182, `fishing` 204, `map/mini` 228-369, `detail` 370, `menus` 514 (shop/inventory cards), `dialogueUI` 610 (Rowan), `flowerDetail` 715 |

---

## 6. Setup and launch inventory

| File | Does | Python lookup | Port | Messages |
|---|---|---|---|---|
| `setup-windows.bat` | `py -3` or `python` → `tools/setup_game.py` | system | — | Korean only |
| `setup-mac.command` (zsh) | `python3 tools/setup_game.py` | system | — | Korean only |
| `tools/setup_game.py` | Require 3.11; create `.venv` if neither `.venv` nor `venv` has python; `pip install -r requirements.txt`; `pip check`; `prepare_speech.py --download`; `check_setup.py --synthesize` | `.venv` then `venv` | — | English |
| `game.bat` | `.venv\Scripts\python.exe` else `venv\...` → `launch_game.py --port 8003 --prepare-demo` | `.venv` then `venv` | **8003** | Korean only |
| `start-mac.command` | `.venv/bin/python` else `venv/...` → `launch_game.py --port 8000 --prepare-demo` | `.venv` then `venv` | **8000** | Korean only |
| `launch_game.py` | `--port` (default 8000), `--no-browser`, `--prepare-demo`, `--check`; probe port (reuse running game / refuse foreign process); `check_setup`; spawn `uvicorn game_app:app`; run `tools/prepare_demo.py --server <url>`; open browser; terminate only owned server | current interpreter | default 8000 | English |
| `tools/check_setup.py` | Python ≥3.11; fastapi, uvicorn, piper-tts==1.8.0, onnxruntime; required files (missing `game_village.py`, `game_icons.py`); 18 MP3s; `speech_config.json` + `models/piper/*.onnx`; writable `saves/`, `.cache/speech`; optional synth | — | — | English |
| `tools/prepare_speech.py` | Download Piper voices to `models/piper` (with fallback downloader) | — | — | English |
| `tools/prepare_demo.py` | Generate all demo lines via server API; report to `output/audio/demo-ready.json` | — | default 8000 | English |
| `tracking_server.bat` / `tracking_test.bat` | Find python in `venv`, `.venv`, `..\venv`, `..\.venv` (**venv first**, opposite of the game scripts); run tracking script | `venv` first | 8765 (config) | English |
| (none) | No mac/linux launcher for tracking; no installer for tracking deps or DotPadSDK | | | |

Other hardcoded ports: `tools/audio_integration_lab.py` 8001; README `adb reverse tcp:8000 tcp:8000` (wrong for game.bat's 8003); `test_startup.py` expects 8000 in messages.

Dependencies NOT installed by any script:
- Tracking: `opencv-python` (cv2), `mediapipe`, `numpy`, `websockets` — absent from `requirements.txt` (which has only `fastapi`, `uvicorn`, `piper-tts==1.8.0`).
- `numpy`, FFmpeg, Node for `tools/prepare_effects_preview.py`.
- Node.js for JS tests.
- DotPadSDK 3.0.3 (`web/vendor/DotPadSDK-3.0.3.js`, `.d.ts`): manual download per README "Dot Pad SDK"; gitignored; Bluetooth button shows an error if absent; `test_hardware.mjs` cannot load without it.

Gaps that justify a unified installer/launcher:
1. Two venv precedence orders (game: `.venv`>`venv`; tracking: `venv`>`.venv`).
2. Port differs by OS (8003 Windows, 8000 mac) with no documented reason; README adb instructions assume 8000.
3. Tracking has no requirements file or setup path; Windows-only `.bat` launchers.
4. Korean-only user prompts in 4 scripts while app/README default is English.
5. `check_setup` required-file list is incomplete (17 in §3.4).
6. No single "run all tests" command (README list is stale; Windows needs `PYTHONUTF8=1`; discover hangs on 3.12).
7. Logic duplicated: python discovery in `game.bat`, `start-mac.command`, `tracking_*.bat`, `tools/setup_game.environment_python`, `test_audio_integration.cjs:100`.
Against: `launch_game.py` + `setup_game.py` are already cross-platform and tested (`test_startup.py`, 15 ok); the gaps can be closed by extending them rather than adding a new tool.

---

## 7. Branches

- Remote branches: `origin/main`, `origin/bluetooth-dotpad`. No tags.
- `origin/bluetooth-dotpad`: 1 commit `dc2fdf7` (2026-10-15, "닷패드 연결을 USB에서 블루투스로 변경") on merge-base `bb081bc` (2026-10-11). main is 24+ commits ahead.
- Actual branch change (vs merge-base), 7 files: `.gitignore` (+`/web/vendor/DotPadSDK-*`), `README.md`/`README.ko.md` (USB→Bluetooth wording, "Dot Pad SDK" section), `test_hardware.mjs`, `web/game.html` (`#usb-button`→`#ble-button` + text), `web/hardware.mjs` (rewritten as SDK-based BluetoothPad, USB removed), `web/vendor/package.json` (new).
- `git diff main origin/bluetooth-dotpad` shows ~45 deletions (`game_flowers.py`, `game_icons.py`, `game_npc.py`, `game_village.py`, `game_speech.py`, `speech_queue.py`, `launch_game.py`, `tools/*`, `docs/audio/*`, most tests, 5 PNGs, ...). These are **stale**: files added on main after the branch point, not deletions made by the branch. Merging the branch is unnecessary.
- Already integrated on main by hand in `0d90cbf` (2026-10-20, "블루투스 브랜치 통합"): Bluetooth adapter moved to new `web/bluetooth-pad.mjs`, lazily imported from `web/hardware.mjs:148`; USB `SerialPad` kept; `game.html` has both buttons; `.gitignore`, `web/vendor/package.json`, `test_hardware.mjs` taken from branch. Same commit also removed `TrackingGestureInput` from hardware.mjs and reverted `tracking/gesture.py`, `tracking/core.py`, `tracking_config.json` changes from `910d6c1` (thumb-press clicks) — unclear if intentional; `test_tracking_input.mjs` (added in `910d6c1`) was left behind and now cannot load.
- Leftover inconsistency to resolve during refactor: `test_hardware.mjs` expects the branch API (`BluetoothPad`, `cellsToHex` exported from `hardware.mjs`). Either point it at `web/bluetooth-pad.mjs` or re-export there.
- Files to keep stable/isolated so the Bluetooth change stays reapplicable: `web/hardware.mjs`, `web/bluetooth-pad.mjs`, `web/vendor/`, the hardware card markup in `web/game.html` line 44 and `window.DotdewInput` (672-700), `test_hardware.mjs`. `origin/bluetooth-dotpad` can be deleted after confirming 0d90cbf is the accepted integration.

---

## 8. Repo hygiene facts (affect collaboration, not code)

- 73 of 86 commits authored as `unknown <seojbin@gmail.com>` (git `user.name` unset on one machine); 12 as `seojbin`, 1 `SWKIMMS`.
- Commit messages are not descriptive: "로직수정" ×25, "디스플레이 추가" ×7 (`641c6f4` with that message deleted `test_fishing.py` and changed 9 files / +585 −367).
- README.md (38 KB) and README.ko.md (46 KB) end in appended changelog sections (README.md:329-417 "Fishing update", "Seafood recipes", ..., "In-place dialogue and tool visuals") that reference non-existent tests.
- `docs/audio/TEAM_HANDOFF.md` (Korean) references fork `SWKIMMS/Visionpad` branch `codex/audio-tts-npc` and commit `3728f76`.
- Mixed languages in code comments: Korean in `dotpad.py:83`, `game_icons.py:148`.
- Test files live at repo root (21 files) alongside source (19 .py at root).

---

## 9. Recommendations (concise)

### 9.1 Target structure

```
dotdew/                      # python package (replaces root-level modules)
  app.py                     # game_app.py
  engine/
    engine.py                # GameEngine shell: __init__, reset orchestration, response, get_state assembly
    registry.py              # feature hooks: pages, draw-by-type, actions(prefix), tts, hover_sfx, state, reset, daily_tick, leave_page, save_migrations, guidance
    render.py                # DotPad primitives + render() loop via registry
    input.py                 # pointer_*/move_minigame/_perform_action via registry
    time.py  keypad.py  saves.py  icons.py  dotpad.py  spectator.py
  features/
    farming/ harvest/ cooking/ seafood/ fishing/ mining/ shop/ research/
    inventory/ minimap/ home/ flowers/ village/ npc/
      __init__.py (mixin + register())  config keys  tests/
  speech/ (game_speech.py, speech_queue.py)
web/
  core/ (game.html split: app.js, input.js, status.js), audio/ (game-audio.js core + features/fishing-audio.js, guidance.js), hardware/ (hardware.mjs, bluetooth-pad.mjs, vendor/), spectator/
tracking/  + requirements-tracking.txt + cross-platform launcher
scripts/   (setup-*, start-*, game.bat → one launcher with a single default port)
tests/python/  tests/js/
```

Keep `GameEngine` as one object (state, save format and tests depend on flat `self.*` names); split code, not state, first.

### 9.2 Extraction order (lowest coupling first)

0. Preconditions: fix test encoding (`encoding="utf-8"`), add a timeout or Python-3.12-safe pattern to `test_failure_does_not_block_the_next_request`, re-baseline inside `.venv` with fastapi and with Node; decide fate of the 8 drift failures (fix tests or code) so baseline is green; resolve `display.js` drift (pick bundle or sources, make the build reproducible).
1. Introduce registry hooks for hotspots 1, 3, 4, 6, 7, 9, 10, 11, 12 while code stays in place (behavior-preserving; one hotspot per PR).
2. `flowers` (already a mixin; deps: time only) → move into `features/flowers`, register hooks; move flower pieces out of `home` (593-602) and `game.html` 728-733.
3. `research`, `minimap`, `inventory` (deps mostly core/time + `clear_*`).
4. `npc` + `village` together (mutual cycle; move `rowan_*` writes out of `travel_to` 2301-2302/2324 and `open_shop`).
5. `mining` (needs `get_pickaxe_price` moved from shop, `market_price` interface).
6. `fishing` + `seafood` (seafood is a cross-feature modifier: define interfaces `loot_amount`, `boost_rare_weights`, `sale_price`, `consume_sale` as engine-level "modifiers").
7. `shop` (catalog aggregator: features register sellable/buyable items instead of shop branching on kinds).
8. `cooking`, `harvest`, `farming` last (largest; share `farm_plots`, `resources`, `active_buff`, minigame pointer state).
9. Frontend split mirrors step order; `game-audio.js` fishing/guidance into feature modules.

### 9.3 Risks

- Save compatibility: save keys = attribute names (`snapshot` uses `vars(self)`); `restore_snapshot` rejects any key-set mismatch. Moving/renaming any attribute without a migration breaks existing `saves/*.json`.
- MRO chains (`show_rowan`, `navigate_key`) and `_perform_action` prefix order (night guard at 2223 applies only to later prefixes) are behavior.
- Tests and `tools/audio_flow.py` reach into engine internals; keep names stable until tests are rewritten against public APIs.
- `display.js` regeneration will silently drop hand edits.
- Shared `resources` dict is mutated by 10 features; concurrent PRs touching resource keys will conflict in `reset` (136-155) and save migrations.
- Hardware/tracking code has no runnable tests in this environment (missing SDK, missing exports, no camera); changes there are unverified.

# BASELINE — test results every refactor phase must reproduce

Replaces AUDIT.md §1 as the reference. Recorded on branch `refactor/modular-structure`, Phase 0, base commit `ea38001`, 2026-10-24.

## Environment

| Item | Value |
|---|---|
| OS | Windows 11 Home 10.0.26200 |
| Python | 3.12.10, project `.venv` created from `requirements.txt` (`fastapi`, `uvicorn`, `piper-tts==1.8.0`); `pip check` clean |
| Node.js | v24.22.1 (winget `OpenJS.NodeJS.LTS`, `C:\Program Files\nodejs`) |
| Not installed | tracking deps (`cv2`, `mediapipe`, `numpy`, `websockets`); DotPadSDK 3.0.3 (gitignored, manual download) |
| `PYTHONUTF8` | not set (encoding is now explicit in tests) |

## Commands

Since Phase 1 (tests live under `tests/`):

```
.venv\Scripts\python.exe -m unittest discover -s tests/python -t . -v
node --test "tests/js/**/test_*.cjs" "tests/js/**/test_*.mjs"
```

Phase 0 (tests at the repo root), as recorded below:

```
.venv\Scripts\python.exe -m unittest test_team_audio test_speech_queue test_speech_api test_gameplay_audio test_speech test_sound_events test_audio_flow test_demo_speech test_startup test_save_compat -v
node --test test_speech.cjs test_guidance.cjs test_fishing_audio.cjs test_effects.cjs test_audio_integration.cjs test_hardware.mjs test_tracking_input.mjs
```

`python -m unittest discover -p "test_*.py"` from the repo root additionally reports `ERROR tracking (unittest.loader._FailedTest)` because discovery imports the `tracking/` package, which needs `cv2`. That error is a discovery artifact and is not part of the baseline; it disappears once tests live under `tests/` (Phase 1). `test_support.py` defines no tests.

When tests move in Phase 1, module paths in the tables change; the comparison key is `Class.test` (Python) and `file stem + test name` (Node).

## Summary

| Suite | Total | ok | FAIL | ERROR |
|---|---|---|---|---|
| Python | 70 | 61 | 6 | 3 |
| Node (`node --test` count, includes 3 subtests and 2 load-failure entries) | 59 | 57 | 2 | — |

All 11 non-ok results are known and must stay exactly as listed (do not fix during the refactor; see FOLLOWUPS.md F1–F4).

## Phase 0 changes to test infrastructure (no game code touched)

| File | Change | Reason |
|---|---|---|
| `test_gameplay_audio.py:19`, `test_sound_events.py:16`, `test_speech.py:98`, `test_team_audio.py:17`, `test_demo_speech.py:44` | `read_text(encoding="utf-8")` | Windows locale codec failed on `game_config.json` (27 setup errors) |
| `test_speech_queue.py` `test_failure_does_not_block_the_next_request` | `asyncio.wait_for(good.future, 5)`; timeout → `self.fail(...)` | Test hung forever on Python 3.12; now a FAIL after 5 s |
| `test_audio_integration.cjs:101` | `spawnSync(..., {maxBuffer: 64 MiB})` | `tools/audio_flow.py --stdout` prints 1,128,947 bytes, above Node's 1 MiB default; spawn aborted with `status null` (ENOBUFS). Not in the original brief; test-infra only. |
| `test_save_compat.py` (new) + `tests/fixtures/saves/v1_day1_farm_started.json` (new) | Loads a save made with the pre-refactor engine; asserts recorded progress, exact `snapshot()` equality, and save → reload round trip | Guards save format (attribute names = save keys). Verified it fails if the engine gains one extra attribute. |
| `README.md:72`, `README.ko.md:72` | Test commands list only existing tests; points to BASELINE.md | `test_fishing` was listed but deleted in `641c6f4` |

## Python results

| Module | Class | Test | Result | Note |
|---|---|---|---|---|
| test_team_audio | TeamIntegrationTests | test_evaluation_click_command_keeps_selecting_instead_of_pausing | ok |  |
| test_team_audio | TeamIntegrationTests | test_motion_without_press_still_collects_targets_and_updates_guidance | ok |  |
| test_team_audio | TeamIntegrationTests | test_pre_audio_quest_save_keeps_its_stage_and_does_not_repeat_soup | ok |  |
| test_team_audio | TeamIntegrationTests | test_shop_advice_is_selectable_without_advancing_the_quest | ERROR | StopIteration: no shop advice object (F1) |
| test_team_audio | TeamIntegrationTests | test_tutorial_gifts_and_crop_reward_are_still_granted_once | ok |  |
| test_team_audio | TeamIntegrationTests | test_village_has_one_rowan_and_quest_replay_does_not_repeat_gifts | FAIL | two `talk_rowan` objects in town (F1) |
| test_speech_queue | QueueTests | test_action_overtakes_other_clients_hover_and_background | ok |  |
| test_speech_queue | QueueTests | test_active_generation_can_finish_without_delivering_obsolete_audio | ok |  |
| test_speech_queue | QueueTests | test_delayed_cancel_does_not_cancel_the_new_sequence | ok |  |
| test_speech_queue | QueueTests | test_failure_does_not_block_the_next_request | FAIL | Python 3.12 `assertRaises` clears the worker frame; now fails after 5 s instead of hanging (F2) |
| test_speech_queue | QueueTests | test_late_old_request_is_rejected_without_synthesis | ok |  |
| test_speech_queue | QueueTests | test_many_obsolete_hovers_never_reach_synthesis | ok |  |
| test_speech_queue | QueueTests | test_queue_capacity_is_bounded | ok |  |
| test_speech_api | SpeechApiTests | test_cancel_route_discards_old_request_but_accepts_current_one | ok |  |
| test_speech_api | SpeechApiTests | test_generation_error_keeps_503_and_the_queue_can_retry | ok |  |
| test_speech_api | SpeechApiTests | test_legacy_request_still_generates_speech | ok |  |
| test_speech_api | SpeechApiTests | test_partial_client_identity_is_rejected_before_generation | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_cooking_reaction_is_recorded_only_after_a_dish_is_created | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_first_fishing_catch_uses_the_actual_fish_name | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_guidance_excludes_collected_targets_and_stops_during_pause | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_mined_rock_disappears_from_guidance_and_hit_progress_is_reported | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_old_progress_does_not_claim_a_first_ever_harvest | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_reaction_is_remembered_across_save_and_dialogue_replay | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_real_harvest_gets_a_first_reaction_without_extra_resources_or_time | FAIL | Rowan quest grants `rowan_soup` (F1) |
| test_gameplay_audio | GameplayAudioTests | test_real_tool_break_gets_replacement_advice | ok |  |
| test_gameplay_audio | GameplayAudioTests | test_rejected_action_does_not_record_a_success | ok |  |
| test_speech | NpcTests | test_dialogue_is_unavailable_in_other_locations_and_while_paused | ok |  |
| test_speech | NpcTests | test_dialogue_topics_do_not_consume_resources_or_time | FAIL | Rowan quest grants `rowan_soup` (F1) |
| test_speech | NpcTests | test_farming_and_fishing_advice_uses_actual_state | FAIL | `npc_action` ignores topic (F1) |
| test_speech | NpcTests | test_npc_is_a_selectable_tactile_target | ERROR | StopIteration: no `rowan` object on shop page (F1) |
| test_speech | NpcTests | test_old_saves_get_npc_defaults_and_current_dialogue_roundtrips | ERROR | KeyError 'shopkeeper' (F1) |
| test_speech | NpcTests | test_trade_and_goodbye_leave_dialogue_and_revisit_changes_greeting | FAIL | 'town' != 'shop_choice' (F1) |
| test_speech | SpeechTests | test_corrupt_cache_is_regenerated | ok |  |
| test_speech | SpeechTests | test_invalid_voice_text_rate_and_path_are_rejected | ok |  |
| test_speech | SpeechTests | test_partial_audio_is_not_cached_and_retry_succeeds | ok |  |
| test_speech | SpeechTests | test_pronunciation_keeps_numbers_and_display_text | ok |  |
| test_speech | SpeechTests | test_repeated_text_reuses_complete_audio | ok |  |
| test_speech | SpeechTests | test_voice_rate_model_and_pronunciation_change_cache_identity | ok |  |
| test_sound_events | ActionSoundTests | test_buying_and_selling_emit_coin_but_rejections_do_not | ok |  |
| test_sound_events | ActionSoundTests | test_care_and_harvest_completion_keep_success_feedback | ok |  |
| test_sound_events | ActionSoundTests | test_cooking_completion_has_success_feedback | ok |  |
| test_sound_events | ActionSoundTests | test_fishing_miss_and_invalid_cast_have_different_feedback | ok |  |
| test_sound_events | ActionSoundTests | test_menus_save_and_load_have_feedback_without_spending_time | ok |  |
| test_sound_events | ActionSoundTests | test_travel_and_shop_entry_emit_the_matching_recording_once | ok |  |
| test_audio_flow | AudioFlowTests | test_all_gameplay_milestones_are_reached_by_pointer_and_key_input | ok |  |
| test_audio_flow | AudioFlowTests | test_required_action_and_result_sounds_are_present | ok |  |
| test_audio_flow | AudioFlowTests | test_save_and_load_preserve_the_completed_session | ok |  |
| test_demo_speech | DemoSpeechTests | test_failed_line_is_not_reported_as_ready_and_can_retry | ok |  |
| test_demo_speech | DemoSpeechTests | test_missing_models_fail_before_generation | ok |  |
| test_demo_speech | DemoSpeechTests | test_repeat_preparation_reuses_audio_and_rate_has_its_own_cache | ok |  |
| test_demo_speech | DemoSpeechTests | test_server_preparation_only_calls_speech_endpoints | ok |  |
| test_demo_speech | DemoSpeechTests | test_source_lines_are_unique_and_include_exact_npc_branches | ok |  |
| test_startup | SetupChecks | test_broken_model_configuration_is_not_accepted_as_a_ready_voice | ok |  |
| test_startup | SetupChecks | test_complete_setup_reports_ready_without_creating_progress_or_cache | ok |  |
| test_startup | SetupChecks | test_missing_dependency_has_an_actionable_fix | ok |  |
| test_startup | SetupChecks | test_missing_sound_and_game_module_are_both_reported | ok |  |
| test_startup | SetupChecks | test_older_python_is_reported_before_starting_any_server | ok |  |
| test_startup | StartupTests | test_broken_existing_environment_is_preserved | ok |  |
| test_startup | StartupTests | test_environment_discovery_supports_both_platforms_and_legacy_venv | ok |  |
| test_startup | StartupTests | test_existing_server_is_reused_without_launching_or_stopping_a_process | ok |  |
| test_startup | StartupTests | test_failed_package_install_stops_before_voice_download | ok |  |
| test_startup | StartupTests | test_first_setup_installs_only_into_its_new_project_environment | ok |  |
| test_startup | StartupTests | test_old_environment_python_is_rejected_before_installing | ok |  |
| test_startup | StartupTests | test_readiness_failure_is_detected_before_opening_the_browser | ok |  |
| test_startup | StartupTests | test_server_probe_requires_game_title_and_speech_endpoints | ok |  |
| test_startup | StartupTests | test_startup_failure_terminates_only_the_server_created_by_the_launcher | ok |  |
| test_startup | StartupTests | test_unrelated_busy_port_is_never_replaced | ok |  |
| test_save_compat | SaveCompatibilityTests | test_fixture_loads_with_the_recorded_progress | ok |  |
| test_save_compat | SaveCompatibilityTests | test_loaded_state_matches_the_fixture_exactly | ok |  |
| test_save_compat | SaveCompatibilityTests | test_save_and_reload_round_trips | ok |  |

## Node results

| File | Test | Result | Note |
|---|---|---|---|
| test_audio_integration.cjs | page changes cancel old tap, target, transaction and cue loads | ok |  |
| test_audio_integration.cjs | leaving the mine cancels deferred loot speech and reward | ok |  |
| test_audio_integration.cjs | sleep transition survives the morning and ordinary scene changes | ok |  |
| test_audio_integration.cjs | back navigation with a recorded step does not add another page tone | ok |  |
| test_audio_integration.cjs | temporary asset failure retries on the next action without a request storm | ok |  |
| test_audio_integration.cjs | background music can recover from an initial asset failure | ok |  |
| test_audio_integration.cjs | the full real-engine flow drives the audio module without leftover task loops | ok |  |
| test_effects.cjs | completed physical tasks get confirmation instead of silent suppression | ok |  |
| test_effects.cjs | recorded footsteps, doors and coins do not get duplicate synthetic cues | ok |  |
| test_effects.cjs | miss, rejection, completion and navigation use distinct cues | ok |  |
| test_effects.cjs | ↳ water_minigame | ok |  |
| test_effects.cjs | ↳ fertilizer_minigame | ok |  |
| test_effects.cjs | ↳ harvest | ok |  |
| test_effects.cjs | held care work uses one active recording; quick taps retain a short cue | ok |  |
| test_effects.cjs | TTS gain changes cannot restart idle chopping; movement restores it | ok |  |
| test_effects.cjs | one-shot and cue volume follows speech and all cue notes stop on mute | ok |  |
| test_effects.cjs | fast hover exploration is rate limited and progress sounds do not multiply | ok |  |
| test_effects.cjs | response routing plays state events and semantic feedback exactly once | ok |  |
| test_effects.cjs | evaluation work starts on movement without a press and silences when idle or away | ok |  |
| test_effects.cjs | task positioning retains the team spatial bus and one-shot effects still duck | ok |  |
| test_fishing_audio.cjs | HRTF follows pointer-relative left, right, ahead and behind | ok |  |
| test_fishing_audio.cjs | nearer water is louder and speech retains the exploration cue | ok |  |
| test_fishing_audio.cjs | server snapshots preserve local pointer position and reuse one water loop | ok |  |
| test_fishing_audio.cjs | leaving stops water and prevents a late decode from restarting it | ok |  |
| test_fishing_audio.cjs | pause stops water and prevents a late decode from restarting it | ok |  |
| test_fishing_audio.cjs | sleep stops water and prevents a late decode from restarting it | ok |  |
| test_fishing_audio.cjs | night stops water and prevents a late decode from restarting it | ok |  |
| test_fishing_audio.cjs | window suspension blocks late state responses; return restores only ambient loops | ok |  |
| test_fishing_audio.cjs | returning to the window preserves the user sound mute | ok |  |
| test_fishing_audio.cjs | old water and transaction decodes cannot play after returning to the window | ok |  |
| test_fishing_audio.cjs | splash and shine start together; stopping pending effects prevents playback | ok |  |
| test_guidance.cjs | beacons follow pointer-relative direction immediately without a server round trip | ok |  |
| test_guidance.cjs | nearest target stays stable at a boundary and changes when collected | ok |  |
| test_guidance.cjs | closer targets use faster pulses and a higher pitch | ok |  |
| test_guidance.cjs | farm and mine activities have distinct beacon pitches | ok |  |
| test_guidance.cjs | pause, leaving, mute and window suspension stop every pending beacon | ok |  |
| test_guidance.cjs | target cue preference survives suspension and does not disable fishing | ok |  |
| test_guidance.cjs | crop progress changes confirmation pitch while cooking retains its original cue | ok |  |
| test_guidance.cjs | successive mine hits change impact pitch without altering the recording | ok |  |
| test_speech.cjs | first input unlocks the pending message, and replay reuses decoded audio | ok |  |
| test_speech.cjs | NPC profile and selected rate are sent to the fixed voice service | ok |  |
| test_speech.cjs | speech starts at 85 percent and volume changes reuse the active voice | ok |  |
| test_speech.cjs | speech volume clamps safely and does not change game sound volume | ok |  |
| test_speech.cjs | late generation never plays after cancellation or a newer message | ok |  |
| test_speech.cjs | hover cannot interrupt a dialogue and only the latest hover follows it | ok |  |
| test_speech.cjs | mute drops speech and deferred hover, without replay on re-enable | ok |  |
| test_speech.cjs | voice failure restores mixing and replay can retry | ok |  |
| test_speech.cjs | TTS ducks BGM and restores it while preserving fishing guidance | ok |  |
| test_speech.cjs | window suspension discards late narration without autoplay on return | ok |  |
| test_speech.cjs | suspending active speech restores mixing and keeps speech mute on return | ok |  |
| test_speech.cjs | a delayed game result can update the caption and replay without autoplay | ok |  |
| test_speech.cjs | stopping a pending line cancels its server sequence without requesting audio | ok |  |
| test_speech.cjs | a superseded API response is silent and a new result still plays | ok |  |
| test_speech.cjs | quest narration finishes before the latest action and drops hover labels | ok |  |
| test_speech.cjs | locked quest is preserved until activation and retains its latest action | ok |  |
| test_speech.cjs | a new quest replaces the old one and cancellation drops deferred actions | ok |  |
| test_speech.cjs | replay retains the quest voice and protection channel | ok |  |
| test_hardware.mjs | test_hardware.mjs | FAIL | file fails to load: `web/vendor/DotPadSDK-3.0.3.js` missing; also imports `BluetoothPad`/`cellsToHex` not exported by `web/hardware.mjs` (F3) |
| test_tracking_input.mjs | test_tracking_input.mjs | FAIL | file fails to load: `TrackingGestureInput` not exported by `web/hardware.mjs` (F4) |

## Python results addendum: registry tests (Phase 2b)

Added with the approved registry changes. These 16 tests are new; every result above is unchanged. Python total becomes 86 (77 ok, 6 FAIL, 3 ERROR).

| Module | Class | Test | Result | Note |
|---|---|---|---|---|
| tests.python.core.test_registry | ConflictTests | test_core_slots_cannot_be_redeclared | ok |  |
| tests.python.core.test_registry | ConflictTests | test_feature_names_must_be_unique_and_present | ok |  |
| tests.python.core.test_registry | ConflictTests | test_two_features_cannot_claim_the_same_hook | ok |  |
| tests.python.core.test_registry | OrderingTests | test_actions_dispatch_by_prefix_or_exact_key_in_their_guard_phase | ok |  |
| tests.python.core.test_registry | OrderingTests | test_events_run_by_order_then_registration | ok |  |
| tests.python.core.test_registry | OrderingTests | test_reset_splits_at_the_core_boundary | ok |  |
| tests.python.core.test_registry | OrderingTests | test_slot_contributions_follow_their_order | ok |  |
| tests.python.core.test_registry | OwnershipTests | test_enabled_features_own_existing_saved_attributes | ok |  |
| tests.python.core.test_registry | OwnershipTests | test_owned_attributes_must_exist_after_reset | ok |  |
| tests.python.core.test_registry | OwnershipTests | test_two_features_cannot_own_one_attribute | ok |  |
| tests.python.core.test_registry | SlotTests | test_a_declared_slot_without_contributions_is_empty | ok |  |
| tests.python.core.test_registry | SlotTests | test_a_slot_declared_by_a_later_feature_accepts_earlier_contributions | ok |  |
| tests.python.core.test_registry | UnknownNameTests | test_collecting_an_undeclared_slot_fails | ok |  |
| tests.python.core.test_registry | UnknownNameTests | test_unknown_event_is_rejected_at_registration | ok |  |
| tests.python.core.test_registry | UnknownNameTests | test_unknown_page_hook_is_rejected | ok |  |
| tests.python.core.test_registry | UnknownNameTests | test_unknown_slot_is_rejected_after_all_features_register | ok |  |

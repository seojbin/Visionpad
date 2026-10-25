# engine

Shared code that every feature uses: the server, the game engine core, the Dot Pad display, saves, speech, the browser player (audio, keys, pad), the companion window, configuration, the launcher and installer logic, dev tools and the shared tests. Changes here need approval (see `AGENTS.md`).

The server owns game state and checks every action. The browser sends pointer and key input and receives dot frames, public state, speech and sound events. Mouse, keyboard, pad buttons and hand tracking all become the same move, press, drag and release events.

## Folders

| Path | Contents |
|---|---|
| `server/` | FastAPI app (`main.py`, run as `uvicorn engine.server.main:app`), shared runtime, routes: game page and input/state API (`/api/state`, `/api/pointer/*`, `/api/command`, `/api/reset`, `/api/visual-tick`), speech (`/api/speech*`), static files |
| `core/` | `engine.py` (state, reset, page objects, responses), `registry.py` (how features plug in), `order.py` (run orders for events and slots), `input.py`, `render.py`, `time.py` (time, night, sleep), `state.py` (shared-state helpers), `effects.py` (food effects) |
| `display/` | `dotpad.py` (dot matrix and drawing), `icons.py` (icon grid and symbols), `keypad.py` (F-key menus, arrow navigation) |
| `services/` | `saves.py` (save files and migrations), `speech.py` (Piper and WAV cache), `speech_queue.py` |
| `spectator/` | `state.py`: public data for the companion window |
| `config/` | `game.json` (rules), `npc.json` (Rowan's lines), `speech.json` (voices), `tracking.json` (camera); `load_config()` in `__init__.py` |
| `web/` | `game.html`; `core/` (`game.js` page script, `pages.js` feature hooks, `game-audio.js`, `game-speech.js`, `game-keys.js`, `pad/`); `audio/` (shared sounds); `spectator/` (companion window) |
| `launcher/` | `launch_game.py`, `setup_game.py` (`--with-pad`), `check_setup.py`, `prepare_pad.py` (optional Dot Pad SDK): the logic behind the root `start-*` and `install-*` files |
| `tools/` | Dev tools (below) |
| `tracking/` | Camera hand and ArUco tracking (below) |
| `tests/` | Shared tests: `python/`, `js/`, `browser/` (URL check, Playwright smoke test), `fixtures/saves/` (a pre-refactor save that must keep loading) |
| `requirements.txt`, `requirements-dev.txt` | Game dependencies; dev-only tools (Playwright) |

Runtime audio files live in one hidden, gitignored folder at the project root, created by the installer and the server: `.audio/voices/` (Piper voice models), `.audio/cache/` (generated speech WAVs) and `.audio/reports/` (voice previews, `demo-ready.json`, `speech-catalog.json`, `integration-flow.json` from `audio_flow.py`, `effects-preview.wav`). Older checkouts used `models/piper/`, `.cache/speech/` and `output/audio/`; the installer, the launcher and the server move those files into `.audio/` on start and print a note (`services/audio_files.py`), so the voices are not downloaded again. A file that already exists in `.audio/` is kept, and anything else in those old folders is left where it is. Saves stay in `saves/`.

Features are in `game/`; the engine loads the names in `game/__init__.py` `ENABLED` and each feature registers its pages, actions, renderers, hover speech and sounds, state keys, event handlers, slot contributions, save fields and shop items. `GameEngine` stays one object whose attribute names are the save-file keys.

## Configuration

Edit `engine/config/game.json` and restart the server. Time is in game ticks, `_ms` values in milliseconds, probabilities 0–1, coordinates in dots.

| Key | Meaning (current value) |
|---|---|
| `game.start_day` | Starting day (1) |
| `resources` | Starting gold, fertilizer, seeds and crops |
| `time.total_cells`, `time.action_costs` | Ticks per day (20); cost per action: travel, plant, water, fertilize, harvest, research, cook, mine, fish |
| `seeds.<id>` | `growth_days`, `yield`, `seed_price`, `crop_price`, `seed_return_chance` (0.1) |
| `fertilizer.growth_day_bonus`, `shop.fertilizer_price` | Immediate growth (1 day); price (12) |
| `recipes.<id>` | `ingredients`, `buff_kind` (`harvest_multiplier`, `pickaxe_protection`, `time_slow`, …), `buff_multiplier`, `buff_ticks`, `gesture_steps` (per stage `kind`, `path`, `tolerance`) |
| `research.seed_return`, `field_expansion`, `mineral_luck` | Costs, levels and effects (farm expansion: `[30, 50, 70, 90]` gold and `[5, 10, 15, 20]` stone, two to six plots; seed return `[0.3, 0.6]`) |
| `care_minigame` | `target_count`, `target_positions`, `tolerance`, `success_ratio` (0.65) |
| `harvest_minigame` | `target_count`, `target_positions` (all targets required; the hit tolerance is fixed at 3.5 in code) |
| `interaction.feedback` | `disappear_delay_ms` (200), `visual_refresh_interval_ms` (100, minimum 50) |
| `interaction.cooking` | `resume_marker_delay_ms` (400), `stir_scale` (1.6) |
| `interaction.inventory` | `items_per_page` (12, range 1–12), `hide_zero_items` (true) |
| `interaction.sleep.blackout_ms` | Sleep blackout and input pause (2000) |
| `interaction.audio` | Volumes and gains (see Audio); `fishing` holds the lake sound settings |
| `mine` | `daily_rock_limit` (7, also capped in code), rock size and gap (10, 10, 5), `hits_to_break` (3), `pickaxe_price_multiplier` (5× fertilizer), `pickaxe_safe_hits` (9), `pickaxe_break_increment` (0.05), `loot_weights` (diamond 1, iron 15, copper 34, stone 50), `mineral_sell_multipliers`, `mineral_sell_price_bonus` (3), `mineral_buy_multiplier` (2) |
| `fishing`, `flowers`, `rowan`, `weekly_market` | See `game/fishing`, `game/flowers`, `game/village` |
| `dotpad`, `time.bar`, `home`, `farm`, `town`, `minimap` | Panel sizes and base layouts. Some screens are normalised to fixed grids in code, so a coordinate or `label` change may not show directly |

The F3 hold time is `holdMs` in `engine/web/core/game-keys.js`. Companion positions belong in `web/spectator/scene-objects.json`, image registration in `visual-assets.json`, card styles in `viewer.css`.

## Saves

Holding F3 saves to a new slot before the key is released (releasing it does not open the list); a short press opens the slot list. Saves are JSON files in `saves/` (the latest 12 are kept, not committed). A save is the engine's attributes in a fixed key order (`services/saves.py`, `SAVE_KEY_ORDER`), so **attribute names must never change**. Older saves get defaults for attributes added later (`reg.save_fields(defaults=...)`) and per-feature migrations. Pad connections, camera calibration and speech settings are not saved.

## Browser page, Dot Pad and tracking

- `web/core/game.js` draws the dot matrix, sends pointer input (queued and throttled), plays responses and exposes `window.DotdewInput` for the pad and tracking code. Feature-specific texts come from `game/<name>/client.js` through `web/core/pages.js`.
- `web/core/pad/hardware.mjs`: USB pad (Web Serial) output and buttons, and the hand-tracking WebSocket client (coordinates; a server that sends no press state needs the press button or F4). `bluetooth-pad.mjs`: Bluetooth pad through the Dot Inc. SDK in `web/core/pad/vendor/` (gitignored). It is optional: `install-windows.bat --with-pad` / `install-mac.command --with-pad` (or `python engine/launcher/prepare_pad.py`) downloads SDK 3.0.3 from Dot Inc.'s public SDK guide at a fixed commit and checks the pinned size and SHA-256. Without it the setup check prints a WARN line, the game still starts, and `test_hardware.mjs` is skipped with a message. The Dot Pad itself does not sense touch.
- **Hand tracking** (`tracking/`): a camera finds the pad with ArUco markers and the hand with MediaPipe, maps the fingertip onto the pad and sends coordinates over WebSocket (port in `config/tracking.json`, default 8765, the page's default too). Its dependencies (`opencv-python`, `mediapipe`, `numpy`, `websockets`) are not in `requirements.txt`; install them into `.venv` yourself. Run `engine\tracking\tracking_server.bat` (or `python engine/tracking/tracking_server.py`) for the server, `tracking_test.bat` / `tracking_test.py` for a local preview window. The `.bat` files look for `venv`, `.venv`, `..\venv`, `..\.venv` relative to the project folder, in that order.
- After changing web files, hard-refresh the game page and reopen the companion window. Serve the page through the server; opening the HTML file directly does not work.

## Visual Companion

A separate, read-only window (`web/spectator/`) that follows locations, selections, minigames, time of day and sleep; clicking it changes nothing. `standalone.html` is the entry page, `display.js` the bundle it loads, `model.mjs` turns game state into layout, `viewer.js` draws scenes, cards, objects and effects, `viewer.css` styles them, `visual-assets.json` registers backgrounds, facilities, items and sprite regions, `scene-objects.json` places facilities. Shared images are in `web/spectator/assets/`, feature images in `game/<name>/assets/`. Each plot and rock is a game object; a page without a visual renderer falls back to the dot display and an unregistered item shows its name in a frame.

**Do not regenerate `display.js`** with `tools/build_display.py`: it has hand edits that are not in `viewer.js`/`model.mjs` (follow-up F5).

`web/spectator/assets/items3.png` is a 3×3 item atlas: fishing rod / calendar / bird; coffee beans / coffee / scissors; animal feed / kitchen knife / bug net. The small rod is used in inventory and shop cards (the detailed rod is `fishing_rod_equipped` in `game/npc/assets/rowan.png`); the other seven are assets for future content. `items3.png` and `rowan.png` were generated with an image tool (pixel-art sprites on transparent backgrounds).

## Audio

Recorded sounds are 18 MP3 files: shared ones in `engine/web/audio/`, feature sounds in `game/<name>/audio/`. The original recordings are unchanged. Short synthetic cues are defined in `engine/web/core/game-audio.js` (`SOUND_CUES`, `feedback`, `cue`); all playback goes through `GameAudio`.

| Situation | Sound | Playback |
|---|---|---|
| Ordinary places | background-basic | Music loop |
| Farming and cooking | background-minigame | Not restarted within the same music group |
| Shop | background-shop | Music loop |
| Watering / fertilizing / harvesting | water / soil / crop | Loops while pressed |
| Chopping and stirring | cut, cook | Work sound continues while moving |
| Target passed | correct | Success sound, independent of the work sound |
| Travel and entering | step, door | One-shot |
| Trading and paid research | coin | One-shot |
| Sleep | sleep | Once when sleep starts; continues into the next morning |
| Mining | pickaxe, break | Hit and rock break |
| Rare find and broken tool | shine, destroy | Once per event |
| Fish caught | splash, shine | Catch and rare sounds start at the same time |
| Fishing exploration | water | HRTF direction relative to the pointer; louder when nearer |
| Task complete | synthetic `complete` | Short rising figure after watering, fertilizing, harvesting, cooking; also save/load success |
| Action not possible | synthetic `error` | Short falling figure: not enough money, no tool, invalid action |
| Fishing miss | synthetic `miss` | Short figure, distinct from the catch splash |
| Planting, menus, selection | synthetic `plant`, `page`, `select` | Short feedback per action type |
| Remaining farm and mine targets | HRTF sine beacon | Nearest remaining target; faster and higher when closer. **Target cues on/off** controls it (not the fishing sound) |

Mixing rules (values in `engine/config/game.json` → `interaction.audio`):

- Speech has its own gain (`GameSpeech`, 85% by default, **Speech volume**); it does not change effects, music or fishing gain. Reloading resets it to 85%.
- Holding a work action does not overlap the short click recording with the loop; a quick tap still leaves a short work sound. Chopping and stirring fade when movement stops, and speech does not revive them.
- `correct` (one target) and `complete` (whole task) are distinct. Recorded `step`, `door` and `coin` suppress duplicate synthetic cues. Hover tones are at least 220 ms apart.
- A page change cancels old work, target, transaction and synthetic sounds and pending decodes, including a deferred mining loot announcement. The sleep recording keeps playing once started. Pause, mute and leaving the window stop everything, including sleep.
- A failed sound load or decode is not cached as failed: it retries on the next action or state update after `audio_retry_ms` (1 s). Background music can recover after a failed first load.
- Music gains 0.30 / 0.20 (minigame) / 0.45 (shop), times the 0.9 master volume. During speech music is multiplied by 0.25 and one-shots and synthetic cues by 0.65; fishing exploration keeps its full gain.
- The quiet harvest and rare-reward recordings are boosted (crop 1.4, shine 3.0); soil 0.35 and cut 0.45. These are linear gains on the source, not slider percentages, and are a first mix for listening tests.

`python engine/tools/prepare_effects_preview.py` writes a labelled, about 37-second mono reel of every effect with the current gains to `.audio/reports/effects-preview.wav` (needs FFmpeg and Node). It does not reproduce HRTF or the live mix with music and speech.

### Voices and their sources

Speech is generated on the server by Piper 1.8.0 with two fixed English models: `en_US-hfc_female-medium` (system) and `en_US-hfc_male-medium` (Rowan). The browser plays the server's WAV files, never operating-system voices. No account or API key is needed. Models are stored in `.audio/voices/` and generated audio in `.audio/cache/`; neither is committed.

- [Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)
- [Piper package, GPL-3.0-or-later](https://pypi.org/project/piper-tts/)
- [HFC female model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/hfc_female/medium/MODEL_CARD)
- [HFC male model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/hfc_male/medium/MODEL_CARD)

Both model cards state the Hi Fi Captain dataset license, CC BY-NC-SA 4.0 (non-commercial). Check the model choice and terms again before any wider distribution.

## Speech

Player controls on the game page: **Test guide** (system voice) and **Test Rowan**; **Replay** repeats the current NPC line or the latest announcement; **Stop speech**; **Speech on/off** and **Speech rate**; **Speech volume** (85% by default, speech only; changing it mid-line does not restart or regenerate the line). Music drops to 25% while speech plays. Hover descriptions wait behind action results and dialogue. Leaving the window silences speech and sounds, including late responses; coming back restores music and the lake sound for the current screen and keeps mute settings, without replaying old lines (the caption and **Replay** still have them). Rowan adds a one-time reaction to the latest real result (first harvest, dish, catch, mineral, broken tool); it survives saves, and older saves get general reactions.

- Voice profiles, pronunciation version, sample sentences and `downloads` (each voice file's pinned URL, size and SHA-256): `engine/config/speech.json`; Rowan's lines: `engine/config/npc.json`. All settings files are read as utf-8-sig, so a byte-order mark added by a Windows editor is harmless; reports are written as UTF-8, and the Windows scripts and installer run Python with `PYTHONUTF8=1`. Display text and spoken text are separate: `F1`–`F4` are read as words, and `NPC` and `Dotdew` have fixed readings.
- `engine/services/speech.py` generates and caches WAVs (a repeated sentence reuses its file; partial or corrupt files are regenerated). `engine/services/speech_queue.py` serves requests through one worker.
- Queue rules: requests carry `client_id`, `sequence` and `priority`, so each browser's latest line wins and a late cancel never cancels a newer line. Action results and dialogue go before hover descriptions and before background preparation (`background` priority). Disconnected requests leave the queue; a synthesis already running finishes and may be cached, but cancelled audio is never delivered. The queue holds at most 64 requests (429 when full). Superseded requests get 204, invalid ones 422, synthesis errors 503. The plain `text/profile/rate` request still works.
- `python engine/tools/speech_inventory.py` lists the speech literals and templates in the game code (`engine/` without tests, tools, launcher and tracking, plus `game/`) into `.audio/reports/speech-catalog.json`. Text passed only through variables and browser-side messages are not expanded.

### Demo voice preparation

The launcher prepares the demo lines when it starts a new server (`--prepare-demo`, used by both start scripts). For a running server, from the project environment:

```
python engine/tools/prepare_demo.py                                   # server on port 8000
python engine/tools/prepare_demo.py --server http://127.0.0.1:8003    # Windows start script port
python engine/tools/prepare_demo.py --list                            # print the lines without a server
python engine/tools/prepare_demo.py --rate 1.2                        # cache for another speech rate
```

It collects about 210 lines at rate 1.0 (fixed guidance, Rowan's tutorial and advice branches, representative actions, objects and reactions) with a temporary engine and temporary saves, then calls only `/api/speech/voices` and `/api/speech`; it never sends game input. Finished WAVs are reused and failures are listed in `.audio/reports/demo-ready.json`; re-running regenerates only what failed. New quantities, prices, reactions and other rates are generated on first use, and the browser still has to download and decode each file.

## Dev tools

| Command | Purpose |
|---|---|
| `python engine/tools/run_tests.py` | Every test suite (see the root README) |
| `python engine/tools/audio_flow.py` | Scripted farming, cooking, Rowan/trading, mining, fishing and save/load run through real pointer and key input on temporary saves; `--stdout` prints the JSON |
| `python engine/tools/audio_integration_lab.py` | Browser lab on `http://127.0.0.1:8001/` starting in a temporary watering scene; does not touch real saves |
| `python engine/tools/prepare_speech.py [--download]` | Download the voice models (verified against the pinned size and SHA-256, three attempts, the old file is kept if a download fails, matching files are reused offline); write preview samples to `.audio/reports/` |
| `python engine/tools/prepare_effects_preview.py` | Effects reel (above) |
| `python engine/launcher/check_setup.py [--synthesize]` | Diagnose packages, files, sounds, voices and writable folders without starting a game |

## Manual testing

Automated tests check positions and playback state, not what a person hears or feels. Record real results; do not mark a check as done before it was run on that computer.

### Listening check

Use stereo headphones (both ears). Refresh the game, click once to enable audio, and save with a long F3 press before spending money or time.

1. **Fishing direction.** Walk to the fishing lake (Farm → Home → Village → Mine → Lake). Without pressing, move the pointer slowly inside the lake, left/right and up/down. Does the water sound get louder when you move towards it and quieter away from it? Note any front/back confusion as it is.
2. **Speech over guidance.** Press **Test guide** and keep exploring: can you follow both the speech and the water? Does the music return to normal afterwards?
3. **Leaving and returning.** Open the map with F1 and press F1 again: the water stops on the map and returns at the lake. Play **Test Rowan**, switch to another window and back: sound stops while away, old lines and effects do not suddenly play, music and lake sound return for the current screen. **Speech off** and **Sound off** stay off across the switch.
4. **A cast (optional, needs a rod).** Press once near the sound: a catch plays splash and the fish name and count; a miss plays no catch sound; holding or dragging does not cast again.
5. **Farm and mine target cues.** While watering, fertilizing, harvesting and mining, toggle **Target cues**. Can you tell direction and closeness, and do the beacons stay out of the way of work sounds, target sounds and speech? Can you hear progress in the rising pitch of farm targets and successive mine hits?
6. **Effects balance.** Listen to `.audio/reports/effects-preview.wav`, then in the game check: travel, shop entry and trading each sound once; water/fertilizer/harvest work sound, target sound and completion are distinct and a quick tap still sounds; chopping and stirring fade when you stop; mining hit, break, rare find and tool break are distinct; impossible actions play the error cue; music and effects do not cover speech; harvest and rare-find sounds are audible.
7. **Another computer.** After installing there, play **Test guide** and **Test Rowan** at the same rate and compare voice and pronunciation. Locally generated audio is not guaranteed to be bit-identical; compare the same `.audio/reports/` sample file when that matters.

Write down date, computer, browser, headphones, left/right, front/back, near/far, speech with water, recovery after map and window changes, and any badly pronounced sentence word for word.

### Play-test checklist

Run on Windows with `start-windows.bat` (port 8003) and, if possible, on a Mac with `start-mac.command` (port 8000). Keep the browser developer console open; any red error is a finding.

1. Setup and start: `python engine/launcher/check_setup.py` says "Setup ready"; the launcher opens the game; a second launch reuses the running server.
2. First click or key enables audio; music plays; **Test guide** and **Test Rowan** speak.
3. **Open visual display**: the companion opens on the home scene and follows every step below. Flower images, fish and fish dishes, and Rowan (portrait, standing, equipped rod) appear.
4. Travel Farm ↔ Home ↔ Village ↔ Mine ↔ Fishing lake with the arrow keys and with the F1 map; each move speaks the place; first village arrival: "Rowan would like to meet you."
5. Rowan quest: talk to Rowan (soup gift), receive seeds, plant, and submit a vegetable later; talking again does not repeat gifts.
6. Farming: plant a seed, water and fertilize with the care minigame (water and soil sounds, target cues), sleep, see growth and the morning "ready" note.
7. Harvest a mature plot (crop sound, yield, seed recovery).
8. Cooking: choose a recipe, select ingredients, trace both stages (cut and cook sounds), stall to see the resume marker, finish the dish; eat it from the F2 inventory and see the effect.
9. Mining: hit rocks (pickaxe, break, shine sounds), mine until the pickaxe breaks (destroy sound, replacement advice), buy a new pickaxe.
10. Fishing: enter without a rod (exploration text), buy a rod, follow the water sound with headphones, cast (splash, shine for rare fish), miss, break a rod.
11. Seafood: cook a fish dish and check its effect.
12. Shop: buy and sell pages, page turning, coin sound, rejection when gold is short; the calendar speaks the weekly offers.
13. Research: buy each upgrade at the home chest; farm expansion adds plots.
14. Flowers: buy morning glory seeds, plant in the pot, water by holding the pointer over the pot, grow over days, harvest bonus while blooming.
15. Time and sleep: run out of time, return home, sleep blackout and sleep sound, next morning.
16. Menus: F1 map and F2 inventory open and close with either arrow; F3 short press opens the save list; F3 hold saves ("Game saved.").
17. Saves: load a save made before the refactor (an existing `saves/*.json` from the old version) and continue; save and reload a new one.
18. Hard-refresh the game page after a run with the old version cached; no 404s.
19. Hardware, if available: USB pad, Bluetooth pad (install the SDK with `--with-pad`), hand tracking server (`engine/tracking/`). The console must not show "Expected a JavaScript-or-Wasm module script" for `hardware.mjs`.
20. Demo preparation: `python engine/launcher/launch_game.py --prepare-demo` completes and `.audio/reports/demo-ready.json` reports the lines ready.

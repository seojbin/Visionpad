# engine

Shared code that every feature uses: the server, the game engine core, the Dot Pad display, saves, speech, the browser player (audio, keys, pad), the companion window, configuration, the launcher and installer logic, dev tools and the shared tests. Changes here need approval (see `AGENTS.md`).

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

`python engine/tools/prepare_effects_preview.py` writes a labelled, about 37-second mono reel of every effect with the current gains to `output/audio/effects-preview.wav` (needs FFmpeg and Node). It does not reproduce HRTF or the live mix with music and speech.

### Voices and their sources

Speech is generated on the server by Piper 1.8.0 with two fixed English models: `en_US-hfc_female-medium` (system) and `en_US-hfc_male-medium` (Rowan). The browser plays the server's WAV files, never operating-system voices. No account or API key is needed. Models are stored in `models/piper/` and generated audio in `.cache/speech/`; neither is committed.

- [Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)
- [Piper package, GPL-3.0-or-later](https://pypi.org/project/piper-tts/)
- [HFC female model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/hfc_female/medium/MODEL_CARD)
- [HFC male model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/hfc_male/medium/MODEL_CARD)

Both model cards state the Hi Fi Captain dataset license, CC BY-NC-SA 4.0 (non-commercial). Check the model choice and terms again before any wider distribution.

## Speech

- Voice profiles, pronunciation version and sample sentences: `engine/config/speech.json`; Rowan's lines: `engine/config/npc.json`. Display text and spoken text are separate: `F1`–`F4` are read as words, and `NPC` and `Dotdew` have fixed readings.
- `engine/services/speech.py` generates and caches WAVs (a repeated sentence reuses its file; partial or corrupt files are regenerated). `engine/services/speech_queue.py` serves requests through one worker.
- Queue rules: requests carry `client_id`, `sequence` and `priority`, so each browser's latest line wins and a late cancel never cancels a newer line. Action results and dialogue go before hover descriptions and before background preparation (`background` priority). Disconnected requests leave the queue; a synthesis already running finishes and may be cached, but cancelled audio is never delivered. The queue holds at most 64 requests (429 when full). Superseded requests get 204, invalid ones 422, synthesis errors 503. The plain `text/profile/rate` request still works.
- `python engine/tools/speech_inventory.py` lists the speech literals and templates in the game code (`engine/` without tests, tools, launcher and tracking, plus `game/`) into `output/audio/speech-catalog.json`. Text passed only through variables and browser-side messages are not expanded.

### Demo voice preparation

The launcher prepares the demo lines when it starts a new server (`--prepare-demo`, used by both start scripts). For a running server, from the project environment:

```
python engine/tools/prepare_demo.py                                   # server on port 8000
python engine/tools/prepare_demo.py --server http://127.0.0.1:8003    # Windows start script port
python engine/tools/prepare_demo.py --list                            # print the lines without a server
python engine/tools/prepare_demo.py --rate 1.2                        # cache for another speech rate
```

It collects about 210 lines at rate 1.0 (fixed guidance, Rowan's tutorial and advice branches, representative actions, objects and reactions) with a temporary engine and temporary saves, then calls only `/api/speech/voices` and `/api/speech`; it never sends game input. Finished WAVs are reused and failures are listed in `output/audio/demo-ready.json`; re-running regenerates only what failed. New quantities, prices, reactions and other rates are generated on first use, and the browser still has to download and decode each file.

## Dev tools

| Command | Purpose |
|---|---|
| `python engine/tools/run_tests.py` | Every test suite (see the root README) |
| `python engine/tools/audio_flow.py` | Scripted farming, cooking, Rowan/trading, mining, fishing and save/load run through real pointer and key input on temporary saves; `--stdout` prints the JSON |
| `python engine/tools/audio_integration_lab.py` | Browser lab on `http://127.0.0.1:8001/` starting in a temporary watering scene; does not touch real saves |
| `python engine/tools/prepare_speech.py [--download]` | Download the voice models; write preview samples to `output/audio/` |
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
6. **Effects balance.** Listen to `output/audio/effects-preview.wav`, then in the game check: travel, shop entry and trading each sound once; water/fertilizer/harvest work sound, target sound and completion are distinct and a quick tap still sounds; chopping and stirring fade when you stop; mining hit, break, rare find and tool break are distinct; impossible actions play the error cue; music and effects do not cover speech; harvest and rare-find sounds are audible.
7. **Another computer.** After installing there, play **Test guide** and **Test Rowan** at the same rate and compare voice and pronunciation. Locally generated audio is not guaranteed to be bit-identical; compare the same `output/audio/` sample file when that matters.

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
19. Hardware, if available: USB pad, Bluetooth pad (with the SDK in `engine/web/core/pad/vendor/`), hand tracking server (`engine/tracking/`). The console must not show "Expected a JavaScript-or-Wasm module script" for `hardware.mjs`.
20. Demo preparation: `python engine/launcher/launch_game.py --prepare-demo` completes and `output/audio/demo-ready.json` reports the lines ready.

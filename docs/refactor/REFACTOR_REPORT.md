# Refactor report

Branch `refactor/modular-structure`, from `main` at `ea38001` (2026-10-24). Goal: split the single-file engine and page into feature modules so people and AI agents can work on one feature without touching the others, with **zero behaviour change**. Every phase had to reproduce the test baseline exactly (BASELINE.md).

Status: Phases 0–5 done. A manual play-test (checklist at the end) is still pending before a pull request. Phase 6 (installer/launcher) is a separate future PR (FOLLOWUPS F18).

## Phases

| Phase | Commits | What changed |
|---|---|---|
| 0 | `9c591a4` | Trustworthy baseline: explicit utf-8 in tests, timeout for the hanging speech-queue test, larger `spawnSync` buffer, save-compatibility test and fixture, AUDIT/BASELINE/FOLLOWUPS. Test files only. |
| 1 | `ed817b9` | `visionpad/` package, `config/`, `tests/python/<area>`, `tests/js/<area>`; root modules become aliases. No logic changes. |
| 2 | `70e6f1b`, `f0eb151`, `8b636fb` | Feature registry (one registration call per engine hotspot), named run orders, slots, attribute ownership, fixed save-key order; flowers is the first feature. |
| 3 | `af56366` … `ce953a0`, `1fff3f8`, `6d10b07` | Research, minimap, inventory, npc + village, mining, fishing + seafood, shop, cooking (food effects to core), harvest, farming, home extracted; core split into shell, time, input and render. |
| 4 | `ccdc7b7`, `2ec84b2`, `c713779`, `7b87762` | URL check and Playwright smoke test; shared players to `web/core/`, pad code to `web/core/pad/`; page script to `web/core/game.js`; feature page texts to `web/features/<name>/client.js`; feature sounds and textures next to their features; old `/static/` URLs still resolve. |
| 5 | `87de91b` … this commit | Boundaries: AGENTS.md (+ CLAUDE.md), CODEOWNERS, feature README gaps filled, `tools/run_tests.py`, README updates, refactor records in `docs/refactor/`, second-machine verification. |

## Final structure

```
visionpad/
  app/            FastAPI app factory (main.py), runtime, routes/{game,speech,static}.py
  core/           engine.py (shell), registry.py, order.py, input.py, render.py, time.py, state.py, effects.py
  display/        dotpad.py, icons.py, keypad.py
  features/       __init__.py (ENABLED) + one folder per feature:
                  cooking farming fishing flowers harvest home inventory minimap
                  mining npc research seafood shop village
                  each: __init__.py, feature.py (+ helpers), README.md
  services/       saves.py, speech.py, speech_queue.py
  spectator/      state.py
  config.py  paths.py
config/           game.json, npc.json, speech.json, tracking.json
web/
  game.html       markup and styles only
  core/           game.js, pages.js, game-audio.js, game-speech.js, game-keys.js
  core/pad/       hardware.mjs, bluetooth-pad.mjs, vendor/ (Dot Pad SDK, not committed)
  features/<name>/ client.js, audio/*.mp3, assets/*.png
  audio/          shared sounds
  spectator/      companion window (display.js is hand-edited, never regenerated)
tests/
  python/{audio,core,saves,setup,speech,support}/   js/{audio,pad,speech}/   browser/   fixtures/saves/
tools/            run_tests.py (new), audio_flow.py, check_setup.py, setup_game.py, prepare_*.py, ...
docs/refactor/    AUDIT.md, BASELINE.md, FOLLOWUPS.md, REFACTOR_REPORT.md
AGENTS.md  CLAUDE.md  .github/CODEOWNERS
```

`GameEngine` is still one object (`class GameEngine(InputDispatch, KeypadUI, SaveMixin, SharedState, FoodEffects, TimeAndSleep, Rendering)`), so every engine attribute name, and therefore the save format, is unchanged. Features register with `visionpad/core/registry.py`; `visionpad/core/engine.py` shrank from 3,465 lines (`game_engine.py`) to 363.

## Old path → new path

Root modules still exist as one-line aliases (`sys.modules[__name__] = <new module>`), checked by `tests/python/core/test_root_aliases.py`; `uvicorn game_app:app` and old imports keep working.

| Old path | New path |
|---|---|
| `game_app.py` | `visionpad/app/main.py`, `runtime.py`, `routes/game.py`, `routes/speech.py`, `routes/static.py` (alias kept) |
| `game_engine.py` | `visionpad/core/engine.py`, `input.py`, `render.py`, `time.py`, `state.py`, `effects.py`, `registry.py`, `order.py`, and the feature folders (alias kept) |
| `game_flowers.py` | `visionpad/features/flowers/feature.py` (alias kept) |
| `game_npc.py` | `visionpad/features/npc/feature.py` (alias kept) |
| `game_village.py` | `visionpad/features/village/feature.py` (alias kept) |
| `game_fishing.py` | `visionpad/features/fishing/feature.py` (alias kept) |
| `game_seafood.py` | `visionpad/features/seafood/feature.py` (alias kept) |
| engine groups in `game_engine.py` (AUDIT §2.3) | `visionpad/features/{research,minimap,inventory,mining,shop,cooking,harvest,farming,home}/` |
| `game_ui.py` | `visionpad/display/keypad.py` (alias kept) |
| `game_icons.py` | `visionpad/display/icons.py` (alias kept) |
| `dotpad.py` | `visionpad/display/dotpad.py` (alias kept) |
| `game_saves.py` | `visionpad/services/saves.py` (alias kept) |
| `game_speech.py` | `visionpad/services/speech.py` (alias kept) |
| `speech_queue.py` | `visionpad/services/speech_queue.py` (alias kept) |
| `spectator_state.py` | `visionpad/spectator/state.py` (alias kept) |
| `game_config.json`, `npc_config.json`, `speech_config.json`, `tracking_config.json` | `config/game.json`, `config/npc.json`, `config/speech.json`, `config/tracking.json` |
| `web/game.html` inline script | `web/core/game.js` + `web/features/<name>/client.js` via `web/core/pages.js` |
| `web/game-audio.js`, `web/game-speech.js`, `web/game-keys.js` | `web/core/` (old `/static/` URLs served through `LEGACY_STATIC`) |
| `web/hardware.mjs`, `web/bluetooth-pad.mjs`, `web/vendor/` | `web/core/pad/` (SDK now `web/core/pad/vendor/DotPadSDK-*`, gitignored) |
| `web/audio/{water,soil}.mp3` | `web/features/farming/audio/` |
| `web/audio/crop.mp3` | `web/features/harvest/audio/` |
| `web/audio/{cut,cook}.mp3` | `web/features/cooking/audio/` |
| `web/audio/{pickaxe,break}.mp3` | `web/features/mining/audio/` |
| `web/audio/splash.mp3` | `web/features/fishing/audio/` |
| `web/spectator/assets/items2.png` | `web/features/fishing/assets/` |
| `web/spectator/assets/flower-{backgrounds,items,stages}.png` | `web/features/flowers/assets/` |
| `web/spectator/assets/rowan.png` | `web/features/npc/assets/` |
| `test_{team_audio,gameplay_audio,sound_events,audio_flow}.py` | `tests/python/audio/` |
| `test_{speech,speech_api,speech_queue,demo_speech}.py` | `tests/python/speech/` |
| `test_startup.py` | `tests/python/setup/` |
| `test_support.py` | `tests/python/support/` |
| `test_{audio_integration,effects,fishing_audio,guidance}.cjs` | `tests/js/audio/` |
| `test_speech.cjs` | `tests/js/speech/` |
| `test_hardware.mjs`, `test_tracking_input.mjs` | `tests/js/pad/` |
| `AUDIT.md`, `BASELINE.md`, `FOLLOWUPS.md`, `REFACTOR_REPORT.md` (root, Phases 0–4) | `docs/refactor/` |
| (new) | `visionpad/features/<name>/README.md`, `tests/python/core/test_registry.py`, `tests/python/core/test_root_aliases.py`, `tests/python/saves/test_save_compat.py`, `tests/fixtures/saves/`, `tests/browser/`, `tools/run_tests.py`, `requirements-dev.txt`, `AGENTS.md`, `CLAUDE.md`, `.github/CODEOWNERS` |

Unchanged locations: `launch_game.py`, `build_display.py`, `game.bat`, `setup-*`, `start-mac.command`, `tools/*` (paths inside updated), `tracking/`, `tracking_*`, `web/spectator/*` (except moved textures), `docs/audio/`.

## Test results before and after

| | Python | Node | Other |
|---|---|---|---|
| Before Phase 0 (`ea38001`, AUDIT §1.3) | 67 collectable: 54 ok, 5 FAIL, 3 ERROR, 1 hang; 4 not collected (no fastapi); on Windows without `PYTHONUTF8` 27 more setup errors | not run (no Node) | — |
| Phase 0 baseline (test fixes only) | 70: 61 ok, 6 FAIL, 3 ERROR | 59: 57 ok, 2 FAIL | — |
| End of refactor (`tools/run_tests.py`) | 95: 86 ok, 6 FAIL, 3 ERROR. The 70 baseline tests are identical per test; the 25 new ones (registry, aliases, save order) pass | 59: 57 ok, 2 FAIL, identical per test | URL check: 82 URLs, 0 failed (2 optional SDK files missing). Smoke test: passes on the first machine; fails on the second because of F17 (machine MIME mapping), passes there with the MIME type registered. `audio_flow --stdout`: 1,128,947 bytes, same size as Phase 0. |

The 11 known non-ok results (F1 Rowan/shop dialogue ×8, F2 speech queue on Python 3.12, F3/F4 pad test files that cannot load) were deliberately left as they were.

How behaviour was checked: per-test comparison with BASELINE.md after every phase; the save-compatibility test (a pre-refactor save loads to an identical snapshot); `tools/audio_flow.py` output (161 real input responses); `/api/state` key order; on the first machine also old-vs-new comparison scripts that drove the Phase 0 worktree and the new engine with the same inputs per feature. Those scripts and the worktree were in the first machine's scratchpad and are gone; they were not recreated, so that evidence cannot be re-run.

## Behaviour notes

Places where the refactored code can behave differently from the pre-refactor engine, all outside what a player can reach.

| Topic | Before | After | Reachable in play? |
|---|---|---|---|
| `perform_action("drag_tool:<tool>", obj)` called directly | `pointer_down` handled `drag_tool:` before `perform_action`; a direct `perform_action` call with that string fell through to the generic fallback (speaks the object's label). | Farming registers `drag_tool:` as a normal action, so a direct call picks up the tool (`drag_tool` set, "Watering can. Drag to a plot.") after the same night guard. Pressing an object with that action behaves exactly as before. | No. No object offers a `drag_tool:` action (since before the split), and the HTTP API only sends pointer coordinates and key commands, never action strings. |
| Unreachable code removed vs kept | Several branches could never run (see AUDIT.md §2.4). | Kept as methods for parity where they contain speech lines, so the demo speech list is unchanged (FOLLOWUPS F14). | No. |
| Save files written with attributes a feature adds later | Key order came from `vars(self)`. | Keys follow `SAVE_KEY_ORDER` (the pre-refactor order); attributes outside it are written alphabetically after it. Current saves keep exactly the pre-refactor key order. | Only for attributes added after the refactor. |
| Old static URLs (`/static/game-audio.js`, `/static/hardware.mjs`, `/static/audio/water.mp3`, …) | Files at those paths. | Files moved; `visionpad/app/routes/static.py` (`LEGACY_STATIC`) serves the moved file at the old URL, so cached pages and bookmarks keep working. | Only with a cached old page. |
| `.mjs` served as `text/plain` on some Windows machines (F17) | Same (same `StaticFiles` mount). | Same. Not a refactor change; recorded so it is not mistaken for one. | Yes, on affected machines: the pad buttons do nothing. |

## Deviations from the plan

- Package name is `visionpad/`, not the `dotdew/` suggested in AUDIT §9.1; tests live under `tests/python/<area>` and `tests/js/<area>` instead of per feature. Per-feature test runs use the Tests row of each feature README (`tools/run_tests.py --feature`); new feature tests go in `tests/python/<name>/`, `tests/js/<name>/`.
- `GameEngine` keeps the core mixins (`InputDispatch`, `KeypadUI`, `SaveMixin`, `SharedState`, `FoodEffects`, `TimeAndSleep`, `Rendering`); all feature mixins are gone.
- Food effects became a core module (`visionpad/core/effects.py`) because every activity uses them.
- Fishing sonar stays in `web/core/game-audio.js` (F16).
- `web/spectator/display.js` is untouched and not regenerated (F5); moved textures are found through `visual-assets.json`.
- Kept for exact parity, listed for later: cross-feature writes (F13), unreachable code (F14), 44 exposed engine methods (F15), ownership declared but not enforced on writes (F11), icon sort naming the town page (F12).
- Phase 0 changed test infrastructure (encoding, a timeout, a buffer size) before the baseline was recorded; no assertion was changed.
- The old-vs-new comparison scripts were not kept in the repository (see above).
- Phase 5 added `tools/run_tests.py` (dev tooling, no game code).

## Manual play-test checklist (pending)

Run on Windows with `game.bat` (port 8003) and, if possible, on a Mac with `start-mac.command` (port 8000). Keep the browser developer console open; any red error is a finding. Use headphones.

1. Setup and start: `tools/check_setup.py` says "Setup ready"; the launcher opens the game; a second launch reuses the running server.
2. First click or key enables audio; music plays; **Test guide** and **Test Rowan** speak.
3. **Open visual display**: the companion opens and shows the home scene; it follows every step below. Check that flower images, fish and fish dishes, and Rowan (portrait, standing, equipped rod) appear (textures that moved in Phase 4).
4. Travel Farm ↔ Home ↔ Village ↔ Mine ↔ Fishing lake with the arrow keys and with the F1 map; each move speaks the place; Village first arrival: "Rowan would like to meet you."
5. Rowan quest: talk to Rowan (soup gift), receive seeds, plant, and submit a vegetable later; repeat-talk does not repeat gifts.
6. Farming: plant a seed, water and fertilize with the care minigame (water and soil sounds, target cues), sleep, see growth and the morning "ready" note.
7. Harvest a mature plot (crop sound, yield, seed recovery).
8. Cooking: choose a recipe, select ingredients, trace both stages (cut and cook sounds), stall to see the resume marker, finish the dish; eat it from the F2 inventory and see the effect.
9. Mining: hit rocks (pickaxe, break, shine sounds), mine until the pickaxe breaks (destroy sound, replacement advice), buy a new pickaxe.
10. Fishing: enter without a rod (exploration text), buy a rod, follow the water sound left/right with headphones, cast (splash, shine for rare fish), miss, break a rod.
11. Seafood: cook a fish dish and check its effect.
12. Shop: buy and sell pages, page turning, coin sound, rejection when gold is short; calendar shows the weekly market.
13. Research: buy each upgrade at the home chest; farm expansion adds plots.
14. Flowers: buy morning glory seeds, plant in the pot, water by holding the pointer over the pot, grow over days, harvest bonus while blooming.
15. Time and sleep: run out of time, return home, sleep blackout and sleep sound, next morning.
16. Menus: F1 map and F2 inventory open and close with either arrow; F3 short press opens the save list; F3 hold saves ("Game saved.").
17. Saves: load a save made before the refactor (an existing `saves/*.json` from the old version) and continue; save and reload a new one.
18. Hard-refresh the game page after a run with the old version cached; no 404s.
19. Hardware, if available: USB pad, Bluetooth pad (with the SDK in `web/core/pad/vendor/`), hand tracking server. On Windows check FOLLOWUPS F17 first: if the console shows "Expected a JavaScript-or-Wasm module script" for `hardware.mjs`, the pad buttons cannot work on that machine.
20. Demo preparation: `python launch_game.py --prepare-demo` completes and `output/audio/demo-ready.json` reports the lines ready.

# AGENTS.md

Working rules for people and AI agents in this repository. `CLAUDE.md` points here; this file is the single source.

The game server is one `GameEngine` (`engine/core/engine.py`) with features plugged in through a registry (`engine/core/registry.py`). Each feature lives in its own folders and describes itself in `game/<name>/README.md`. Background: `docs/refactor/` (audit, test baseline, follow-ups, refactor report).

## Who owns what

A task for feature **X** may edit only:

| Path | Notes |
|---|---|
| `game/X/` | Server code and the feature README. Keep the README's table current. |
| `game/X/client.js` | What the game page shows for X's pages (`DotdewPages.register`, see `engine/web/core/pages.js`). |
| `engine/tests/python/X/`, `engine/tests/js/X/` | Feature tests. A new Python test folder needs an empty `__init__.py`. Name new test files in the README's Tests row. |
| X's section of `engine/config/game.json` | Adding keys X reads. Changing existing values (prices, timings, balance) needs approval. |

Everything else needs **explicit approval** from the owner before it is changed:

| Path | Why |
|---|---|
| `engine/core/` (engine, registry, `order.py`, input, render, time, state, effects) | Every feature depends on it. New run orders go in `order.py`. |
| `engine/display/` (Dot Pad matrix, icons, keypad), `engine/spectator/` | Shared drawing and public state. |
| `engine/services/` (saves, speech, speech queue) | Save format and speech pipeline. |
| `engine/server/` (FastAPI app, routes, static fallback map) | HTTP API used by the page and the launcher. |
| `game/__init__.py` | The `ENABLED` list: adding a feature is one line here. |
| `engine/config/__init__.py`, `engine/paths.py`, `engine/config/*.json` outside your section, any config **value** | Shared settings. |
| Saves: attribute names, `SAVE_KEY_ORDER`, `engine/tests/fixtures/saves/` | The save format (see below). Never edit the fixtures. |
| Assets: every `.mp3` and `.png`, including `game/X/audio/` and `game/X/assets/`; `engine/web/spectator/visual-assets.json`, `scene-objects.json` | Binaries are committed without LFS (FOLLOWUPS F9). A new sound also needs entries in `engine/web/core/game-audio.js` (`FEATURE_SOUND_URLS` and the sound list) and `engine/launcher/check_setup.py` (`ASSETS`, `FEATURE_SOUNDS`). |
| `engine/web/spectator/display.js` | Hand-edited bundle. Never regenerate it with `engine/tools/build_display.py` (FOLLOWUPS F5). |
| `engine/web/core/`, `engine/web/game.html`, `engine/web/spectator/` (other files) | Shared client. A new `game/X/client.js` needs one script tag in `engine/web/game.html`. |
| `engine/tests/python/{audio,core,saves,setup,speech,support}/`, `engine/tests/js/{audio,pad,speech}/`, `engine/tests/browser/` | Shared tests. Adding a test here is fine with approval; never change an existing assertion to make it pass. |
| `docs/refactor/BASELINE.md` | Expected results. Add an addendum for new tests; changing a known result needs approval. |
| `engine/tools/`, launchers (`engine/launcher/launch_game.py`, `start-windows.bat`, `setup-*`, `start-mac.command`), `requirements*.txt` | Setup and launch (Phase 6 will replace these). |
| `engine/tracking/`, `tracking_*` | Camera tracking; not installed or testable in the default setup. |

`.github/CODEOWNERS` mirrors this table for review requests.

## Game state and saves

- **Never rename or remove engine attributes.** Their names are the save-file keys (`engine/services/saves.py`, `engine/tests/python/saves/test_save_compat.py`); a rename breaks every existing save.
- A feature declares the attributes it owns with `reg.owns(...)`. Write only your own attributes; shared state goes through the helpers in `engine/core/state.py` (`set_page`, `resource`, `add_resource`).
- A new attribute is a save-format change (approval): own it, set it in your `reset` handler, and list it in `reg.save_fields(defaults=...)` so older saves load. Transient values (drag flags, deadlines) use `transient=` or `clock=`.
- Do not change behaviour while restructuring: player-visible text, sounds, timing, random draws and `/api/state` keys stay identical unless the task says otherwise.

## Connecting features

- Prefer **events** (`reg.on(...)`, `registry.run(...)`; list in `EVENTS`, `engine/core/registry.py`) and **slots** (`reg.slot(...)`, `reg.contribute(...)`) for anything one feature needs from another. Pass run orders from `engine/core/order.py`, never a bare number.
- Use `reg.expose(name, fn)` only for:
  - methods that tests or tools call on the engine (`engine.talk_rowan()`), or
  - paired features that already depend on each other (npc ↔ village, cooking ↔ seafood, farming ↔ harvest).
- Every exposed name is listed with its owner in `engine/tests/python/core/test_registry.py` (`ExposeTests.EXPECTED`). Adding one fails that test until the list is updated, so it shows up in review. The goal is fewer, not more (FOLLOWUPS F15).
- When a feature calls another feature's exposed method, list it under "Engine API used" in the calling feature's README.

## Feature README

Each `game/<name>/README.md` is one table. Keep these rows accurate when you change the feature: Code, Pages, Actions, Object types, Owned engine attributes, Shared attributes written/read, Events, Slots, State keys, Saves, Engine API provided, Engine API used, Config, Client (web), Tests. Write "none" rather than leaving a row out. The Tests row lists full paths; `engine/tools/run_tests.py --feature <name>` runs exactly those files.

## Before you finish: run the tests

From the repository root, inside the project environment (`.venv`, Python 3.11+; Node.js 20+ for the JS tests):

```
# Windows
.venv\Scripts\python.exe tools\run_tests.py --feature X     # the feature you changed (repeat --feature for several)
.venv\Scripts\python.exe tools\run_tests.py                 # everything: Python, Node, URL check, browser smoke test

# macOS / Linux
.venv/bin/python engine/tools/run_tests.py --feature X
.venv/bin/python engine/tools/run_tests.py
```

- Done means the last line reads `All results match docs/refactor/BASELINE.md (known failures included).` The 11 known failures (FOLLOWUPS F1–F4) are expected; do not fix them in an unrelated task.
- The browser checks need `pip install -r engine/requirements-dev.txt` and `python -m playwright install chromium`; `--no-browser` skips them. On Windows the smoke test fails when the registry maps `.mjs` to `text/plain` (FOLLOWUPS F17); that is the machine, not your change.
- Report the exact command and its final lines. If a result differs, say so; do not edit the baseline to match.

## Commits

- One logical change per commit, with a summary line that says what changed (not "로직수정" or "update").
- Work on a branch and merge through a pull request; do not push to `main` directly.

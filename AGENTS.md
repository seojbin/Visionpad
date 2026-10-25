# AGENTS.md

Rules for people and AI agents working in this repository. `.claude/CLAUDE.md` points here; this file is the single source.

The game is one `GameEngine` (`engine/core/engine.py`) with features plugged in through a registry (`engine/core/registry.py`). Shared code is in `engine/` ([engine/README.md](engine/README.md)); each feature is one folder in `game/` ([game/README.md](game/README.md)) with its own README.

## Who may edit what

- **A task for feature X edits only `game/X/`**: its Python code, `client.js`, tests in `game/X/tests/` and its README.
- **`engine/` needs explicit approval** from the owner before any change, including configuration values in `engine/config/`, the browser player, the companion window, launcher, tools and shared tests.
- Also needs approval although it sits outside `engine/`: `game/__init__.py` (the `ENABLED` list and its order), sounds and images (`game/X/audio/`, `game/X/assets/`; binaries are committed without LFS), the root `install-*` and `start-*` files, `README.md`, `README.ko.md` and this file.
- Never edit or regenerate `engine/web/spectator/display.js` (hand-edited bundle, follow-up F5) or the save fixtures in `engine/tests/fixtures/saves/`.
- When a feature task needs an engine change (a new event, slot, script tag in `engine/web/game.html`, sound registration, config key), stop and ask; describe the smallest change.

These rules are guidance for people and agents; nothing in the repository enforces them.

## Game state and saves

- **Never rename or remove engine attributes.** Their names are the save-file keys (`engine/services/saves.py`); a rename breaks every existing save. `engine/tests/python/saves/test_save_compat.py` loads a pre-refactor save to guard this.
- A feature declares the attributes it owns with `reg.owns(...)` and writes only those; shared state goes through `engine/core/state.py` (`set_page`, `resource`, `add_resource`).
- A new attribute changes the save format (approval): own it, set it in the `reset` handler, list it in `reg.save_fields(defaults=...)` so older saves load; transient values use `transient=` or `clock=`.
- Do not change gameplay while restructuring: player-visible text, sounds, timing, random draws and `/api/state` keys stay identical unless the task asks for it.

## Connecting features

- Prefer **events** (`reg.on`, `registry.run`; the list is `EVENTS` in `engine/core/registry.py`) and **slots** (`reg.slot`, `reg.contribute`) over `reg.expose`. Pass run orders from `engine/core/order.py`, never a bare number.
- Use `reg.expose(name, fn)` only for methods tests or tools call on the engine, or for paired features that already depend on each other (npc ↔ village, cooking ↔ seafood, farming ↔ harvest). Every exposed name is listed with its owner in `engine/tests/python/core/test_registry.py` (`ExposeTests.EXPECTED`), so a new one fails that test until it is reviewed. The goal is fewer (follow-up F15).
- List other features' exposed methods you call under "Engine API used" in your README.

## Feature README

Each `game/X/README.md` is a table: Code, Pages, Actions, Object types, Owned engine attributes, Shared attributes written/read, Events, Slots, State keys, Saves, Engine API provided/used, Config, Client (web), Tests. Write "none" rather than leaving a row out. The Tests row lists shared test files by full path; `engine/tools/run_tests.py --feature X` runs those plus `game/X/tests/`.

## Before you finish: run the tests

From the repository root, with the project environment (`.venv`, Python 3.11+; Node.js 20+):

```
# Windows
.venv\Scripts\python.exe engine\tools\run_tests.py --feature X     # the feature you changed (repeat --feature for several)
.venv\Scripts\python.exe engine\tools\run_tests.py                 # everything: Python, Node, URL check, browser smoke test

# macOS / Linux
.venv/bin/python engine/tools/run_tests.py --feature X
.venv/bin/python engine/tools/run_tests.py
```

- Done means the last line reads `All green.` Known failures are marked in the tests (`@unittest.expectedFailure` or a node `todo`, each with its follow-up ID and reason) and listed at the end of the run. Do not fix them in an unrelated task. If your change makes one pass, the run fails: remove that marker in the same change and say so.
- The browser checks need `pip install -r engine/requirements-dev.txt` and `python -m playwright install chromium`; `--no-browser` skips them (then say so).
- Report the exact command and its final lines. Never weaken an assertion to make a test pass.

## Commits

- One logical change per commit, with a summary line that says what changed (not "로직수정" or "update").
- Work on a branch and merge through a pull request; do not push to `main` directly.

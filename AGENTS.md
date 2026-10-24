# AGENTS.md

Working rules for people and AI agents in this repository. Phase 5 of the refactor completes this file; until then it holds the rules agreed during the split.

## Connecting features

- Prefer **events** (`reg.on(...)`, `registry.run(...)`) and **slots** (`reg.slot(...)`, `reg.contribute(...)`) for anything one feature needs from another.
- Use `reg.expose(name, fn)` only for:
  - methods that tests or tools call on the engine (`engine.talk_rowan()`), or
  - paired features that already depend on each other (npc ↔ village).
- Every exposed name is listed with its owner in `tests/python/core/test_registry.py` (`ExposeTests.EXPECTED`). Adding one fails that test until the list is updated, so it shows up in review.
- When a feature calls another feature's exposed method, list it under "Engine API used" in the calling feature's README.

## Game state

- Never rename or remove engine attributes: their names are the save format (`visionpad/services/saves.py`, `tests/python/saves/test_save_compat.py`).
- A feature declares the attributes it owns with `reg.owns(...)`.

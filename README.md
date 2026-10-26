# Dotdew Valley

English | [한국어](README.ko.md)

A farming and life simulation game for the Dot Pad, a 60×40 tactile display. Blind and low-vision players read the world by touch and sound and act directly on the surface they are reading: farm, cook, mine, fish, trade and research across home, farm, village, mine and a fishing lake. Shapes and English speech guide the player; Braille literacy is not required.

A browser simulator supports mouse and keyboard. A USB or Bluetooth Dot Pad and an external hand-tracking camera can be connected, and a separate Visual Companion window shows the same game with images for low-vision players and companions.

## Install

Install Python 3.11 or newer (3.12 64-bit recommended; the Windows installer uses 3.12 when it is present), then open **install-windows.bat** (Windows) or **install-mac.command** (macOS) once. It creates `.venv/` in the project, installs `engine/requirements.txt` and downloads the two English voices into `.audio/voices/`, checking each file's size and SHA-256 (an interrupted or damaged download is fetched again; run the installer again after an error). Nothing is installed globally. Internet is needed for this step; no account or API key is used. For the Bluetooth Dot Pad, run the installer with `--with-pad` (for example `install-windows.bat --with-pad`) to also download Dot Inc.'s SDK; the game, the USB pad and hand tracking work without it.

Manual install from the project folder:

```
python -m venv .venv
.venv\Scripts\activate                 # macOS / Linux: source .venv/bin/activate
python -m pip install -r engine/requirements.txt
python engine/tools/prepare_speech.py --download
```

`python engine/launcher/check_setup.py --synthesize` diagnoses packages, files, sounds and voices without starting a game. Settings files are read as UTF-8 whether or not an editor saved them with a byte-order mark, and the Windows scripts run Python in UTF-8 mode, so a Korean (cp949) Windows code page does not matter.

## Start

Open **start-windows.bat** (http://127.0.0.1:8003) or **start-mac.command** (http://127.0.0.1:8000), or run `python engine/launcher/launch_game.py --prepare-demo` (port 8000). The launcher checks the setup, starts or reuses the game server, prepares the demo voices and opens the browser. Keep its window open while playing.

1. Click or press a key on the game page to enable audio.
2. Select **Open visual display** for the companion window (allow pop-ups).
3. Hold F3 to save; the server forgets the game when it stops. Saves are in `saves/`.

## Controls

| Input | Action |
|---|---|
| Hover | Hear an object's name and state |
| Click, Enter, F4 | Select, use a facility, strike a rock, cast |
| Move over targets or paths | Water, fertilize, harvest, trace a cooking path |
| F1 / F2 | Map / inventory; press again to return |
| F3 short / hold | Open the save list / save to a new slot |
| Left / right arrows or pad buttons | Travel, go back or turn a page |
| W A S D (Shift for larger steps) | Move the pointer |
| Space | Toggle pressed/released |
| Shift push | detail tts mode |

Locations run Farm ↔ Home ↔ Village ↔ Mine ↔ Fishing lake. Exploring and travelling cost no game time; hovering never triggers an action.

## Folders

| Folder | What is in it |
|---|---|
| `engine/` | Shared code: server, engine core, Dot Pad display, saves, speech, browser player (audio, keys, pad), Visual Companion, configuration, launcher and installer logic, camera tracking, dev tools and shared tests. See [engine/README.md](engine/README.md). |
| `game/` | One folder per feature (cooking, farming, fishing, flowers, harvest, home, inventory, minimap, mining, npc, research, seafood, shop, village) with its Python code, browser texts, sounds, images, tests and README. See [game/README.md](game/README.md). |
| `install-*`, `start-*` | Thin wrappers that call `engine/launcher/`. |
| `.audio/`, `saves/` | Created when you install and play, not committed: voices, speech cache and audio reports; saved games. Voices and cache from older versions (`models/`, `.cache/`, `output/`) are moved into `.audio/` automatically. |
| `AGENTS.md` | Rules for people and AI agents: who owns which folder, what needs approval, the save format. |

## Add a feature

1. Create `game/<name>/` with `feature.py` (a `Feature` subclass whose `register(reg)` declares pages, actions, drawings, state and events through `engine/core/registry.py`) and `__init__.py` exporting it as `Feature`.
2. Add `<name>` to `ENABLED` in `game/__init__.py`.
3. Optional: `client.js` (page texts), `audio/`, `assets/`, a section in `engine/config/game.json`, tests in `game/<name>/tests/`, and a README.

Step 2, config values, sounds, images and any `engine/` change need approval. A worked example is in [game/README.md](game/README.md); the rules are in [AGENTS.md](AGENTS.md).

## Tests

```
.venv\Scripts\python.exe engine\tools\run_tests.py                   # everything
.venv\Scripts\python.exe engine\tools\run_tests.py --feature fishing # one feature
```

On macOS/Linux use `.venv/bin/python engine/tools/run_tests.py`. It runs the Python and Node tests (Node.js 20+) and the browser checks (`--no-browser` skips them; they need `pip install -r engine/requirements-dev.txt` and `python -m playwright install chromium`). The last line must read **All green.** Known failures are marked in the tests and listed with their reason.

## License note

Speech uses [Piper](https://pypi.org/project/piper-tts/) (GPL-3.0-or-later) with the `en_US-hfc_female-medium` and `en_US-hfc_male-medium` voice models, whose training data is licensed CC BY-NC-SA 4.0: **non-commercial use only**. The models are downloaded at install time and are not part of this repository. Sources: [engine/README.md](engine/README.md#voices-and-their-sources).

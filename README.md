# Dotdew Valley

English | [한국어](README.ko.md)

A farming and life simulation game for the Dot Pad, a 60×40 tactile display. Blind and low-vision players read the world by touch and sound and act directly on the surface they are reading: farm, cook, mine, fish, trade and research across home, farm, village, mine and a fishing lake. Shapes and English speech guide the player; Braille literacy is not required.

A browser simulator supports mouse and keyboard. A USB or Bluetooth Dot Pad and an external hand-tracking camera can be connected, and a separate Visual Companion window shows the same game with images for normal players and companions.

## Contents

- [Proposal](#proposal)
- [Install and start](#install)
- [Controls](#controls)
- [Gameplay guide](#playing-the-game)
- [Folders](#folders)
- [System and configuration](#system-structure)
- [Further development](#further-development-and-evaluation)
- [Add a feature](#add-a-feature)
- [Tests](#tests)

## Proposal

Dotdew Valley adapts everyday farming-game activities, inspired by Stardew Valley, to a surface that can be explored by touch. Players find an object, hear what it is, and perform the activity in the same space. The tactile game is playable without the companion window.

| Channel | Role |
|---|---|
| Touch | Position, shape, routes, growth and task progress |
| Speech and sound | Names, quantities, results and directional guidance |
| Visual Companion | Images, larger quantities and selection highlights for low-vision players and companions |
| Buttons | Travel, menus, selection and saves |
| Pointer or tracked hand | Explore, sweep targets, trace paths and select objects |

Farming, cooking, mining, fishing, trading, research, Rowan's tutorial quests and a houseplant are implemented. Ranching, pets, music, crafting and additional NPCs are planned, and artwork for these expansions has been prepared.

## Install

Install Python 3.11 or newer (3.12 64-bit recommended; the Windows installer uses 3.12 when it is present), then open **install-windows.bat** (Windows) or **install-mac.command** (macOS) once. It creates `.venv/` in the project, installs `engine/requirements.txt` and downloads the two English voices into `.audio/voices/`, checking each file's size and SHA-256 (an interrupted or damaged download is fetched again; run the installer again after an error). Nothing is installed globally. Internet is needed for this step; no account or API key is used. For the Bluetooth Dot Pad, run the installer with `--with-pad` (for example `install-windows.bat --with-pad`) to also download Dot Inc.'s SDK; the game, the USB pad and hand tracking work without it.

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
| W A S D | Move the pointer one dot at a time while the canvas has focus |
| Space | One selection at the pointer, like F4 (outside focused form controls) |
| Hold Shift | detailed TTS mode; release to return to normal movement |

Travel runs Farm ↔ Home ↔ Village, with separate up/down controls in the village for the mine and lake. Travelling costs no game time. Hovering over an ordinary object reads its information; inside a movement-based minigame, moving over a target advances the task. Hold Shift to inspect without advancing it. F4 currently acts as a click substitute. The original pause route remains in the code for use when gesture-based selection becomes available.

## Playing the game

### Navigation and the lower panel

Use Left and Right to travel along **Farm ↔ Home ↔ Village**. Arrival speech names the destination; an unavailable direction gives a short message. F1 opens the minimap: explore its nodes and select a destination. The filled node marks the current location. In the village, use the separate on-screen up/down controls to reach the **mine** and **lake**.

The menu window that turns on the device is displayed above the current region; pressing the same key again in the F1 or F2 menu returns you to the current region. The menu does not overlap even when navigating through other menus. In menus without multiple pages, the right arrow key can also be used to go back. The minimap that appears when you press F1 and the save file list that appears when you press F3 can also be navigated back to the previous screen using the arrow keys. 

If there are multiple pages, the arrow keys in the inventory that appear when pressing F2 are for page navigation only, and the end indicates the first and last page. Therefore, use the arrow keys to navigate inventory, and only use the arrow keys to leave the page or the F2 key to close it.

Each shop consists of three levels (Town - Shop Selection Page - Buy/Sell Page). In Buy/Sell, if a page allows navigation beyond two pages, page switching takes priority; on the Buy/Sell page, the arrow key that leaves the page scroll activates the back button, leading to the shop selection screen, while the arrow key on the shop selection screen takes you to the town.

For screens with few icons, such as villages and houses, create a detailed display at the bottom. On the display, you can select objects just like with the buttons, and move them using arrow indicators. At this time, the objects selectable on the display were rendered as fully filled recessed shapes, unlike the road and detail parts, to distinguish them from the general background.

The lower 20-cell panel normally shows activity time. On a multi-page list it becomes a page-position strip: the width is divided by the page count and the current segment is raised. On a single-page shop screen it displays Braille **shop**, **buy** or **sell** to indicate the current menu depth. Pagination takes priority over that label; sleep blanks the panel.

Hold Shift in the demo, or use the pointing gesture with hand tracking, to hear detailed speech about the current location and the object under the pointer.

### Inventory and item recognition

Press F2 to check belongings. The first page holds gold and usable items. Additional food pages come first when needed, followed by seeds, crops, fish, minerals and tools. Empty items are hidden and each page holds up to 12 entries in three rows of four. Select food to eat it; other inventory entries are for inspection, not direct use.

The current tactile renderer uses a single-line rectangular frame for ordinary items, gold and NPCs. Usable food has two nested rectangular outlines with no central symbol. Seeds, crops, minerals and tools have category symbols inside their frames. The shared grid keeps objects in predictable slots. The companion uses image cards and quantities, rather than reproducing every tactile frame.

### Home, time and sleep

At home, select the bed to sleep, the research station to buy an upgrade, the kitchen to cook or **Flower pot** to tend the houseplant. A new game starts with 60 gold, two fertilizer, crop seeds and three of each vegetable for cooking.

Time is measured in ticks consumed by activities. The current day allows 20 ticks: planting, watering, fertilizing, breaking a rock and casting each cost 2; harvesting, research and cooking cost 3. Travelling costs 0. Individual mine hits cost nothing until the rock breaks. Food can change the time cost.

When time runs out, the player returns home and must select the bed. Sleep blanks the tactile panels for two seconds and pauses the music. The next morning, watered crops grow, the houseplant updates and mine rocks refresh. The companion also follows the time of day and sleep transition.

### Farming: plant, water, fertilize and harvest

1. Travel to the farm and select a plot. A plot's interior fills from the bottom as its crop grows.
2. On an empty plot, choose planting and select an owned seed. On a planted plot, check its growth, water and fertilizer state.
3. Choose watering or fertilizing and sweep over the target dots. Holding a click is not required.
4. Sleep after watering to advance growth. Fertilizer immediately advances growth by one day; it is an optional aid.
5. Once mature, choose harvest and pass every crop target. There is no time limit or score-based yield multiplier. Basic yield, food effects and any flower bonus determine the result. Seed recovery, improved through research, is checked separately and may return seeds.

Care dots and cooking traces remain briefly after contact, then disappear. The current delay is 200 ms, configurable to 1000 ms for a one-second tactile reading interval. Completion waits for the applicable delayed display to finish.

### Cooking and food effects

Choose a recipe in the kitchen, then select its ingredients. Selecting every required ingredient starts cooking automatically. Trace from the start marker through both stages in order. If progress stops, a 4x4 square marker shows where to resume. Ingredients and cooking time are consumed after the completed dish, not after the first stage; no time limit is imposed.

The first stage depends on the ingredient: a horizontal preparation path for fish or a vertical chopping path for vegetables. The second stage depends on the cooking method. Frying, grilling and stirring soup are currently implemented.

| Vegetable dish | Ingredients (one each) | Effect | Duration |
|---|---|---|---|
| Tomato carrot stew | Tomato, carrot | Harvest boost | 6 game hours |
| Potato tomato soup | Potato, tomato | Pickaxe protection | 10 game hours |
| Vegetable fritters | Potato, carrot | Time saving | 10 game hours |

| Fish dish | Vegetable | Eligible fish | Effect |
|---|---|---|---|
| Grilled fish | Potato | Mackerel, carp, salmon | Better chances of iron, diamonds and rare fish; 12 / 14 / 16 hours |
| Fish stew | Tomato | Sardine, catfish, rainbow trout | Better selling prices for 3 / 4 / 5 sales |
| Fried fish | Carrot | Bass, flounder | Chance of double finds for 12 / 14 hours |

Fish dishes are named **Simple**, **Ordinary** or **Luxurious** according to the rarity of the fish used, which also determines the strength of the effect. Descriptions show duration or remaining sales, without exposing the probability or multiplier. Eat food from F2 to apply it. Only one food effect is active; eating another replaces it. Timed effects decrease with consumed game time, while a sale effect loses a charge only after a successful sale.

### Mining

Enter the mine and select a rock to strike it. A pickaxe is required to hit, but not to enter. The shop sells one at a time; buy a replacement when it breaks. Up to seven spaced rocks appear per day, normally taking three hits each. Their interiors lose dots in fixed damage patterns while their borders remain readable. After the ninth strike, the pickaxe’s break chance increases by 5 percentage points per strike.

Each broken rock yields stone, copper, iron or diamonds according to its drop probabilities. Research and food may improve the result. Hit, rock break, rare find and tool destruction have different sounds; a tool-breaking hit uses the destruction sound instead of the ordinary hit/break sound. Tool durability and drop probabilities are not disclosed during play.

### Fishing

The fishing lake is beside the mine. Entry is free without equipment, but casting requires a fishing rod (base price 100 gold, one owned at a time). Use stereo headphones and move towards the looping water sound. It is positioned relative to the pointer and becomes louder near the hidden target. The tactile outline marks the lake; the companion does not reveal the accuracy zones. Moving closer to the target improves the chance of a rare fish and reduces the chance of a miss compared with casting far away.

Click, Enter or F4 casts once inside the lake. Both a catch and a miss use 2 ticks and move the target; holding does not cast repeatedly. Input outside the circular lake boundary is ignored. A catch plays splash, with shine added for a rare fish. The lake keeps basic music at a reduced level; speech does not lower the exploration water sound. Rod use is counted only on successful catches. Starting with the fifth successful catch, its break chance increases by 10 percentage points per catch.

| Fish | Base sale price | Cooking use |
|---|---:|---|
| Sardine / mackerel / bass | 24 each | Stew / grill / fry |
| Carp / catfish / flounder | 27 each | Grill / stew / fry |
| Salmon / rainbow trout | 36 each | Grill / stew |

### Shop and the weekly calendar

Select the village shop, then Sell, Buy or Calendar. Hover an item to check its price and owned quantity; select it to trade one. The shop sells crop seeds, fertilizer, tools, selected minerals and morning glory seeds, and buys eligible crops, food, fish and minerals. Lists use pages rather than scrolling. Calendar speaks today's offer only, without opening another page.

| Day | Offer |
|---|---|
| Monday | Ore purchases 20% off |
| Tuesday | Cooked food sells for 20% more |
| Wednesday | Fish sells for 20% more |
| Thursday | Crop seeds 20% off |
| Friday | Ore sells for 20% more |
| Saturday | Fertilizer, pickaxes and rods 20% off |
| Sunday | All eligible sales earn 20% more |

Day 1 is Monday. Prices are rounded down after each applicable multiplier; food sale bonuses also affect the shown price and the paid amount.

### Rowan and tutorial quests

Rowan stands beside the shop. Select him to hear his dialogue without leaving the village; only quest item submission opens a separate selection page. The companion overlays his portrait and text. Hover speech does not replace an active quest line; a new dialogue replaces the previous dialogue.

The first conversation gives **Rowan's soup**, with the stew's harvest effect. Eat it from F2 or sell it (base value 100 gold), then return to receive one seed of each crop. Talk again for the farming tutorial and vegetable request. Select any owned crop in the submission page to give one and receive 100 gold; either arrow cancels. Gifts, rewards and quest progress are saved. Later advice and reactions to recent activities use Rowan's voice.

To fix the lock where users had zero gold or no crops to plant and could no longer earn money, Rowan was set to give out free carrot seeds if no seeds were held.
### Research

Select the research station at home, inspect an upgrade and select it to pay its gold and material cost. The list uses three columns. Research consumes game time, and its progress is saved. More upgrades are planned.

| Upgrade | Materials | Result |
|---|---|---|
| Seed recovery | Gold and copper | Better seed recovery, up to two levels |
| Farm expansion | Gold and stone | Two initial plots, up to six |
| Mineral luck | Gold and iron | Better mineral rolls and bonus quantities, up to two levels |

Gameplay descriptions report research levels rather than exact probabilities.

### Flower pot

Buy morning glory seeds for 150 gold and select **Flower pot** at home to plant. This is mainly a decorative activity: it costs a substantial amount of gold for a modest practical benefit. The small home drawing and the enlarged detail drawing show sprout, stem, flower or wilted states. The detail page has watering and empty-pot controls above the plant.

A blooming plant grants a hidden effect. Morning glory adds one crop to each harvest while in bloom.

Choose water, then keep the pointer on the actual pot area for a total of three seconds. Clicking is unnecessary; contact time, not a path score, determines completion. Water each day and sleep to grow the plant: two watered nights to a stem and two more to a flower. A blooming plant stays in bloom rather than returning to a stem, but becomes more likely to wilt as it ages. Missing water adds risk. A wilted plant cannot be watered and must be emptied before planting again. Hidden bloom benefits and wilt probabilities are not announced in play. Morning glory is the currently playable plant; images for other seeds are planned.

### Save and load

Hold F3 for 0.8 seconds to save into a new file. **Game saved.** plays while the button is held; releasing it leaves the current screen unchanged. A short press opens the save list; select a slot to restore it.

The latest 12 JSON saves are kept in `saves/`; older slots are removed. Gold, items, day, plots, research, food effects, quests, mine/fishing state and the houseplant are restored. Older formats receive defaults and feature migrations. Connections, camera calibration and browser audio preferences are separate. Save before shutting down: the server's in-memory game is not an automatic persistent save.

## Folders

| Folder | What is in it |
|---|---|
| `engine/` | Shared code: server, engine core, Dot Pad display, saves, speech, browser player (audio, keys, pad), Visual Companion, configuration, launcher and installer logic, camera tracking, dev tools and shared tests. See [engine/README.md](engine/README.md). |
| `game/` | One folder per feature (cooking, farming, fishing, flowers, harvest, home, inventory, minimap, mining, npc, research, seafood, shop, village) with its Python code, browser texts, sounds, images, tests and README. See [game/README.md](game/README.md). |
| `install-*`, `start-*` | Thin wrappers that call `engine/launcher/`. |
| `.audio/`, `saves/` | Created when you install and play, not committed: voices, speech cache and audio reports; saved games. Voices and cache from older versions (`models/`, `.cache/`, `output/`) are moved into `.audio/` automatically. |
| `AGENTS.md` | Rules for people and AI agents: who owns which folder, what needs approval, the save format. |

## System structure

The FastAPI server owns game state and validates actions. The browser sends pointer and key events, then receives dot matrices, public state, speech and sound events. USB, Bluetooth, mouse, keyboard and camera input feed the same game input path. The companion receives public state and never sends gameplay commands.

### Shared engine

| Path | Responsibility |
|---|---|
| `engine/server/main.py`, `engine/server/` | FastAPI app; game/static pages, state, input, command, visual-tick and speech routes |
| `engine/core/engine.py`, `registry.py`, `order.py` | One game instance; feature registration and event order |
| `engine/core/input.py`, `state.py`, `render.py` | Input dispatch, shared resource/page helpers, response and drawing coordination |
| `engine/core/time.py`, `effects.py` | Activity time, sleep, lower panel, food modifiers |
| `engine/display/icons.py`, `keypad.py`, `dotpad.py` | Three-row/four-column icon slots, frames, navigation and dot drawing |
| `engine/services/saves.py` | File slots, serialization and older-save compatibility |
| `engine/services/speech.py`, `speech_queue.py`, `audio_files.py` | Piper synthesis, cache, prioritized requests and runtime audio storage |
| `engine/spectator/state.py` | Public scene and object data for the companion |
| `engine/config/` | Rules, NPC dialogue, speech profiles and camera configuration |
| `engine/launcher/` | Installation, diagnostics, optional SDK preparation and server launch |
| `engine/tools/`, `engine/tests/` | Voice preparation, audio diagnostics and shared tests |

### Game features

Each folder's README documents its pages, actions, state, events, configuration and tests. Most behavior is in `feature.py`; farming additionally separates care, drawing and trading code.

| Folder under `game/` | Responsibility |
|---|---|
| `home/`, `minimap/` | Home facilities, location nodes and travel selection |
| `farming/`, `harvest/` | Plot state, planting, water/fertilizer activities, growth and harvest |
| `cooking/`, `seafood/` | Recipes, ingredient selection, paths and fish-dish variants |
| `mining/`, `fishing/` | Rocks, catches, tool wear and resource prices |
| `flowers/` | Pot interaction, daily plant state and bloom contribution |
| `inventory/`, `shop/` | Item lists, pagination and transactions |
| `research/` | Upgrade costs, levels and plot expansion |
| `village/`, `npc/` | Village, tutorial progression, submission, weekly prices, dialogue and reactions |

Features register with `engine/core/registry.py`; `game/__init__.py` selects the enabled features. They contribute items and drawings through slots and react through events. Save compatibility depends on existing engine attribute names: renaming one can change the save format.

### Browser, pad and hand tracking

| Path | Responsibility |
|---|---|
| `engine/web/game.html` | Simulator page and controls |
| `engine/web/core/game.js` | Pointer queue, state drawing, detail mode, speech/audio dispatch and companion updates |
| `engine/web/core/pages.js`, `game/<feature>/client.js` | Feature-specific browser text and hooks |
| `engine/web/core/game-keys.js` | F-key/arrow handling and F3 hold detection |
| `engine/web/core/game-audio.js`, `game-speech.js` | Effects/music/spatial playback and server speech playback |
| `engine/web/core/pad/hardware.mjs` | USB Web Serial, pad buttons and tracking WebSocket client |
| `engine/web/core/pad/bluetooth-pad.mjs` | Optional Dot Inc. Bluetooth SDK connection |
| `engine/tracking/` | Camera tracking, calibration and WebSocket server |

The pad raises dots and sends buttons; it does not itself sense fingertip coordinates. The camera uses MediaPipe and ArUco markers to map a fingertip to pad coordinates. Install `opencv-python`, `mediapipe`, `numpy` and `websockets` in the project environment for tracking; these are separate from the game requirements. Start `python engine/tracking/tracking_server.py` or its Windows `.bat`; `tracking_test.py` provides a preview. Configure it in `engine/config/tracking.json` (default WebSocket port 8765). A coordinate-only source can use F4 for selection.

Bluetooth requires SDK 3.0.3 and its dependencies in `engine/web/core/pad/vendor/`, prepared by `--with-pad` or `python engine/launcher/prepare_pad.py`. USB does not require that SDK. Browser support and device permissions must be checked on the target computer. Serve HTML through the application, not as a local file. After web changes, hard-refresh and reopen the companion.

### Visual Companion and images

Select **Open visual display** to open the read-only window and keep the game tab open. It follows places, selections, activity progress, catches, dialogue, plant stages and time of day. Each plot and mine rock corresponds to its game object. Inventory and shop cards use the same page contents as the tactile view.

| Under `engine/web/spectator/` | Responsibility |
|---|---|
| `standalone.html`, `boot.js` | Window entry and startup integration |
| `display.js` | Bundle loaded by the current display |
| `viewer.js`, `model.mjs`, `viewer.css` | Scene drawing, state-to-layout mapping and interface styles |
| `visual-assets.json` | Backgrounds, facilities, items and sprite rectangles |
| `scene-objects.json` | Facility positions, sizes and order |
| `assets/` | Shared atlases; feature art also lives in `game/<feature>/assets/` |

Backgrounds, facilities and item registrations are separate so existing art can be reused. Unknown pages fall back to the dot view; an item without art uses a name card. Keep existing atlases when adding assets. **Do not regenerate or edit `display.js` under the current repository rules:** it contains hand edits not yet reconciled with the source files (follow-up F5). The older instruction to rebuild it with `build_display.py` no longer applies.

### Audio and speech

`GameAudio` plays music, work loops, rewards, one-shots and synthetic cues. Shared recordings are in `engine/web/audio/`; feature recordings are in `game/<feature>/audio/`. `GameSpeech` plays server-generated speech through a separate gain. TTS and ordinary nonspatial cues remain nonspatial.

| Sound | Use |
|---|---|
| `background-basic`, `background-minigame`, `background-shop` | Music groups; no restart within the same group |
| `water`, `soil`, `crop`, `cut`, `cook` | Work sounds; independent of success feedback |
| `correct` | Target progress and ordinary reward |
| `step`, `door`, `coin` | Travel, shop entry, trading/paid research |
| `pickaxe`, `break`, `destroy`, `shine` | Hit, broken rock, broken tool and rare reward |
| `splash` | Fish catch, synchronized with shine for rare catches |
| `sleep` | One-shot that continues across the morning transition |
| Synthetic cues and target beacons | Selection, errors, progress and optional directional target guidance |

Task spatial sound places the pointer relative to the pad centre. Fishing places the hidden target relative to the pointer. Target beacons are a separate guide to remaining farm/mine targets and can be disabled with **Target cues**. Shop entry and trading remain nonspatial; travel uses the pressed direction. Current task routing uses `dry_gain: 0`, avoiding a centred copy that can weaken direction. Repeat presses do not add another copy over an active work loop, and structured sound events suppress overlapping legacy feedback. These controls do not make every sound spatial.

Speech uses fixed English Piper models, not the browser's operating-system voice. The system guide uses `en_US-hfc_female-medium`; Rowan uses `en_US-hfc_male-medium` (the internal profile key is still `shopkeeper`). Models, cached WAVs and reports are in `.audio/voices/`, `.audio/cache/` and `.audio/reports/`. **Test guide**, **Test Rowan**, **Replay**, speech stop/on/off, rate and volume controls are available. Speech volume defaults to 85% and is separate from music/effects.

Action results and dialogue take priority over hover text. Requests carry client and sequence information so stale replies do not replace newer speech. New NPC dialogue replaces old dialogue; ordinary hover does not interrupt it. Leaving the window silences playback and discards late replies. On return, current music and lake sound can resume without replaying old speech. Speech can lower background music and selected effects; fishing exploration retains its configured gain.

### Configuration reference

Edit **`engine/config/game.json`**, not the former root `game_config.json`, then restart the server. Values below describe this checkout. Ticks are game time, `_ms` values milliseconds, coordinates dots, and probabilities normally 0–1. Audio gains are linear multipliers and can exceed 1; they are not slider percentages. The following numeric chances are developer settings, not player-facing dialogue.

| Path in `game.json` | What it changes / current value |
|---|---|
| `game.start_day`, `resources` | Starting day (1), gold, fertilizer, seeds and crops |
| `time.total_cells`, `time.action_costs` | Day length (20), per-action costs listed above |
| `seeds.<id>.growth_days`, `.yield`, `.seed_price`, `.crop_price`, `.seed_return_chance` | Growth, yield, prices and baseline seed recovery (0.1) |
| `fertilizer.growth_day_bonus`, `shop.fertilizer_price` | Immediate growth bonus (1 day), fertilizer price (12) |
| `research.seed_return` | Gold `[20,40]`, copper `[3,6]`, recovery `[0.3,0.6]`, maximum level 2 |
| `research.field_expansion` | Initial 2 plots; gold `[30,50,70,90]`, stone `[5,10,15,20]` |
| `research.mineral_luck` | Gold `[20,40]`, iron `[3,6]`; diamond weight +1 and double-drop chance +0.15 per level |
| `recipes.<id>` | Ingredients, effects, duration, sale price and `gesture_steps`; hidden quest recipes stay out of kitchen lists |
| `recipes.<id>.allowed_fish`, `.quality_effects` | Fish eligibility; grill multipliers 1.5/2/3, stew 1.25/1.5/1.8 for 3/4/5 sales, frying double chance 0.3/0.6 |
| `cooking_methods.gestures` | Shared fish-cleaning, grilling, stirring and frying paths and tolerances |
| `care_minigame` | Target count (6), positions, tolerance (4), success ratio (0.65) |
| `harvest_minigame` | Target count (6) and positions; all required. Collection tolerance is fixed at 3.5 in code |
| `interaction.feedback` | Disappearance delay 200 ms; visual refresh 100 ms (minimum 50) |
| `interaction.cooking` | Resume marker delay 400 ms; stir scale 1.6, clipped to the display |
| `interaction.inventory` | Page size 12 (clamped 1–12), hide empty items |
| `interaction.sleep.blackout_ms` | Sleep blackout: 2000 ms |
| `mine.daily_rock_limit`, `.rock_width`, `.rock_height`, `.rock_gap` | 7 rocks (also capped in code), size 10×10, gap 5 |
| `mine.hits_to_break`, `.pickaxe_price_multiplier`, `.pickaxe_safe_hits`, `.pickaxe_break_increment` | 3 hits; 5× fertilizer price; safe threshold 9; break increase 0.05 |
| `mine.loot_weights` | Diamond / iron / copper / stone weights: 1 / 15 / 34 / 50 |
| `mine.mineral_sell_multipliers`, `.mineral_sell_price_bonus`, `.mineral_buy_multiplier` | Crop-based mineral pricing; +3 gold; buy at 2× sale price |
| `fishing.rod_price`, `.rod_safe_catches`, `.rod_break_increment` | 100 gold; 4 safe successful catches; then +0.1 per success |
| `fishing.near_radius`, `.middle_area_fraction` | Near radius 4; middle circle area 1/6 of the display |
| `fishing.zone_weights` | Miss/low/medium/high: far 30/40/20/10, middle 10/30/40/20, near 10/20/30/40 |
| `fishing.fish`, `.fish_sell_prices` | Species, internal grades, base prices 24/27/36 |
| `flowers.seed_price`, `.watering_seconds`, `.contact_gap_seconds` | 150 gold; 3 seconds contact; maximum contact-sample gap 0.5 seconds |
| `flowers.sprout_days`, `.stem_days`, `.bloom_cycle_days` | 2 watered days per early stage; 3-day bloom-age cycles |
| `flowers.bloom_wilt_increment`, `.dry_wilt_increment`, `.harvest_bonus` | Hidden wilt increments 0.1 per bloom cycle and 0.3 per dry day; blooming crop bonus +1 |
| `rowan.seed_gift_each`, `.vegetable_reward_gold` | One seed each; submission reward 100 gold |
| `weekly_market.discount_percent`, `.bonus_percent`, `.days` | 20% discount/bonus and the weekday item categories |
| `dotpad`, `time.bar`, `home`, `farm`, `town`, `minimap` | Display sizes and base layouts; some are normalized by fixed-grid code |

Travel is fixed to zero in code. Several action costs have minimums in `engine/core/time.py`; lowering JSON below those minimums has no effect. Some labels and layout coordinates are normalized, so changing a JSON label alone may not change the displayed English text. F3's 800 ms threshold is `holdMs` in `engine/web/core/game-keys.js`.

All entries below are under `interaction.audio`:

| Key | What it changes / current value |
|---|---|
| `default_volume` | Master music/effects volume: 1.0 |
| `bgm_gain.basic`, `.minigame`, `.shop` | Music gains: 0.7 / 0.4 / 0.7 |
| `bgm_during_tts`, `one_shot_during_tts` | Speech-time multipliers: 0.6 / 0.7 |
| `work_gain`, `work_gain_during_tts` | Water/soil/cut/cook 0.7 / 0.6 during speech; crop 1.5 / 1.4 |
| `reward_gain`, `reward_gain_during_tts` | Reward gain 0.6 / 0.5 |
| `one_shot_gain`, `one_shot_gain_links` | Per-effect gain; `step` inherits `door`; shine is 3.0 |
| `cooking_correct_interval_ms`, `other_correct_interval_ms` | Minimum reward intervals: 650 / 90 ms |
| `click_duration_ms`, `motion_idle_ms`, `motion_check_interval_ms` | Tap duration 650 ms, motion idle 450 ms, check 120 ms |
| `correct_max_load_age_ms`, `max_reward_sources`, `hover_interval_ms` | Stale reward cutoff 650 ms, at most 2 rewards, hover interval 220 ms |
| `bgm_minigame_pages`, `bgm_shop_pages` | Music group membership by page ID |
| `task_spatial.enabled`, `.dry_gain`, `.spatial_gain` | Task spatial routing: true / 0 / 1 |
| `task_spatial.min_gain`, `.max_gain`, `.distance_scale`, `.position_scale`, `.smoothing_seconds` | Task attenuation/position: 0.65 / 1 / 40 / 10 / 0.03 |
| `fishing.min_gain`, `.max_gain`, `.distance_scale`, `.position_scale` | Lake sound: 0.12 / 0.85 / 40 / 10 |
| `fishing.tts_multiplier`, `.bgm_multiplier` | Exploration during speech 1; lake background music 0.2 |

`engine/config/npc.json` holds dialogue and advice; `speech.json` holds profiles, pronunciation version, samples and verified model-download metadata; `tracking.json` holds camera/WebSocket settings. Companion layout and image registration remain separate from game rules.

### Diagnostics and developer tools

| Command from the repository root | Use |
|---|---|
| `python engine/launcher/check_setup.py --synthesize` | Validate installation and synthesize voice checks |
| `python engine/tools/prepare_speech.py --download` | Fetch verified models and prepare samples |
| `python engine/tools/prepare_demo.py --server http://127.0.0.1:8003` | Cache demo speech for the Windows server; use port 8000 where applicable |
| `python engine/tools/prepare_demo.py --list` | Inspect demo lines without changing the live game |
| `python engine/tools/speech_inventory.py` | Catalogue speech literals/templates |
| `python engine/tools/audio_flow.py` | Scripted activity flow with temporary saves |
| `python engine/tools/audio_integration_lab.py` | Temporary browser audio lab on port 8001 |
| `python engine/tools/prepare_effects_preview.py` | Effect reel; requires FFmpeg and Node, does not reproduce live HRTF |

A failed launch does not always mean the port is occupied. Check the preceding setup/speech error first, verify voices with `check_setup.py`, and rerun the installer for missing or damaged downloads. Use the address printed by the launcher. Do not close an unrelated process merely because it uses the requested port.

## Further development and evaluation

Planned work includes additional plants and pets, ranching, more recipes and quests, music and crafting. Shared work includes reconciling the companion bundle with its sources and reducing remaining cross-feature dependencies.

User evaluation should record task success, completion time, accidental input, understanding of tactile/audio information and workload. Compare pointer delay on older laptops, camera calibration and occlusion, tactile legibility, voice pronunciation and stereo guidance with actual hardware.

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

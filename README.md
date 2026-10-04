# Dotdew Valley

English | [한국어](README.ko.md)

A farming and life simulation game for the Dot Pad. Players farm, cook, mine, trade, and research upgrades across four locations: home, farm, village, and mine. The activities draw on Stardew Valley, with each task adapted to a 60×40 tactile display.

The browser simulator supports mouse and keyboard input. A USB Dot Pad and an external hand-tracking system can also be connected. A separate Visual Companion window shows the same game state using images.

## Design

The project explores how blind and low-vision players can understand a game world through touch and sound, then act directly on the surface they are reading. Shapes and speech provide guidance without requiring Braille literacy.

| Channel | Use |
|---|---|
| Touch | Position, shape, layout, paths, and progress |
| Speech and sound | Names, quantities, states, and action results |
| Visual display | Images, quantities, and selection highlights for low-vision players and companions |
| Buttons | Navigation, menus, saving, loading, and pause |
| Pointer and hand gestures | Selecting, sweeping, tracing, and tapping |

Exploration and travel cost no game time. Moving over an object and pressing it are separate inputs, so reading the display does not trigger an action.

Farming, cooking, mining, trading, and research are implemented. Fishing, ranching, music, NPC dialogue, quests, and crafting are planned. The controls below describe the current build; some differ from the initial proposal.

## Running the game

Create a Python environment and install the dependencies from the project root.

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

python -m pip install -r requirements.txt
python -m uvicorn game_app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser. Builds with the Windows launcher use `game.bat` to run `launch_game.py`; use the address printed by that launcher. Serve the HTML through the local server rather than opening it directly.

1. Click or press a key on the game page to enable audio.
2. Use the mouse and keyboard, or connect the USB pad and hand-tracking server.
3. Select **Open visual display** to open the companion window. Allow pop-ups for the site if needed.
4. Keep the original game page open while using the companion.

Restart the server after changing the configuration. After replacing web files, hard-refresh the game page and reopen the companion window.

## Controls

| Input | Action |
|---|---|
| Hover | Hear an object's name and state |
| Click | Select, use a facility, or strike a rock |
| Press and drag | Water, fertilize, harvest, or trace a cooking path |
| F1 | Open the minimap; press again in that menu to return to the current location |
| F2 | Open inventory; press again in that menu to return to the current location |
| F3, short press | Open or close the save list |
| F3, hold | Save to a new slot after about 0.8 seconds; stay on the current screen after `Game saved.` |
| F4 | Pause or resume |
| Left/right arrow keys or pad buttons | Travel, go back, or turn a page, depending on the screen |
| W / A / S / D | Move the pointer while the game canvas has focus |
| Shift + W / A / S / D | Move the pointer in larger steps |
| Enter | Select at the pointer position |
| Space | Toggle pressed/released input |

Locations run from left to right: **Farm ↔ Home ↔ Village ↔ Mine**. Travel announces the destination. A direction with no route produces an unavailable-direction message.

Either arrow closes the minimap, inventory, or load screen and returns to the current location. Going back from buying or selling returns to the shop's buy/sell selection screen. Shop page-turn commands remain separate. Use the on-screen previous/next items to turn inventory pages.

Hand tracking supplies coordinates and press state from an external device. A server that sends coordinates only requires the press button or Space as well. The Dot Pad does not detect touch coordinates itself. Guidance uses English speech; a new announcement interrupts the previous one.

## Locations and activities

| Location | Activities |
|---|---|
| Home | Sleep, research, and cook |
| Farm | Plant seeds, water, fertilize, check growth, and harvest |
| Village | Buy and sell; travel to home or the mine |
| Mine | Break rocks with a pickaxe and collect minerals |

Crops can be sold or cooked. Minerals can be traded or spent on research. Research adds plots and improves seed recovery and mineral drops. Food is consumed from inventory to apply an effect.

### Time and sleep

Time advances when activities finish. The current configuration gives each day 20 ticks. Travel costs 0; planting, watering, and fertilizing cost 2; harvesting, research, and cooking cost 3. Mining costs 2 ticks when a rock breaks, rather than on every hit.

When the daily allowance runs out, the player returns home. During sleep, the tactile panels briefly turn off and background music pauses. The sleep sound plays once and continues to its end after the next day begins. The pad uses a lower tactile time panel; the companion uses a thin orange bar that fills as time is spent.

### Farming

Select a plot to open its management screen. Empty plots accept seeds; planted plots show growth, water, and fertilizer status. On the farm, the plot fills from the bottom as the crop grows. The detail screen provides growth information and care buttons.

Watering and fertilizing use press-and-drag targets. Completion follows `care_minigame.success_ratio`. If the threshold has not been reached, the player can continue over the remaining targets. Watered crops grow after sleep. Fertilizer advances growth immediately.

Harvesting requires every target. Yield comes from the crop's base amount and the active food effect, with no minigame-score multiplier. Seed recovery uses the crop's base chance or its research level.

### Cooking and food

Choose a recipe and select all required ingredients to start cooking. Complete the chopping path and the second path in order. Ingredients and time are spent when both stages are complete. There is no time limit. A marker shows where to resume after progress stalls, and passed sections disappear after a configured delay.

| Food | Ingredients | Effect | Duration |
|---|---|---|---|
| Tomato carrot stew | Tomato, carrot | Harvest boost | 6 hours |
| Potato tomato soup | Potato, tomato | Pickaxe protection | 10 hours |
| Vegetable fritters | Potato, carrot | Time saving | 10 hours |

Durations use game time. The second path for vegetable fritters has eight petals. Food is used from inventory, with one effect active at a time. Eating another dish replaces the effect. Its duration decreases as game time is spent. Player-facing descriptions show the effect and duration without detailed multipliers.

### Shop and inventory

The shop sells seeds, fertilizer, pickaxes, and selected minerals, and buys crops, food, and minerals. Only one pickaxe can be held at a time. Buy another when it breaks.

Inventory hides zero-count items and shows up to 12 items per page. Tactile frames distinguish food with an oval, gold with a diamond, and other items with rectangles and category symbols. The companion uses rectangular cards throughout, with colored borders and the name, quantity, and price below the image.

### Mining and research

Up to seven rocks are placed each day, with gaps between them. A rock normally takes three hits to break. Damage reduces the density of its internal dots using fixed patterns; the outline remains readable.

Rocks drop stone, copper, iron, or diamonds. Research can add bonus drops. Pickaxe durability is handled internally and is not shown as a player-facing value. When a tool breaks, the shared destruction sound replaces the normal hit sound.

| Research | Materials | Effect |
|---|---|---|
| Seed recovery | Gold, copper | Improve seed recovery |
| Farm expansion | Gold, stone | Increase plots from two to six |
| Mineral luck | Gold, iron | Improve mineral drops and bonus quantities |

Research uses three cards per row. There is no harvest-yield research upgrade.

## Code structure

The server owns game state and action checks. The browser sends input and receives dot frames, public state, speech, and sound events. Mouse, keyboard, and device input share move, press, drag, and release events.

### Game and server

| File | Responsibility |
|---|---|
| `game_app.py` | FastAPI server, game page, static files, input and state APIs |
| `game_engine.py` | Locations and activities, game rules, resources, time, tactile rendering, and announcements |
| `game_ui.py` | Keypad navigation, temporary menus, tactile frames, and category icons |
| `game_saves.py` | State serialization, save files, loading, and slot management |
| `dotpad.py` | Dot matrices and drawing primitives |
| `spectator_state.py` | Public object, plot, rock, path, and quantity data for the companion |
| `game_config.json` | Rules, starting resources, activity settings, audio, and layout data |

### Browser, hardware, and audio

| File | Responsibility |
|---|---|
| `web/game.html` | Pad simulator, pointer input, status, English TTS, and companion connection |
| `web/game-keys.js` | Function and arrow keys, F3 short/long press, repeat suppression, and cancellation |
| `web/hardware.mjs` | Web Serial pad output and physical buttons; WebSocket hand coordinates |
| `web/game-audio.js` | Separate music, action, reward, and one-shot sound channels |
| `web/audio/` | MP3 assets |
| `game.bat`, `launch_game.py` | Windows startup and server/browser launch helpers |

### Visual Companion

The companion is a separate, read-only window under `web/spectator/`. It follows locations, selections, minigames, time of day, and sleep. Clicking this window does not change game state.

| File | Responsibility |
|---|---|
| `standalone.html` | Companion window entry point |
| `viewer.js` | Scene, card, object, and effect rendering source |
| `model.mjs` | Convert game state into visual layout data |
| `viewer.css` | Cards, quantities, colors, selection highlights, and time bar |
| `display.js` | Runtime bundle loaded by the page |
| `build_display.py` | Build `display.js` from the source files |
| `visual-assets.json` | Background, facility, item, and sprite-region registry |
| `scene-objects.json` | Facility positions, sizes, and draw order |
| `assets/` | Images including `scenes.png`, `scenes2.png`, `facilities.png`, `items.png`, and `extras.png` |

Each plot and rock corresponds to a game object. Individual farm plots have fences. The shop places its catalog on the left and the merchant and counter on the right. Inventory and shop pages fit their items without scrolling.

Backgrounds, facilities, and objects have separate asset entries so existing images can be reused. A page without a visual renderer falls back to the dot display. An unregistered item shows its name in a frame. Rebuild `display.js` after editing its source files.

## Saving and loading

Holding F3 saves before the key is released. Releasing it after a save does not open the load screen. A short press opens the slot list.

Saves are JSON files in `saves/`; the latest 12 are retained. They restore progress including items, gold, day, plots, research, and food effects. Save files are excluded from version control. Server memory resets on restart, so save and load to continue a session. USB connections, camera calibration, and browser voice selection are separate from game saves.

## Audio

| Asset | Use |
|---|---|
| `background-basic`, `background-minigame`, `background-shop` | Music for the three page groups |
| `water`, `soil`, `crop` | Watering, fertilizing, harvesting |
| `cut`, `cook` | Chopping and stirring |
| `correct` | Target progress and ordinary loot feedback |
| `step`, `door`, `coin` | Travel, shop entry, transactions, and paid research |
| `sleep` | Sleep transition |
| `pickaxe`, `break`, `shine`, `destroy` | Hits, broken rocks, diamonds, and broken items |

Assets use matching MP3 names in `web/audio/`. Reward sounds do not interrupt action sounds. Moving within the same music group does not restart the track. TTS uses an English browser voice and has separate controls from game audio.

## Configuration

Edit `game_config.json` and restart the server. Values below reflect the current configuration.

Time uses game ticks, `_ms` values use milliseconds, probabilities use 0–1, and coordinates use dot units. Engine-side limits are noted below the tables.

### Rules and starting state

| Path | Setting / current value |
|---|---|
| `game.start_day` | Starting day: 1 |
| `resources` | Starting gold, fertilizer, seeds, and crops; three of each crop for cooking tests |
| `time.total_cells` | Daily allowance: 20 |
| `time.action_costs` | Costs for `travel`, `plant`, `water`, `fertilize`, `harvest`, `research`, `cook`, and `mine` |
| `seeds.<id>.growth_days`, `yield` | Growth days and base yield |
| `seeds.<id>.seed_price`, `crop_price` | Seed purchase and crop sale prices |
| `seeds.<id>.seed_return_chance` | Base seed recovery chance: 0.1 for each crop |
| `fertilizer.growth_day_bonus` | Immediate growth advance: 1 day |
| `shop.fertilizer_price` | Fertilizer price: 12 |
| `recipes.<id>.ingredients` | Ingredient IDs and amounts |
| `recipes.<id>.buff_kind` | `harvest_multiplier`, `pickaxe_protection`, or `time_slow` |
| `recipes.<id>.buff_multiplier`, `buff_ticks` | Effect multiplier and duration |
| `recipes.<id>.gesture_steps` | Per-stage `kind`, `path`, and `tolerance` |
| `research.seed_return` | `costs`, `copper_costs`, `return_chances`, `max_level` |
| `research.field_expansion` | `initial_plot_count`, `costs`, `stone_costs` |
| `research.mineral_luck` | `costs`, `iron_costs`, `max_level`, `diamond_weight_per_level`, `double_drop_chance_per_level` |

Farm expansion costs `[30, 50, 70, 90]` gold and `[5, 10, 15, 20]` stone, adding four plots to the initial two. Seed recovery research uses `[0.3, 0.6]`. These are development settings; detailed probabilities are not announced during play.

### Minigames and feedback

| Path | Setting / current value |
|---|---|
| `care_minigame.target_count`, `target_positions` | Watering/fertilizing target count and candidate positions |
| `care_minigame.tolerance` | Target hit tolerance |
| `care_minigame.success_ratio` | Completion threshold: 0.65; use 1.0 to require every target |
| `harvest_minigame.target_count`, `target_positions` | Harvest target count and candidate positions; all targets are required |
| `interaction.feedback.disappear_delay_ms` | Delay before care targets and cooking paths disappear: 200; use 1000 for one second |
| `interaction.feedback.visual_refresh_interval_ms` | Delayed-feedback refresh interval: 100; engine minimum 50 |
| `interaction.cooking.resume_marker_delay_ms` | Delay before the resume marker appears: 400 |
| `interaction.cooking.stir_scale` | Stirring path scale: 1.6, limited to the display bounds |
| `interaction.inventory.items_per_page` | Items per page: 12; engine range 1–12 |
| `interaction.inventory.hide_zero_items` | Hide empty items: `true` |
| `interaction.sleep.blackout_ms` | Sleep blackout and input wait: 2000 |

Harvest tolerance is fixed at 3.5 in the engine and does not follow `harvest_minigame.tolerance`. Adjust the F3 hold threshold through `holdMs` in `web/game-keys.js`.

### Mining and prices

| Key under `mine` | Setting / current value |
|---|---|
| `daily_rock_limit` | Daily rocks: 7; also capped at 7 by the engine |
| `rock_width`, `rock_height`, `rock_gap` | Rock size and spacing: 10, 10, 5 |
| `hits_to_break` | Hits per rock: 3 |
| `pickaxe_price_multiplier` | Pickaxe price relative to fertilizer: 5 |
| `pickaxe_safe_hits`, `pickaxe_break_increment` | Safe-hit threshold and subsequent break-chance increment: 9, 0.05 |
| `loot_weights` | Diamond 1, iron 15, copper 34, stone 50 |
| `mineral_sell_multipliers` | Mineral sale-price multipliers relative to the reference crop price |
| `mineral_sell_price_bonus` | Added sale price: 3 |
| `mineral_buy_multiplier` | Purchase price relative to sale price: 2 |

### Volume and playback

All keys below are under `interaction.audio`. Start with gains between 0 and 1 and check the loudness of the source audio.

| Key | Setting |
|---|---|
| `default_volume` | Master game-audio volume: 0.7 |
| `bgm_gain.basic`, `minigame`, `shop` | Music gains: 0.9, 0.5, 0.9 |
| `work_gain` | Per-action gains for `water`, `soil`, `crop`, `cut`, and `cook` |
| `work_gain_during_tts` | Action gains during speech |
| `reward_gain`, `reward_gain_during_tts` | Reward gains normally and during speech |
| `one_shot_gain` | Per-sound gains for sleep, entry, transactions, mining, and destruction |
| `one_shot_gain_links` | Shared settings; `step` uses `door` |
| `cooking_correct_interval_ms`, `other_correct_interval_ms` | Minimum reward intervals: cooking 650, other activities 90 |
| `click_duration_ms` | Short click-sound duration: 650 |
| `motion_idle_ms`, `motion_check_interval_ms` | Cooking movement timeout and check interval |
| `correct_max_load_age_ms`, `max_reward_sources` | Stale-reward cutoff and simultaneous reward limit |
| `bgm_minigame_pages`, `bgm_shop_pages` | Page IDs assigned to each music group |

### Layout and images

`dotpad` and `time.bar` define panel dimensions. `home`, `farm`, `town`, and `minimap` contain base layouts. The engine normalizes some screens to fixed grids and English names, so changing a coordinate or `label` may not directly change the rendered screen. Check the device dimensions and engine layout code when modifying these settings.

Companion positions and sizes belong in `scene-objects.json`; image registration belongs in `visual-assets.json`; card sizes and colors belong in `viewer.css`.

## Planned work and evaluation

User testing will examine game comprehension and enjoyment, the workload of tactile and spoken information, and the usability and accuracy of hand gestures.

- Improve coordinate calibration, jitter and occlusion handling, and the separation of exploration from action input.
- Measure and reduce input queues, state-transfer delays, and rendering delays on older laptops.
- Add fishing, ranching, music, NPC dialogue, quests, and crafting.
- Evaluate task completion, time, errors, comprehension, workload, and gesture accuracy with approximately six to eight visually impaired participants.

User testing has not yet been conducted. Physical pad refresh speed, tracking under different lighting and camera positions, occlusion, and speech quality remain part of the planned evaluation. The current design assumes usable hearing and hand control.

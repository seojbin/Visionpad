# Dotdew Valley

English | [한국어](README.ko.md)

A farming and life simulation game for the Dot Pad, a 60×40 tactile display. Blind and low-vision players read the world by touch and sound and act directly on the surface they are reading: farm, cook, mine, fish, trade and research across home, farm, village, mine and a fishing lake. Shapes and English speech guide the player; Braille literacy is not required.

A browser simulator supports mouse and keyboard. A USB or Bluetooth Dot Pad and an external hand-tracking camera can be connected, and a separate Visual Companion window shows the same game with images for normal players and companions.

## Contents

- [Proposal](#proposal)
- [Install and start](#install)
- [Controls](#controls)
- [Gameplay guide](#playing-the-game)
- [Tactile design rules](#tactile-design-rules)
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

Farming, cooking, mining, fishing, trading, research, Rowan's tutorial quests and a houseplant are implemented. Ranching, dog and cat care, and a shop prize draw are also implemented. Music, crafting and additional NPCs are planned, with artwork prepared for these expansions.

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

Use Left and Right to travel along **Farm ↔ Home ↔ Village**. Arrival speech names the destination; an unavailable direction gives a short message. F1 opens the minimap: explore its nodes and select a destination. The node with a small solid square in its centre marks the current location; paths stop one pin short of every node. The **Guide** button in the map's top-left corner opens the tutorial and symbol key (see [Learning support](#learning-support-the-guide)). In the village, use the separate on-screen up/down controls to reach the **mine** and **lake**. The farm has tactile exit arrows in both bottom corners (pasture on the left, home on the right) and the pasture one on its east fence, so travel works from the graphic as well as from the keys; on the home Care page Left and Right travel as on the home page.

The menu window that turns on the device is displayed above the current region; pressing the same key again in the F1 or F2 menu returns you to the current region. The menu does not overlap even when navigating through other menus. In menus without multiple pages, the right arrow key can also be used to go back. The minimap that appears when you press F1 and the save file list that appears when you press F3 can also be navigated back to the previous screen using the arrow keys. 

If there are multiple pages, the arrow keys in the inventory that appear when pressing F2 are for page navigation only, and the end indicates the first and last page. Therefore, use the arrow keys to navigate inventory, and only use the arrow keys to leave the page or the F2 key to close it.

Each shop consists of three levels (Town - Shop Selection Page - Buy/Sell Page). In Buy/Sell, if a page allows navigation beyond two pages, page switching takes priority; on the Buy/Sell page, the arrow key that leaves the page scroll activates the back button, leading to the shop selection screen, while the arrow key on the shop selection screen takes you to the town.

For screens with few icons, such as villages and houses, create a detailed display at the bottom. On the display, you can select objects just like with the buttons, and move them using arrow indicators. Selectable objects on the display are raised outlines with a lowered interior, separated from roads, walls and each other by at least one lowered pin; small solid triangles at the edges are exits. See [Tactile design rules](#tactile-design-rules).

The lower 20-cell panel normally shows activity time. On a multi-page list it becomes a page-position strip: the width is divided by the page count and the current segment is raised. On a single-page shop screen it displays Braille **shop**, **buy** or **sell** to indicate the current menu depth. Pagination takes priority over that label; sleep blanks the panel.

Hold Shift in the demo, or use the pointing gesture with hand tracking, to hear detailed speech about the current location and the object under the pointer.

### Inventory and item recognition

Press F2 to check belongings. The first page holds gold and usable items. Additional food pages come first when needed, followed by seeds, crops, fish, minerals and tools. Empty items are hidden and each page holds up to 12 entries in three rows of four. Select food to eat it. Adoption vouchers, care supplies and gold tool kits can also be used from inventory; other entries are for inspection.

Every entry has a single-line rectangular frame. Usable items, including food, vouchers, care supplies and gold tool kits, have two nested rectangular outlines with no central symbol. Other entries carry one symbol from the shared 14-symbol vocabulary (seed, crop, fish, mineral, tool, gold and so on; see [Symbol vocabulary](#symbol-vocabulary)), always with a lowered pin between the symbol and its frame; an item without a category shows the frame alone. The shared grid keeps objects in predictable slots. The companion uses image cards and quantities, rather than reproducing every tactile frame.

### Home, time and sleep

At home, select the bed to sleep, the research station to buy an upgrade, the kitchen to cook, or the fourth **Care** control to choose Plants or Pets. The lower **Flower pot** opens plant care; the pet house opens the pet slots. A new game starts with 60 gold, two fertilizer, crop seeds and three of each vegetable for cooking.

Time is measured in ticks consumed by activities. The current day allows 20 ticks: planting, watering, fertilizing, breaking a rock and casting each cost 2; harvesting, research and cooking cost 3. Travelling costs 0. Individual mine hits cost nothing until the rock breaks. Food can change the time cost.

When time runs out, the player returns home and must select the bed. Sleep blanks the tactile panels for two seconds and pauses the music. The next morning, watered crops grow, the houseplant updates and mine rocks refresh. The companion also follows the time of day and sleep transition.

### Farming: plant, water, fertilize and harvest

1. Travel to the farm and select a plot. A plot's interior fills from the bottom as its crop grows.
2. On an empty plot, choose planting and select an owned seed. On a planted plot, check its growth, water and fertilizer state.
3. Choose watering or fertilizing and sweep over the target dots. Holding a click is not required.
4. Sleep after watering to advance growth. Fertilizer immediately advances growth by one day; it is an optional aid.
5. Once mature, choose harvest and pass every crop target. There is no time limit or score-based yield multiplier. Basic yield, food effects and any flower or pet bonuses determine the result. Seed recovery, improved through research, is checked separately and may return seeds.

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

If a dish is successful, the price of the base ingredients rises by about 1.5 times, enabling efficient acquisition of goods.

### Mining

Enter the mine and select a rock to strike it. A pickaxe is required to hit, but not to enter. The shop sells one at a time; buy a replacement when it breaks. Up to seven spaced rocks appear per day, normally taking three hits each. Their interiors lose dots in fixed damage patterns while their borders remain readable. After the ninth strike, the pickaxe’s break chance increases by 5 percentage points per strike.

Each broken rock yields stone, copper, iron or diamonds according to its drop probabilities. Research and food may improve the result. Hit, rock break, rare find and tool destruction have different sounds; a tool-breaking hit uses the destruction sound instead of the ordinary hit/break sound. Tool durability and drop probabilities are not disclosed during play.

### Fishing

Entry is free without equipment, but casting requires a fishing rod (base price 100 gold, one owned at a time). Use stereo headphones and move towards the looping water sound. It is positioned relative to the pointer and becomes louder near the hidden target. The tactile outline marks the lake; the companion does not reveal the accuracy zones. Moving closer to the target improves the chance of a rare fish and reduces the chance of a miss compared with casting far away.

Click, Enter or F4 casts once inside the lake. Both a catch and a miss use 2 ticks and move the target; holding does not cast repeatedly. Input outside the circular lake boundary is ignored. A catch plays splash, with shine added for a rare fish. The lake keeps basic music at a reduced level; speech does not lower the exploration water sound. Rod use is counted only on successful catches. Starting with the fifth successful catch, its break chance increases by 10 percentage points per catch.

| Fish | Base sale price | Cooking use |
|---|---:|---|
| Sardine / mackerel / bass | 24 each | Stew / grill / fry |
| Carp / catfish / flounder | 27 each | Grill / stew / fry |
| Salmon / rainbow trout | 36 each | Grill / stew |

### Shop and the weekly calendar

Select the village shop, then Sell, General goods, Tools or Calendar. Hover an item to check its price and owned quantity; select it to trade one. The shop sells crop seeds, feed, pet medicine, tools, livestock and selected minerals, and buys eligible crops, food, fish, minerals and animal products. Fertilizer and flower seeds are now prize-draw rewards rather than direct purchases. Lists use pages rather than scrolling. Calendar speaks today's offer only, without opening another page.

| Day | Offer |
|---|---|
| Monday | Ore purchases 20% off |
| Tuesday | Cooked food sells for 20% more |
| Wednesday | Fish sells for 20% more |
| Thursday | Crop seeds 20% off |
| Friday | Ore sells for 20% more |
| Saturday | Pickaxes and rods 20% off |
| Sunday | All eligible sales earn 20% more |

Day 1 is Monday. Prices are rounded down after each applicable multiplier; food sale bonuses also affect the shown price and the paid amount.

### Prize draw and special items

**Prize draw** is the first item in General goods and costs 200 gold. It has a dedicated wheel icon; selecting the wheel beside the shopkeeper in the lower scene buys a draw directly. The reward is granted immediately. Its spoken result starts at least one second after the roulette sound begins, or later if speech is still being prepared.

| Reward | Chance | Quantity |
|---|---:|---|
| Plant nutrient | 12% | 1 |
| Special feed | 12% | 1 |
| Gold tool kit | 10% | 1 pickaxe or fishing-rod kit |
| Adoption voucher | 6% | 1 dog or cat voucher |
| Flower seed | 6% | 1 morning glory, sunflower or orchid seed |
| Diamond | 1% | 1 |
| Fertilizer | 20% | 3 |
| Crop seeds | 33% | 3 of one crop type |

Types within each reward category are equally likely. The draw always costs 200 gold, ignores weekly and food discounts, and does not consume discount charges. An adoption voucher can be used to adopt or sold for exactly 300 gold. Its sale neither applies weekly/food bonuses nor consumes sale-effect charges.

Plant nutrient resets a living plant's dry-day and bloom-age counters and prevents wilting for six days; it does not revive a wilted plant. Special feed gives a large affection increase. A gold tool kit requires the corresponding owned tool, resets its wear and divides subsequent effective use by four. Upgrades do not stack and are lost when the tool breaks. The break-probability formula still applies, so this does not guarantee exactly four times as many uses.

Five upcoming rewards are prepared in advance. Each paid draw awards the first and adds one at the end. This list and the random state are stored in the normal save slot; loading restores that slot's reward order. A failed purchase does not advance it. There is no separate prize-sequence file.

### Rowan and tutorial quests

Rowan stands beside the shop. Select him to hear his dialogue without leaving the village; only quest item submission opens a separate selection page. The companion overlays his portrait and text. Hover speech does not replace an active quest line; a new dialogue replaces the previous dialogue.

The first conversation gives **Rowan's soup**, with the stew's harvest effect. Eat it from F2 or sell it (base value 100 gold), then return to receive one seed of each crop. Talk again for the farming tutorial and vegetable request. Select any owned crop in the submission page to give one and receive 100 gold; either arrow cancels. Gifts, rewards and quest progress are saved. Later advice and reactions to recent activities use Rowan's voice.

To fix the lock where users had zero gold or no crops to plant and could no longer earn money, Rowan was set to give out free carrot seeds if no seeds were held.
### Pasture

The pasture is west of the farm. It starts empty: buy a chicken for 100 gold or a sheep for 250 gold from the shop's **Tools** counter. One of each can be kept. Upper icons open the animal's detail page; the lower scene shows the owned animals moving and changing direction. Their detail drawings also move slightly as they breathe.

The detail page has **Feed** and **Collect eggs** or **Shear wool** controls. Animals graze without feed, but feeding helps shorten production cycles and keeps them from leaving. Buy the shared **Animal feed** item from General goods; its current base price is 80 gold. Feed can be given once per animal per day. If a product is ready or due the next day, the feed bonus is carried forward to the next cycle rather than producing it immediately.

Petting is a hidden interaction: move the pointer back and forth over the animal's body. Brushing plays while moving, and three accumulated seconds award affection once per day with the animal's main call. There is no petting button or percentage display. Status changes from **Indifferent** to **Recognizes you** and **Seems happy**. Not petting does not itself reduce affection; prolonged lack of feed or leaving products uncollected does. Animals may leave if they go too long without feed, with more familiar animals staying longer. On entering the pasture, a short message identifies an animal that has left. Exact affection and escape rules are not spoken during play.

| Animal | Product and timing | Collection |
|---|---|---|
| Chicken | A new batch after 1–2 days; usually one egg, occasionally two. Eggs accumulate to a maximum of three. | Select the egg below the chicken directly, or choose Collect eggs and select it on the collection screen. |
| Sheep | Wool becomes ready after 2–4 days and stays ready until collected; it does not stack across cycles. | Select the ready sheep or Shear wool to open the fleece screen. Sweep across it without holding a click. A round eraser removes individual dots until enough fleece has been cut. |

Readiness is announced as **Eggs ready** or **Wool ready**, without a quantity. The collection result states the actual amount. Wool normally gives 2–5 bundles; animal-shelter research can add bonus eggs or wool. Collecting eggs or finishing shearing costs 3 ticks. Base sale values are 70 gold per egg and 100 per wool.

Only owned animals make routine calls in the pasture; the detail page plays calls for its selected animal. Entry and completed interactions use the main call. Brushing and calls can overlap. Feeding has its own sound, and shearing uses its own cut sound. A chicken also gives a morning call after sleep. Ownership, production, affection, feed history and unfinished shearing are saved.

Eggs can be cooked with a carrot to make **Fried egg**. The two stages are a bouncing egg-cracking path and the frying path. Eating it discounts the gold cost of the next successful research purchase by 20%; material requirements are unchanged.

### Research

Select the research station at home, inspect an upgrade and select it to pay its gold and material cost. The list uses three columns. Research consumes game time, and its progress is saved. More upgrades are planned.

| Upgrade | Materials | Result |
|---|---|---|
| Seed recovery | Gold and copper | Better seed recovery, up to two levels |
| Farm expansion | Gold and stone | Two initial plots, up to six |
| Mineral luck | Gold and iron | Better mineral rolls and bonus quantities, up to two levels |
| Animal shelter | Level 1: 150 gold + 2 wool; level 2: 250 gold + 4 wool | Additional eggs and wool at collection, up to two levels |

Gameplay descriptions report research levels rather than exact probabilities.

Animal shelter checks each original product separately when eggs or wool are collected: a 15% bonus chance per item at level 1, or 30% at level 2. For two eggs at level 2, two independent checks each have a 30% chance to add one egg. Bonus items do not trigger further checks. This keeps the chance per product the same for chickens and sheep. The nest still holds at most three eggs before collection; research bonuses are added when collected.

Short research speech lists the name and next-level gold/material cost. Detailed speech includes the next level, requirements and effect; Animal shelter uses “Increased yield.” At the limit it reports maximum level and no longer offers a purchase. The research level is saved, and older saves without it start at level zero.

### Flower pot

Use a morning glory, sunflower or orchid seed from the prize draw through **Care → Plants** or the lower **Flower pot** at home. Choose a species for the single pot. This is mainly a decorative activity: it costs a substantial amount of gold for a modest practical benefit. The small home drawing and the enlarged detail drawing show sprout, stem, flower or wilted states. The detail page has watering and empty-pot controls above the plant.

A blooming plant grants a hidden effect. Morning glory adds one crop to each harvest while in bloom.

Choose water, then keep the pointer on the actual pot area for a total of three seconds. Clicking is unnecessary; contact time, not a path score, determines completion. Water each day and sleep to grow the plant: two watered nights to a stem and two more to a flower. A blooming plant stays in bloom rather than returning to a stem, but becomes more likely to wilt as it ages. Missing water adds risk. A wilted plant cannot be watered and must be emptied before planting again. Hidden bloom benefits and wilt probabilities are not announced in play. The three species currently share growth, watering and bloom-effect rules. Their flower dots and existing seed images differ; dedicated detail artwork for the additional species has not been added.

### Pets

Use a dog or cat voucher from the prize draw in inventory. Choose one of 12 names for that species; the pet is displayed as **Cat Luna**, for example. The voucher is consumed only after the name is confirmed. Up to six pets can live together, including several of the same species.

Open the six pet slots through **Care → Pets** or the pet house in the lower home scene. Choosing a pet opens its detail page and brings it out at home. It moves within the lower-left area at home and shifts slightly on the detail page. Position, direction and pose change every 3–5 seconds; stroking does not force a pose. Dog and cat dots retain connected bodies and tails with slightly shorter muzzles.

| Detail control | Action |
|---|---|
| Give something | Choose shared Animal feed or special feed. Medicine is shown and usable only when the pet is sick. |
| Receive | Collect a waiting gift, or select the gift beside the animal directly. |
| Change pet | Open the slots and choose which pet to bring out. |
| Let pet go | Ask for confirmation. Confirm sends the pet away; Keep pet cancels. |

Move over the body for three seconds to increase affection once per day. There is no percentage display or petting button; the reward plays the main call. Normal feed can be given once daily, and special feed uses the existing feed sound too. Missed feeding leads to hunger and illness. Medicine is available from General goods at a base price of 30 gold. Unlike livestock, pets do not die or escape.

Affection states are **Getting to know you → Recognizes you → Trusts you**. Healthy, fed pets may prepare gifts according to affection: crop seeds from dogs or low-tier fish from cats. One gift waits until collected. A healthy, fed pet at the highest affection stage adds one crop per harvest. Multiple pets do not stack this bonus, and it is separate from food effects. Numeric affection and probabilities are not spoken in play.

At home, routine calls rotate through owned pets; the detail page plays only the selected pet's calls. Entry and care use main calls, which can overlap with brushing. Each pet's pitch is assigned at adoption and saved. Cat routine gain is currently 0.8; the default routine gain is 0.35.

### Save and load

Hold F3 for 0.8 seconds to save into a new file. **Game saved.** plays while the button is held; releasing it leaves the current screen unchanged. A short press opens the save list; select a slot to restore it.

The latest 12 JSON saves are kept in `saves/`; older slots are removed. Gold, items, day, plots, research, food effects, quests, mine/fishing state, the houseplant, individual pets, the active pet, gold tool upgrades and the next five prize-draw rewards are restored. Older formats receive defaults and feature migrations. Connections, camera calibration and browser audio preferences are separate. Save before shutting down: the server's in-memory game is not an automatic persistent save.

## Tactile design rules

The tactile layer follows published guidance for tactile graphics, adapted to the Dot Pad (60 × 40 single-height pins, about 2.5 mm apart). The rules live in `engine/display/tactile.py`. `python engine/tools/tactile_audit.py [--show] [--png DIR]` renders every page (see [Dot review](#dot-review)) and reports violations, and `engine/tests/python/display/test_tactile_rules.py` fails when a page breaks them. Numbers in brackets refer to [References](#references-for-the-tactile-design).

| Rule in this game | Why (source) | Where it is enforced |
|---|---|---|
| **Separation.** Every symbol, framed icon, map object and doorway arrow has at least one lowered pin around it. Lines (roads, walls, map paths) stop short of a symbol instead of running into it. | A point symbol needs at least 1/8 inch (3 mm) of space from any other component, and symbols placed closer are felt as one [1 §3.4.3.11, §8.5.3, §8.6.5]. Lines are broken where they meet other elements [1 §2.11]. One pin pitch (about 2.5 mm) is the closest the Dot Pad gets to 3 mm, so one lowered pin is the minimum. | `tactile.isolation_problems()`; `tactile.SymbolTrace` (records which drawing raised each pin, so a symbol touching a wall or its own frame fails); map paths shortened in `game/minimap`; road edges stop before the arrows and the shop in `game/village`; room walls open two pins around the doorway arrows (`Rendering.draw_room`) |
| **Outlines for large shapes; solid only for small signs.** Large objects (furniture, the shop, counters, the current map node) are a raised outline with a lowered interior. Solid shapes are small signs of at most 4 × 4 solid pins (arrows, the person's head, the "you are here" mark). Progress is a line texture, not a solid bar. **Exceptions by owner decision:** mine rocks keep their filled shape with damage patterns, and a sheep with grown wool (and the shearing field) stays filled, because the wool is what gets sheared. | Project decision from the professor's review: blind readers found filled (engraved) icons hard to read. On pin displays, plain outlines with empty insides were recognised most easily, and filled circles were hard to recognise [14, citing Bellik & Clavel and Velázquez]. Important features should be raised edges, not indents [3]. Outlines were easier than solids in older studies, but that advantage "does not hold when the size is reduced" [15]; BANA likewise finds solid shapes easier for young readers on paper [1 §11.2.1, §6.11.1.2]. That is why small signs stay solid. | `tactile.solid_blocks()`: no solid block larger than 4 × 4 outside the mine and the sweep minigames. `tactile.fill_ratio()`: objects of 8 × 8 pins or more raise at most half of their interior, unless marked `filled_by_design` (the woolly sheep) |
| **Animals: solid limbs, outlined body, line texture.** The large cat, dog, chicken and shorn-sheep drawings keep thin parts (legs, tail, ears; at most five pins across, `THIN_PART`) solid. The body is a one-pin outline, then one lowered pin, then horizontal raised lines with one lowered row between them. Texture runs shorter than three pins are dropped, so no single pin stands alone. On the cat and dog only the body gets the texture; the head stays an empty outline. The woolly sheep stays filled: its wool is the part that identifies it and the part that is sheared. | Single interior pins read as eyes or as braille [14], and fewer, isolated dots hurt recognition [21]; the earlier staggered-dot texture looked like a face for this reason (owner feedback). On pin displays the best-tested choices are an empty interior or one uniform line texture [14, citing Bellik & Clavel; 16; 23]. Line pictograms were recognised better than dot pictograms (88.0 % vs 62.6–64.8 %), and at small sizes filled parts beat outlined ones [21], hence solid limbs. Lines need at least one blank row between them and blank space from other elements [23]; at 10 dpi vertical and horizontal lines are confused with each other [16], so only one direction is used. Uniformly textured pictures were recognised better than raised-line ones on paper [17, 25], and a texture on the one identifying part (a lion's mane) helped most [17], which supports the filled wool. No study of fur or petting texture on pins was found. | `tactile.fur_rows()` (optional `mask`), `shapes.TEXTURE` and `shapes.drawing()` in `game/pets`, `tactile.close_gaps()` (fills carved lines in the chicken first), `test_fur_texture_has_no_isolated_pins` |
| **Symbols differ in structure, not only outline.** Symbols that appear together come from different classes: solid (seed, arrows), open lines (crop, tool, bed, check, bag), closed outlines (mineral, water, page, pot) and closed outlines with one extra feature (fish tail, coin centre pin, person). Each symbol is one connected shape, except the coin's centre pin. | In 194 readers, only 13 of 30 point symbols met discriminability criteria; the most confused pairs were solids of different form, closed outlines of different form, and open outlines of different form [15, citing Jansson 1972]. Readers count corners and treat every pin as meaningful; a small feature works best as a single pin [14]. A gap under the person's head made it read as two objects (owner feedback). | Comment in `SYMBOLS`; `test_each_symbol_is_felt_as_one_object` |
| **Pixel-art drawing on the pin grid.** Outlines are one pin wide; diagonal steps touch only at their corners; drawings are redrawn for the grid instead of shrunk, and use the full space. | Guidelines G1–G6 for primitives on a pin display (square, rectangle and triangle 100 % recognised; circle 6 of 8) [14]; shrinking pictures to pin resolution lost crucial details, and larger drawings are recognised better [14, citing Bornschein et al. and Wijntjes et al.]. | `game/pets/shapes.py` (cat and dog at 36 × 24, with the proportions of the team's original drawings) |
| **Few symbols.** One shared vocabulary of 14 symbols (previously 23 names). Each symbol means one thing everywhere, and a page shows at most five different symbols. | No more than five types of point symbols on one graphic [1 §3.2.2]; symbols are assigned consistently throughout [1 §2.18]; raised-line maps support only about 10–15 distinct symbols [3]. | `SYMBOLS` and `SYMBOL_ALIASES` in `engine/display/icons.py`; the audit counts symbols per page |
| **Size and shape.** Symbols are 3–7 pins wide and at most 5 rows tall. They differ in shape (ring, diamond, drop, plus and so on), never only in size. | Differently shaped symbols need at least 1/4 inch (6 mm) to be told apart [1 §3.4.3.11]. Symbols of the same shape must differ in size by 25–30 % [1 §8.6.5], so the vocabulary avoids differences of size alone. | `test_symbol_vocabulary_is_small_and_fits_inside_a_frame` |
| **Simplify, and let speech be the label.** Decorative detail is removed (the village's dashed centre lines, the shop's carved windows and eaves). Every object speaks its name on hover, and Shift gives the long description. | Simplify as long as the intent survives; drop non-essential information and decorative frames [1 §2.8, §3.7.1, §2.5–2.6]; prefer a direct label to a keyed symbol [1 §2.17]. Blind participants strongly preferred a refreshable display combined with speech [7]. | Scene code in `game/home`, `game/village`, `game/shop` |

### Symbol vocabulary

| Symbol | Shape | Meaning (old names now pointing to it) |
|---|---|---|
| `seed` | small plus | seeds (`plant`) |
| `crop` | sprout on a stem | crops, harvesting (`harvest`) |
| `fish` | fish outline with a tail | fish |
| `mineral` | diamond outline | stone, copper, iron, diamond |
| `tool` | bar on a handle | pickaxe, rod, fertilizer, feed, the tool shop (`tools`) |
| `water` | drop outline | watering |
| `coin` | ring with a centre dot | gold, selling (`sell`) |
| `bag` | open basket (U shape) | the shop, buying (`shop_npc`, `buy`) |
| `person` | head joined to shoulders by a neck | Rowan and other people (`rowan`, `npc`) |
| `bed` | headboard and mattress | sleep |
| `pot` | pot with a lid and knob | kitchen, cooking (`stove`) |
| `page` | page with a folded corner | research, the calendar, saves, the guide (`chest`, `calendar`, `save`, `research`) |
| `arrow_up`, `arrow_down`, `arrow_right` | small solid triangle | a direction or exit (`nav_up`, `nav_down`, `start`) |
| `check` | tick | selected or done |
| two nested frames | no symbol | food and other usable items |
| frame only | no symbol | anything else; listen for the name (`material`) |

Old names keep working (`IconRenderer.PATTERNS["rowan"]` returns the person symbol), so saves, features and the icon lab are unaffected. Iterating `PATTERNS` lists only the canonical symbols.

### Where each icon comes from, and why it should be recognisable

None of these drawings has been tested with blind readers yet. The *basis* column gives the design reasoning and the studies behind it, not test results. "Team" means the drawing came from the project's own earlier icons on `main` (filled silhouettes); "this overhaul" means it was redrawn during the tactile updates. No icon was copied from a published, tested symbol set: the studies found test simple shapes and pictures, not these exact symbols.

| Symbol | Drawn as | Origin | Recognition basis | Test first |
|---|---|---|---|---|
| `seed` | 3 × 3 solid plus | Team's filled seed, reduced to a plus | Solid class [15]; small filled signs read better than outlines at small sizes [21]; a cross was among the shapes recognised fastest on a pin array [14, citing Bellik & Clavel] | Smallest symbol: 3 pins is the BANA minimum for telling shapes apart [1 §3.4.3.11] |
| `crop` | 5 × 5 V on a stem with a base | New in this overhaul (the team's sprout was a solid blob) | Open-lines class; the V top separates it from the T of `tool` | `crop` vs `tool` |
| `fish` | 7 × 5 outline with a forked tail | Team's fish, outlined; separate eye pin removed | Closed outline plus one protruding feature [15]; exaggerate the identifying feature [3] | — |
| `mineral` | 5 × 5 diamond outline | Team's diamond, outlined | Closed outline with four corners; corners are counted [14] | `mineral` vs `coin` and `water` |
| `tool` | 5 × 4 T (bar on a handle) | Team's hammer, head reduced to a bar | Open lines; a T-junction | `tool` vs `crop` |
| `water` | 5 × 5 drop outline | Team's drop, outlined | Closed outline with one pointed top | `water` vs `mineral` |
| `coin` | 5 × 5 ring with a centre pin | Team's filled disc, outlined; centre pin added | A single-pin feature reads well [14]; the centre pin separates it from other closed outlines [15] | `coin` vs `mineral`: pin circles were sometimes felt as octagons [14] |
| `bag` | 7 × 5 open basket (U) | New in the second round (the team's bag was a solid blob) | Open structure, unlike the closed coin and page beside it; closed outlines of different form are the most confused pairs [15] | — |
| `person` | 5 × 5 head on a neck and shoulders | Team's Rowan figure, joined by a neck pin | One connected shape; a gap under the head read as two objects (owner feedback) | — |
| `bed` | 7 × 4 headboard and mattress | Team's bed, outlined | Open lines; one familiar side view | — |
| `pot` | 7 × 5 pot with lid and knob | Team's stove, redrawn | Closed outline plus a feature (lid) | `pot` vs `page` |
| `page` | 5 × 5 sheet with a cut corner | New in this overhaul | Closed outline with one cut corner | `page` vs `pot` |
| arrows | small solid triangle | Team's navigation arrows, simplified | Solid small sign; triangles were recognised 100 % on a pin array [14] | — |
| `check` | tick | Team's tick, unchanged | Open line | — |
| frames | double frame = food, empty frame = other items | Team's frame convention | Frames carry no picture; speech names the item [1 §2.17] | — |
| Prize draw (shop only) | 7 × 5 starburst | New in the third round (the 7 × 7 wheel touched its frame) | Radiating open lines, unlike the closed coin | — |
| animal icons | 7 × 5 cat (ear points, raised tail), dog (snout, drooping ear), chicken, sheep | Cat and dog redrawn in the second round; chicken and sheep from the team | The identifying feature is at the top [3] | Only need to differ from each other on one page |

Test these pairs first, with the Nolan & Morris criteria under [References](#references-for-the-tactile-design).

### Where each graphic comes from

| Graphic | Drawn as | Origin | Basis |
|---|---|---|---|
| Rooms (home, shop) | Double divider, side walls with doorway gaps, small solid doorway arrows | Team's layout; walls opened around the arrows in the first round (`draw_room`) | Lines break where they meet a symbol [1 §2.11]; one lowered pin of space [1 §3.4.3.11] |
| Home furniture | Bed, chest and stove as outlines | Team's furniture, converted to outlines | Empty outlines were recognised best on pin arrays [14, citing Bellik & Clavel]; professor's feedback |
| Village | House outline with door and windows, road edges that stop before the arrows, Rowan as one figure | Team's scene, simplified | Remove decoration [1 §2.8]; break lines [1 §2.11] |
| Shop | Calendar, shopkeeper, prize wheel, three counters 12 pins wide showing coin, bag and tool | Team's scene, redrawn; counters widened in the third round | One lowered pin inside each counter; the same symbol for the same thing everywhere [1 §2.18] |
| Map | Square nodes, paths that end one pin before a node; the current node has a 3 × 3 centre mark | Team's map; marks redesigned in the first round | You-are-here marking on a pin display [9]; break lines [1 §2.11] |
| Farm | Plot outlines, growth as a vertical-line texture, exit arrows in the bottom corners | Team's plots; texture in the first round, exits in the second | Line texture from the pin-display pattern set [16, 23] |
| Plot detail | Growth gauge with vertical lines, field outline | Team; gauge moved one row down in the third round | One lowered row below the divider |
| Mine | Filled rocks with damage patterns | Team's original (restored) | Owner decision; exempt from the outline rule |
| Fishing lake | Large ellipse outline | Team | Outline rule |
| Pasture | Fence with a gate gap and exit arrow; woolly sheep filled; chicken textured | Team's pasture; exit added in the second round | Texture or fill on the identifying part (wool), as with the textured mane [17] |
| Cat and dog | 36 × 24 side view: solid legs, tail and ears; one-pin outline; line texture on the body only | Proportions of the team's original drawings (long body, head set on the body); identifying features exaggerated | See the *Animals* rule above; full-body side view, the same view for every animal, bigger is better [3, 24] |
| Chicken, shorn sheep | Same treatment as the cat and dog | Team's drawings | Same |
| Flower pot | Pot outline; plant stages drawn pin by pin | Team; pot outlined in the third round (the watering area is unchanged) | Outline rule |
| Cooking path | A line with a solid 4 × 4 start marker one pin away | Team; gap added in the third round | Break lines at symbols [1 §2.11] |
| Minigame targets | Small plus or 2 × 2 marks inside a field outline | Team | Small solid signs; sweep pages are exempt from the fill rule |
| Shearing field | Full fleece | Team | Owner decision: the wool is what is sheared |

### Dot review

Every registered page (46) plus the minigame, harvest, cooking, egg-collecting, shearing, flower and stocked-inventory states, 61 views in all, is rendered by `python engine/tools/tactile_audit.py --png DIR` and checked twice:

1. **By the rules.** `audit()` checks fills and object boxes. `SymbolTrace` records which drawing raised each pin, so a symbol touching a wall, a frame, a road or another symbol is caught even when one object box contains both (the General goods bag touched its own counter this way and the box check missed it).
2. **By eye.** Each picture (with and without object boxes) was looked at for things the rules cannot judge: odd shapes, crowded areas, unclear figures.

The third-round review found and fixed: the General goods bag touching its counter, the Prize draw wheel touching its frame, the growth gauge touching the divider, a solid flower pot, and the cooking start marker sitting on its path. After the fixes the audit reports 0 problems. Remaining by design: the filled mine rocks and the shearing field.

### Learning support: the Guide

A map scene may be easier to experience than a row of icons, but it needs more learning. Tactile pictures are named poorly without context. Across studies, raised-line pictures are named correctly about 42 % of the time on average (range 9–85 %) [5, citing Picard & Lebaz 2012]. Knowing the category, or hearing a description first, raises accuracy: from 51.6 % to 70.7 % in [5]; see also [8]. In TactIcons, "learnable" icons were remembered after a single exposure to the key [3]. Game accessibility guidance asks for a tutorial that can be replayed at any time and a way to practise without failing [10, 11]. The game therefore adds:

- **Guide** (`game/guide/`). It opens from the Guide button at the top left of the F1 map and has six topics: *Touch and listen*, *Select*, *Sweep tasks*, *Keys*, *Screen layout* and *Symbol key*. Touching a topic speaks its name; selecting it reads the explanation. It costs no time, gold or items and can be repeated at any time.
- **Symbol key.** Five pages of four symbols each (*things you grow and find*, *tools and trade*, *places and people*, *signs*, *animals*), so every page stays within the five-symbol limit. Selecting an animal opens the **animal gallery**: the same large drawing used in the game with a spoken description of what to feel for; Right shows the next animal. Touching a symbol speaks its name; selecting it describes its shape and where it is used. Left and Right turn pages.
- Rowan's tutorial quests in the village still teach the activities themselves. The guide teaches how to read the pad.

**Are the animal drawings (cat, dog, chicken, sheep) recognizable?** Probably not by touch alone. Raised-line pictures of familiar objects are identified poorly, and congenitally blind readers do worse [6]. Category information improves identification [8]. Blind participants matched pictures far more accurately than they named them [8]. No study of animal recognition on the Dot Pad itself was found. The game therefore never relies on recognition:
- every animal speaks its name and state on hover;
- the large drawings are full-body side views with the proportions of the team's original drawings and the features that tell the species apart exaggerated (cat: tall pointed ears, upright curling tail; dog: long snout, drooping ear, thick legs, short tail), solid limbs, an outlined body with a line texture to stroke, and an empty head outline;
- the small 7 × 5 icons only need to be told apart from each other on one page;
- the animal gallery in the guide lets the player feel each drawing with its name before meeting it in play. Even with a category cue, recognition stays around 31–52 % [17, 18], so speech remains the main channel.

Before changing the drawings, test them with at least three novice and three congenitally blind readers [3].

### Changes in this update (tactile overhaul)

Engine changes were approved by the owner and stay within the existing hover-based point-and-click design.

| Area | Change |
|---|---|
| `engine/display/tactile.py` (new) | Rules and checker: `MIN_GAP`, `MAX_SOLID_SIDE`, `MAX_FILL_RATIO`, `MAX_SYMBOLS_PER_PAGE`, `outline_rows()`, `audit()` |
| `engine/tools/tactile_audit.py` (new) | Renders the main pages (home, village, shop, map, mine, farm, inventory, pets, pasture, guide and others) and lists rule violations; `--show` prints the dots |
| `engine/tests/python/display/test_tactile_rules.py` (new) | Every audited page passes; vocabulary size and symbol size; aliases; the Tools counter symbol |
| `engine/display/icons.py` | 23 symbol names reduced to 14 outline-style symbols (`SYMBOLS`) plus aliases (`SYMBOL_ALIASES`, `SymbolTable`). An unknown kind shows the frame alone instead of a solid block |
| `engine/core/render.py` | `draw_room()`, shared by the home and shop scenes: walls open two pins around the doorway arrows |
| `engine/core/petting.py` | `next_feedback_id()`: petting sound IDs are unique (bug fix below) |
| `engine/display/keypad.py` | Uses the empty frame instead of the removed solid `material` block |
| `engine/web/game.html` | Loads `game/guide/client.js` |
| `game/__init__.py` | `guide` added at the end of `ENABLED` |
| `game/guide/` (new) | Guide topics and symbol key. Adds no engine attribute (the key page number is part of the page id), so the save format is unchanged |
| `game/minimap/` | New slot `minimap.objects` (holds the Guide button). Paths stop one pin short of nodes. The current node is an outline with a 3 × 3 centre mark |
| `game/home/`, `game/shop/`, `game/village/` | Scenes redrawn as outlines. Doorway and road-end arrows are clear of walls and road edges; road edges stop before the shop; decorative centre lines removed |
| `game/pets/`, `game/pasture/` | Large animal drawings shown with a lowered interior (replaced in the second round, below) |
| `game/farming/` | The growth fill and the growth gauge use a line texture instead of solid blocks |

Second round (owner feedback after the first update):

| Area | Change |
|---|---|
| `game/pets/` | **Bug fix:** the home Care page drew the doorway arrows but had no arrow objects, so Left/Right answered "Cannot go left/right"; they now travel to the farm and the village like on the home page. New `shapes.py`: cat and dog redrawn from simple shapes so the species differ in ears, snout, legs and tail in every pose; new 7 × 5 icons (cat: ear points and raised tail; dog: snout and floppy ear); the large drawing has solid limbs and a fur texture |
| `game/farming/`, `game/pasture/` | Tactile exits at both ends of the farm (bottom left: pasture, bottom right: home) and on the pasture's east fence (to the farm), selectable and spoken, one lowered pin clear of the plots and fence |
| `game/mining/` | Rolled back to the original filled rocks with damage patterns (owner decision) |
| `game/pasture/` | The woolly sheep stays filled (scene and detail); the chicken and the shorn sheep get solid legs and a textured body |
| `engine/display/icons.py` | `person` joined into one shape (head, neck, shoulders); `bag` is now an open basket so it differs in structure from the coin and page next to it; `fish` without a separate eye pin and `pot` without separate steam dots, so each is one shape |
| `game/village/`, `game/shop/` | Rowan and the shopkeeper drawn as one connected figure |
| `engine/display/tactile.py` | `fur_rows()`, `close_gaps()`, and the `filled_by_design` exemption in `audit()` |
| `game/guide/` | Fifth symbol-key page, *Animals*, and an animal gallery (`guide_animal_cat` … `guide_animal_sheep`): selecting an animal shows the same large drawing used in the game, with a spoken description of what to feel for. Practice with tactile pictures roughly doubled recognition (41.7 % for regular vs 21.2 % for rare users) [17] |

Third round (owner feedback: symbols still touched walls; the cat looked odd):

| Area | Change |
|---|---|
| `engine/display/tactile.py` | `SymbolTrace`: records which drawing raised each pin, so a symbol touching its own frame is caught. `fur_rows()` rewritten: one-pin outline, lowered channel, horizontal line texture, no isolated pins, optional `mask` |
| `engine/tools/tactile_audit.py` | Checks every registered page plus minigame, harvest, cooking, egg-collecting, shearing and flower states; `--png DIR` saves pictures for a visual dot review |
| `game/shop/` | Counters are 12 pins wide (the 7-pin bag had no gap on one side). The Prize draw icon is a 7 × 5 starburst (the 7 × 7 wheel touched its frame) |
| `game/farming/` | Growth gauge one row lower (it touched the divider) |
| `game/flowers/` | The pot is an outline (it was a 21 × 6 solid block); the blossom is drawn as part of its stem |
| `game/cooking/` | Path pins around the start and resume markers are lowered (the marker sat on the path) |
| `game/pets/` | Cat and dog redrawn with the proportions of the team's original drawings. The second-round cat had a longer neck and a smaller body; that came from building it out of shapes, not from any source. Texture only on the body (`shapes.TEXTURE`, `shapes.drawing()`) |
| `engine/tests/python/display/test_tactile_rules.py` | Trace test (a symbol touching its own frame), no isolated pins in animal drawings |

Bugs fixed:

- **The shop's Tools button showed the General goods symbol.** `shop_tools_choice` had `choice: "buy"`. It is now `"tools"` and shows the tool symbol, and the Tools counter in the shop scene shows a tool instead of a second bag.
- **Petting sounds could be skipped on Windows.** Feedback IDs came from `time.monotonic_ns()`, which repeats within its tick of about 15 ms. A second completion could reuse the first ID, and the browser would then not play it. IDs now include a counter.
- **Stale tests.** Pasture and research tests expected old prices (egg 70, feed 30, shelter wool 2 and 4). The configuration had already been changed to egg 50, feed 80 and wool 3 and 6. The tests now follow the configuration; the game rules were not changed.

### References for the tactile design

**[V]** means the item was read on its source page. **[S]** means it is known only from search results or secondary sources; check [S] items before citing them in a paper.

1. Braille Authority of North America (2010). *Guidelines and Standards for Tactile Graphics, 2010*. Web manual: https://www.brailleauthority.org/tg/web-manual/tgmanual.html (sections cited above) **[V]**. A 2022 PDF edition is on the same site; its section numbers were not re-checked. Korean translation: 국립장애인도서관 (2015) **[S]**.
2. Holloway, L., Marriott, K., & Butler, M. (2018). Accessible Maps for the Blind: Comparing 3D Printed Models with Tactile Graphics. *CHI '18* **[S]**.
3. Holloway, L., Butler, M., & Marriott, K. (2023). TactIcons: Designing 3D Printed Map Icons for People who are Blind or have Low Vision. *CHI '23*. https://doi.org/10.1145/3544548.3581359 **[V]**
4. Holloway, L., et al. (2022). Animations at Your Fingertips: Using a Refreshable Tactile Display to Convey Motion Graphics for People who are Blind or have Low Vision. *ASSETS '22*. https://doi.org/10.1145/3517428.3544797 **[S]**. A 60 × 40 refreshable display needs much more simplification than paper graphics.
5. Vinter, A., Orlandi, O., & Morgan, P. (2020). Identification of Textured Tactile Pictures in Visually Impaired and Blindfolded Sighted Children. *Frontiers in Psychology*, 11, 345. https://doi.org/10.3389/fpsyg.2020.00345 **[V]**
6. Lederman, S. J., Klatzky, R. L., Chataway, C., & Summers, C. D. (1990). Visual mediation and the haptic recognition of two-dimensional pictures of common objects. *Perception & Psychophysics*, 47, 54–64 **[S]**.
7. Reinders, S., et al. (2024). When Refreshable Tactile Displays Meet Conversational Agents. *IEEE TVCG* (VIS 2024). https://doi.org/10.1109/TVCG.2024.3456358 **[V, abstract only]**
8. Heller, M. A., Calcaterra, J. A., Burson, L. L., & Tyler, L. A. (1996). Tactual picture identification by blind and sighted people: Effects of providing categorical information. *Perception & Psychophysics* **[S]**. Heller (2002) on matching versus naming **[S]**.
9. Zeng, L., & Weber, G. (2016). Exploration of Location-Aware You-Are-Here Maps on a Pin-Matrix Display. *IEEE Transactions on Human-Machine Systems*, 46(1), 88–100 **[S]**. Zeng, L., Miao, M., & Weber, G. (2015). Interactive audio-haptic map explorer on a tactile display. *Interacting with Computers*, 27(4), 413–429. https://doi.org/10.1093/iwc/iwu006 **[S]**. Both use map symbols with audio on a pin-matrix display; the full texts were not read.
10. Yuan, B., Folmer, E., & Harris, F. C. (2011). Game accessibility: a survey. *Universal Access in the Information Society*, 10(1), 81–100. https://doi.org/10.1007/s10209-010-0189-5 **[S]**
11. Game Accessibility Guidelines, https://gameaccessibilityguidelines.com/ (practice without failing; reminders of controls and objectives) **[S]**.
12. Bhatnagar, T., et al. (2023). Pixelated Interactions: Exploring Pixel Art for Graphical Primitives on a Tactile Display. *DIS '23*. arXiv:2305.19444 **[V, abstract only]**. Eight tactile readers found pixel-art shapes on a pin array clear. Full text: [14].
13. Prescher, D., Bornschein, J., & Weber, G. (2017). Consistency of a Tactile Pattern Set. *ACM TACCESS*. https://doi.org/10.1145/3053723 **[S]**. Bornschein, J., et al. (2018). Comparing Computer-Based Drawing Methods for Blind People with Real-Time Tactile Feedback. *CHI '18*. https://doi.org/10.1145/3173574.3173689 **[S]**. Background on area patterns and drawing on pin-matrix displays, for future textures and editors.

14. Bhatnagar, T., Upadhyay, V., Sharma, A., Rao, P. V. M., Miodownik, M., Marquardt, N., & Holloway, C. (2023). Pixelated Interactions: Exploring Pixel Art for Graphical Primitives on a Tactile Display. *DIS '23*. arXiv:2305.19444 **[V, full text]**; DOI 10.1145/3563657.3596044 (from the repository record, not checked on a resolver). 27 × 27 pin display, eight blind adults; guidelines G1–G6; reviews pin-display studies by Bellik & Clavel, Velázquez, Bornschein et al. and Wijntjes et al.
15. Gill, J. M., & James, G. A. (1973). A study on the discriminability of tactual point symbols. *AFB Research Bulletin*, 26, 19–34. https://www.duxburysystems.org/downloads/library/history/afb_rb_26_1973.pdf **[V]**. Cites Nolan & Morris (1971) for the test criteria and Jansson (1972) for the confusable classes.
16. Prescher, D. (2016). *Taktile Interaktion auf flächigen Brailledisplays*. PhD thesis, TU Dresden, §7.3.2 and appendix F **[V]**; published as Prescher, D., Bornschein, J., & Weber, G. (2017). Consistency of a Tactile Pattern Set. *ACM TACCESS*, 10(2), 7. https://doi.org/10.1145/3053723 **[S]**.
17. Theurel, A., Witt, A., Claudet, P., Hatwell, Y., & Gentaz, E. (2013). Tactile picture recognition by early blind children: The effect of illustration technique. *Journal of Experimental Psychology: Applied*, 19(3), 233–240. https://doi.org/10.1037/a0034255 **[V]**
18. Picard, D., Albaret, J.-M., & Mazella, A. (2014). Haptic identification of raised-line drawings when categorical information is given. *Psicológica*, 35, 277–290 **[V]**. With a category cue, visually impaired children named 51.9 % of drawings (blindfolded sighted children 37.5 %).
19. Connor, C. E., Hsiao, S. S., Phillips, J. R., & Johnson, K. O. (1990). Tactile roughness: neural codes that account for psychophysical magnitude estimates. *Journal of Neuroscience*, 10(12), 3823–3836. https://doi.org/10.1523/JNEUROSCI.10-12-03823.1990 **[S]**. Perceived roughness of raised dots peaks near 3 mm spacing, so a 2.5 mm pin grid feels rough.
20. O'Modhrain, S., Giudice, N. A., Gardner, J. A., & Legge, G. E. (2015). Designing Media for Visually-Impaired Users of Refreshable Touch Displays. *IEEE Transactions on Haptics*, 8(3), 248–257. https://doi.org/10.1109/TOH.2015.2466231 **[S]** (full text not read).

21. Mascle, C. (2020). *Le livre tactile illustré : influence de la technique d'illustration sur la reconnaissance des images*. PhD thesis, Université Toulouse 2 Jean Jaurès. Repository PDF: https://dante.univ-tlse2.fr/files/original/2115ecdc02a126b329722093a1e11088f420fae1.pdf **[V, via text extraction]**. Study 3: 5 × 5 tactile pictograms (cat, bird, sheep and others), each keeping one identifying feature; line versions 88.0 % vs dot versions 62.6–64.8 % (cat: 75.0 % vs 50.0 / 42.8 %); in dot versions filled shapes beat outlines. Related article: *Tactile perception of line and dotted pictograms by sighted and blind people*, https://isidore.science/document/10670/1.223f20794ea2ceb76f66b394e408af46fdb5ef68 **[S]** (dot pictograms need fewer dots and no curves).
22. Kalia, A., Hopkins, R., Jin, D., Yazzolino, L., Verma, S., Merabet, L., Phillips, F., & Sinha, P. (2014). Perception of tactile graphics: embossings versus cutouts. *Multisensory Research*, 27(2), 111–125. https://pmc.ncbi.nlm.nih.gov/articles/PMC5757243 **[V]**. Cutout silhouettes were recognised more often than raised-line drawings; a textured background did not help in pilot data.
23. American Printing House for the Blind. *Best Practices and Standards for Creating Monarch Tactile Graphics* (reference document for the Monarch pin display, about 10 dpi). https://louis.aph.org/documents/Best-Practices-Monarch-Reference.docx **[V]**. "The larger the details of a texture, the better"; at least 3/16 inch between texture lines and 1/8 inch of blank space between elements.
24. Build a Better Book, University of Colorado Boulder. Tactile picture book project and guidance: https://www.colorado.edu/project/bbb/creating-tactile-graphics **[S]**. Show all animals in the same view; highlight one identifying part rather than the whole furry body.
25. Thompson, L. J., Chronicle, E. P., & Collins, A. F. (2003). The role of pictorial convention in haptic picture perception. *Perception*, 32(7), 887–893. https://doi.org/10.1068/p5020 **[S]**. Thompson, L. J., Chronicle, E. P., & Collins, A. F. (2006). Enhancing 2-D tactile picture design from knowledge of 3-D haptic object recognition. *European Psychologist*, 11(2), 110–118. https://doi.org/10.1027/1016-9040.11.2.110 **[S]**. Uniformly textured pictures were identified better than line drawings.

Pin-display studies cited through others: Bellik & Clavel (2017; 60 × 60 pins, empty outlines best) and Velázquez et al. (2008; filled shapes confused) are known from [14] and [21] only **[S]**.

Existing Dot Pad games: Dot Vision (SmileShark with Dot Inc., 2024) is a set of arcade-style Dot Pad games known only from press coverage **[S]**; no evaluated game on any pin display was found, so this game's rules rest on the symbol, picture and texture studies above.

**Test criteria for user testing.** To cut testing to a pass/fail check, use the Nolan & Morris criteria quoted in [15]: a symbol passes when its average confusion with the other symbols is at most 5 % and its confusion with any single symbol at most 10 %. Test the symbols that share a page (the per-page limit keeps that at five or fewer), and test the animal drawings by naming with the category given, as in [18].

No peer-reviewed study of icon or shape recognition on the Dot Pad itself was found, and no Korean national tactile-graphics standard with spacing figures was found. Open questions for user testing:
- large outlines versus large solid shapes on single-height pins;
- whether one lowered pin (about 2.5 mm) is enough, or two are needed;
- how well thin outlines hold up when a finger presses the pins down.

## Folders

| Folder | What is in it |
|---|---|
| `engine/` | Shared code: server, engine core, Dot Pad display, saves, speech, browser player (audio, keys, pad), Visual Companion, configuration, launcher and installer logic, camera tracking, dev tools and shared tests. See [engine/README.md](engine/README.md). |
| `game/` | One folder per feature (cook, cooking, farming, fishing, flowers, harvest, home, inventory, minimap, mining, npc, pasture, pets, research, roulette, seafood, shop, village) with its Python code, browser texts, sounds, images, tests and README. See [game/README.md](game/README.md). |
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
| `engine/display/icons.py`, `keypad.py`, `dotpad.py`, `tactile.py` | Three-row/four-column icon slots, the shared symbol vocabulary, frames, navigation, dot drawing and the tactile design rules |
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
| `guide/` | Replayable tutorial and symbol key, opened from the F1 map |
| `farming/`, `harvest/` | Plot state, planting, water/fertilizer activities, growth and harvest |
| `cooking/`, `seafood/` | Recipes, ingredient selection, paths and fish-dish variants |
| `mining/`, `fishing/` | Rocks, catches, tool wear and resource prices |
| `flowers/` | Pot interaction, daily plant state, bloom contribution, seed selection and nutrients |
| `pets/` | Adoption, names, slots, care, health, gifts, movement and animal dots |
| `roulette/` | Weighted rewards, the five-draw queue, special items and gold tool upgrades |
| `inventory/`, `shop/` | Item lists, pagination and transactions |
| `research/` | Upgrade costs, levels, plot expansion and animal-shelter research |
| `pasture/` | Animal ownership, movement, feed, hidden petting, production, escape and collection |
| `cook/` | Shared ingredient access for eggs and the existing cooking system |
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
| `display.js` | Existing bundle on the game page; the separate window loads `viewer.js` |
| `viewer.js`, `model.mjs`, `viewer.css` | Scene drawing, state-to-layout mapping and interface styles |
| `visual-assets.json` | Backgrounds, facilities, items and sprite rectangles |
| `scene-objects.json` | Facility positions, sizes and order |
| `assets/` | Shared atlases; feature art also lives in `game/<feature>/assets/` |

The separate window shows the pet house and moving active pet at home, and the roulette object beside the shopkeeper. Pet detail pages currently use the tactile fallback.

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
| `dog_main`, `cat_main`, `dog_routine`, `cat_routine` | Pet entry/care and routine calls, with per-pet pitch |
| `feed`, `brush` | Normal/special feed and petting, independent of animal calls |
| `roulette` | Prize draw; result speech follows the sound start by at least one second |
| Synthetic cues and target beacons | Selection, errors, progress and optional directional target guidance |

Task spatial sound places the pointer relative to the pad centre. Fishing places the hidden target relative to the pointer. Target beacons are a separate guide to remaining farm/mine targets and can be disabled with **Target cues**. Shop entry and trading remain nonspatial; travel uses the pressed direction. Current task routing uses `dry_gain: 0`, avoiding a centred copy that can weaken direction. Repeat presses do not add another copy over an active work loop, and structured sound events suppress overlapping legacy feedback. These controls do not make every sound spatial.

Speech uses fixed English Piper models, not the browser's operating-system voice. The system guide uses `en_US-hfc_female-medium`; Rowan uses `en_US-hfc_male-medium` (the internal profile key is still `shopkeeper`). Models, cached WAVs and reports are in `.audio/voices/`, `.audio/cache/` and `.audio/reports/`. **Test guide**, **Test Rowan**, **Replay**, speech stop/on/off, rate and volume controls are available. Speech volume defaults to 85% and is separate from music/effects.

Action results and dialogue take priority over hover text. Requests carry client and sequence information so stale replies do not replace newer speech. New NPC dialogue replaces old dialogue; ordinary hover does not interrupt it. Leaving the window silences playback and discards late replies. On return, current music and lake sound can resume without replaying old speech. Speech can lower background music and selected effects; fishing exploration retains its configured gain.

Initial prompts and visible page text are synthesized and decoded in the background at low priority to reduce first-play delay. Prepared speech is reused; new text or an unprepared voice model still needs synthesis time. Prize-draw results retain the existing speech priority and cancellation behavior.

### Configuration reference

Edit **`engine/config/game.json`**, not the former root `game_config.json`, then restart the server. Values below describe this checkout. Ticks are game time, `_ms` values milliseconds, coordinates dots, and probabilities normally 0–1. Audio gains are linear multipliers and can exceed 1; they are not slider percentages. The following numeric chances are developer settings, not player-facing dialogue.

| Path in `game.json` | What it changes / current value |
|---|---|
| `game.start_day`, `resources` | Starting day (1), gold, fertilizer, seeds and crops |
| `time.total_cells`, `time.action_costs` | Day length (20), per-action costs listed above |
| `seeds.<id>.growth_days`, `.yield`, `.seed_price`, `.crop_price`, `.seed_return_chance` | Growth, yield, prices and baseline seed recovery (0.1) |
| `fertilizer.growth_day_bonus`, `shop.fertilizer_price` | Immediate growth bonus (1 day); fertilizer reference price (12) retained for tool pricing, not direct fertilizer sales |
| `research.seed_return` | Gold `[20,40]`, copper `[3,6]`, recovery `[0.3,0.6]`, maximum level 2 |
| `research.field_expansion` | Initial 2 plots; gold `[30,50,70,90]`, stone `[5,10,15,20]` |
| `research.mineral_luck` | Gold `[20,40]`, iron `[3,6]`; diamond weight +1 and double-drop chance +0.15 per level |
| `research.animal_shelter` | Maximum level 2; gold `[150,250]`, wool `[2,4]`, independent per-product bonus chances `[0.15,0.30]` |
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
| `pasture.animals.<id>` | Animal purchase/product prices, `wait_days`, `wait_weights`, egg `double_egg_chance` (0.2) and `ready_capacity` (3), wool `yield_range` ([2,5]) |
| `pasture.feed_price`, `.pet_seconds` | Shared feed base price 80 gold; petting reward after 3 seconds of movement, once per day |
| `pasture.escape_grace_days`, `.escape_increment` | Affection-tier grace periods `[1,2,3]`; daily escape chance is excess unfed days × 0.1, clamped to 0–1 |
| `pasture.move_interval_seconds`, `.flip_interval_multipliers`, `.breath_seconds` | Movement every 3–5 seconds; independent flips after 3–5 times a sampled interval; breathing step 1.5 seconds |
| `pasture.shear_radius`, `.shear_success_ratio` | Eraser radius 5.5 dots; complete at 75% of fleece dots removed |
| `pasture.audio` | Routine interval/gain, main-call gain and morning-call delay |
| `time.action_costs.animal_collect`, `recipes.fried_egg` | Collection costs 3 ticks; egg-and-carrot recipe with one-use research discount |
| `flowers.species`, `.watering_seconds`, `.contact_gap_seconds` | Morning glory, sunflower and orchid; 3 seconds contact; maximum sample gap 0.5 seconds. Legacy `seed_price` is not used for direct sales |
| `flowers.sprout_days`, `.stem_days`, `.bloom_cycle_days` | 2 watered days per early stage; 3-day bloom-age cycles |
| `flowers.bloom_wilt_increment`, `.dry_wilt_increment`, `.harvest_bonus` | Hidden wilt increments 0.1 per bloom cycle and 0.3 per dry day; blooming crop bonus +1 |
| `pets.max_pets`, `.names`, `.pitch_values` | Up to 6 pets, 12 names per species, pitches `[0.88,1.04,0.96,1.12,0.92,1.08]` |
| `pets.pet_seconds`, `.contact_gap_seconds`, `.pet_points`, `.feed_points`, `.treat_points` | Petting 3 seconds, sample gap 0.5 seconds; affection gains 10 / 5 / 60 |
| `pets.hungry_days`, `.sick_after_days`, `.neglect_points` | Hungry after 2 unfed days, sick after 4; affection loss 10 on hungry days |
| `pets.gift_chances`, `.trusted_harvest_bonus` | Gift chances by tier `[0,0.15,0.30]`; trusted-pet crop bonus 1 |
| `pets.audio` | Calls every 8–14 seconds; routine gain 0.35, cat routine 0.8, main 1.3 |
| `roulette.price`, `.weights` | 200 gold per draw; reward weights from the table above |
| `roulette.seed_quantity`, `.fertilizer_quantity`, `.voucher_sell_price`, `.medicine_price` | 3 seeds/fertilizer per reward; voucher sale 300; medicine base price 30 |
| `roulette.nutrient_days`, `.gold_durability_multiplier`, `.result_delay_ms` | Wilt protection 6 days, effective tool-use divisor 4, result speech delay 1000 ms |
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
| `python engine/tools/tactile_audit.py [--show]` | Check the main pages against the tactile design rules (gaps, outlines, symbols per page) |

A failed launch does not always mean the port is occupied. Check the preceding setup/speech error first, verify voices with `check_setup.py`, and rerun the installer for missing or damaged downloads. Use the address printed by the launcher. Do not close an unrelated process merely because it uses the requested port.

## Further development and evaluation

Planned work includes additional plants and pets, ranching, more recipes and quests, music and crafting. Shared work includes reconciling the companion bundle with its sources and reducing remaining cross-feature dependencies.

User evaluation should test the open tactile design questions listed under [References](#references-for-the-tactile-design) and record task success, completion time, accidental input, understanding of tactile/audio information and workload. Compare pointer delay on older laptops, camera calibration and occlusion, tactile legibility, voice pronunciation and stereo guidance with actual hardware.

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

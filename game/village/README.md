# Village

Rowan's sequential tutorial quest (soup → seeds → bring a vegetable → advice), the town square, and the weekly market that changes prices by weekday.

| Item | Value |
|---|---|
| Code | `feature.py` (`Village`) |
| Pages | `town` (scene drawing, icon grid, first-arrival greeting); `rowan_submit` (choose a vegetable); `shop_calendar`, `rowan_dialogue` (unreachable since before the split, kept with their save migrations) |
| Actions (before the night guard) | `talk_rowan`, `repeat_rowan`, `rowan_submit:<seed>`, `open_calendar`, `calendar_day:<n>` |
| Object types | `rowan`, `nav_up`, `nav_down`, `calendar_day`, `calendar_button` (icons); `town_hitbox` scene targets |
| Owned engine attributes (save format) | `rowan_stage`, `rowan_greeted`, `rowan_dialogue`, `rowan_submit_open` |
| Shared attributes written | `resources` (`foods.rowan_soup`, `seeds`, `crops` via `add_resource`, `coin` via `add_resource`), `current_page` (via `set_page`), `hover_object_id` |
| Shared attributes read | `config`, `day`, `current_location`, `current_page`, `resources` |
| Events | `reset` (`Reset.VILLAGE`), `close_dialogue` (travel and opening the shop clear Rowan's line) |
| State keys | `rowan_submission`, `calendar` |
| Saves | Defaults for all four attributes; migration moves saves made on `rowan_dialogue`/`rowan_submit`/`shop_calendar` to their replacement pages |
| Engine API provided | `market_price(price, kind, mode)` (used by shop, mining, fishing), `talk_rowan()`, `submit_rowan_crop(seed)`, `open_calendar()` |
| Engine API used | from NPC: `recent_reaction`, `npc_voice_profile`, `rowan_advice`, `next_rowan_advice`; from seafood: `sale_price` |
| Config | `engine/config/game.json` → `rowan.*`, `weekly_market.*`, `town.objects`, `seeds`; page name `pages.town` |
| Slots | none |
| Client (web) | `game/village/client.js` (town task text) |
| Tests | `engine/tests/python/audio/test_team_audio.py`, `engine/tests/python/speech/test_speech.py` (5 of 8 known Rowan failures, follow-up F1) |
| Note | The home/town icon sort in `engine/display/icons.py` still names the `town` page. |

## Gameplay

Rowan stands beside the shop. Talking to him keeps the village page: the first talk gives one Rowan's soup (stew image and harvest effect, sells for 100, cannot be cooked); after you use or sell it he gives one seed of each crop (`rowan.seed_gift_each`); then the farming tutorial; bring any one crop and select it on the submission page (owned crops only) for 100 gold (`rowan.vegetable_reward_gold`). Gifts and rewards are given once; quest progress is saved, and older saves start the quest from the beginning. Either arrow cancels the submission page.

Game day 1 is Monday; the shop counter's Calendar button speaks the week's offers. They repeat every seven days (`weekly_market`, 20 %):

| Day | Offer |
|---|---|
| Monday | Ore purchases 20 % off |
| Tuesday | Cooked food sells for 20 % more |
| Wednesday | Fish sells for 20 % more |
| Thursday | Seeds 20 % off |
| Friday | Ore sells for 20 % more |
| Saturday | Fertilizer, pickaxes and fishing rods 20 % off |
| Sunday | Everything sells for 20 % more |

Prices are rounded down after the day's change; an active sale-boost food applies afterwards and rounds down again. Research costs and quest rewards are unaffected. The companion shows Rowan and his portrait from `game/npc/assets/rowan.png` and never sends game input.

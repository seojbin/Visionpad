# Village

Rowan's sequential tutorial quest (soup → seeds → bring a vegetable → advice), emergency crop seeds, the town square, and the weekly market that changes prices by weekday.

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
| Tests | `game/village/tests/test_seed_help.py` (seed help, quest priority, speech channel, repeat prevention and save restore), `engine/tests/python/audio/test_team_audio.py`, `engine/tests/python/speech/test_speech.py` (5 of 8 known Rowan failures, follow-up F1) |
| Note | The home/town icon sort in `engine/display/icons.py` still names the `town` page. |

## Gameplay

If the player owns no plantable crop seeds, talking to Rowan first gives one carrot seed for free. He says he found it on the path and suggests planting and watering it. This takes priority at every tutorial stage, including after completion, without advancing the quest, consuming a pending activity reaction or spending time or gold. Talk again to continue the existing quest. Rowan's icon and scene target both announce that seeds are available; hovering or replaying dialogue never gives items.

Any positive stock of a configured crop seed prevents another gift. Flower seeds do not block help because they cannot restart crop farming. There is no gold requirement or daily limit: if crop seeds run out again, Rowan can help again. If carrot is removed from the crop configuration, the first configured crop is used instead. The gift uses the existing seed inventory, quest speech channel and companion dialogue; no new save fields, voice model or audio files are required.

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

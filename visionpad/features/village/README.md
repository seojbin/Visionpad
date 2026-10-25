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
| Config | `config/game.json` → `rowan.*`, `weekly_market.*`, `town.objects`, `seeds`; page name `pages.town` |
| Slots | none |
| Client (web) | `web/features/village/client.js` (town task text) |
| Tests | `tests/python/audio/test_team_audio.py`, `tests/python/speech/test_speech.py` (5 of 8 known Rowan failures, FOLLOWUPS F1) |
| Note | The home/town icon sort in `visionpad/display/icons.py` still names the `town` page. |

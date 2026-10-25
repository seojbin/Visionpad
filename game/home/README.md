# Home

The home page: bed, research chest and kitchen icons, the drawn home scene with its hitboxes, and the roads to the farm and the village.

| Item | Value |
|---|---|
| Code | `feature.py` (`Home`) |
| Pages | `home` (icon grid, scene drawing, location text) |
| Actions | none of its own; objects carry `rest` (core time/sleep), `open_research` (research), `open_recipes` (cooking), `flower:open` (flowers), `travel:*` (core) |
| Object types | `bed`, `chest`, `stove` (icons, hover sounds, home/town grid order 0–2), `home_hitbox` (scene targets; hover speech is the label) |
| Owned engine attributes | none |
| Shared attributes read | `config` (`home.objects`, `recipes`), `day_ended`, `dotpad` |
| Slots declared | `home.objects`, `home.scene_objects`, `home.scene` (order tables `order.HomeObjects`, `HomeSceneObjects`, `HomeScene`); flowers contributes |
| Engine API used | `can_craft_recipe` (cooking) for "Kitchen. Available recipes: N."; `draw_icon_pattern`, `draw_solid_pattern` (core) |
| Config | `engine/config/game.json` → `home.objects`; page name `pages.home` |
| Events | none |
| Client (web) | `game/home/client.js` (home task text) |
| Tests | No dedicated tests. Covered through `engine/tests/python/audio/test_audio_flow.py` and `engine/tests/python/saves/test_save_compat.py`. |

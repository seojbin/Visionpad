# Flowers

The houseplant at home: buying morning glory seeds, planting, watering by keeping the hand over the pot, daily growth and wilting, and the harvest bonus while it blooms.

| Item | Value |
|---|---|
| Code | `feature.py` (`Flowers`) |
| Pages | `flower_detail` ("Flower pot") |
| Actions | `flower:open`, `flower:plant`, `flower:water`, `flower:empty` (run before the night guard; the handler checks `day_ended`) |
| Object types | `flower_pot` (icon on home, full drawing on the detail page) |
| Owned engine attributes (save format) | `flower_seeds`, `houseplant`, `flower_watering`, `flower_contact_at` |
| Shared attributes written | `resources["coin"]` (via `add_resource`), `current_page` (via `set_page`), `last_pointer` |
| Shared attributes read | `config`, `current_page`, `day_ended`, `paused`, `sleep_until`, `dotpad` |
| Events | `reset` (`Reset.FLOWERS`), `end_of_day` (`EndOfDay.FLOWERS`), `before_navigation` |
| Slots contributed | `home.objects`, `home.scene_objects`, `home.scene`, `inventory.items`, `shop.buy_items` (fixed price), `harvest.bonus` |
| State key | `flowers` in `/api/state` |
| Saves | `flower_contact_at` and `flower_watering` are reset on save and load; all four attributes default from a fresh engine for older saves |
| Config | `engine/config/game.json` → `flowers.*` (`seed_price`, `watering_seconds`, `contact_gap_seconds`, `sprout_days`, `stem_days`, `bloom_cycle_days`, `bloom_wilt_increment`, `dry_wilt_increment`, `harvest_bonus`) |
| Engine API used | none from other features; core helpers `add_resource`, `resource`, `set_page`, `back_arrow`, `draw_solid_pattern`, `night_only_response` |
| Client (web) | `game/flowers/client.js` (100 ms pointer re-send while the mouse rests on the pot during watering); textures `engine/web/spectator/assets/flower-backgrounds.png`, `flower-items.png`, `flower-stages.png` |
| Tests | No dedicated tests yet. Covered by `engine/tests/python/saves/test_save_compat.py` (owned attributes) and `engine/tests/python/core/test_registry.py`. |

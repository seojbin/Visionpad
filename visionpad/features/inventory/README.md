# Inventory

The F2 item pages: gold and food first, then everything else, twelve per page. Food can be used from here.

| Item | Value |
|---|---|
| Code | `feature.py` (`Inventory`) |
| Pages | `inventory` (F2 menu, spoken "Inventory. N gold."; icons on the shared grid; Left/Right turn pages) |
| Actions | `inventory_page:-1`, `inventory_page:1` (after the night guard). Food entries carry `use_food:<recipe>` (cooking, still core) |
| Owned engine attributes (save format) | `inventory_page`, `inventory_page_count` |
| Shared attributes written | `current_page` (via `set_page` in `open`), `seed_select_plot_id` (in `open`) |
| Shared attributes read | `resources`, `config`, `paused`, `day_ended`, `inventory_items_per_page`, `inventory_hide_zero_items`, `fishing_config()`, `recipe_effect_text()` |
| Read by other code | `lower_panel_state` (page bar), `perform_action` (step sound on page change) |
| Slot declared | `inventory.items` (order table `order.InventoryItems`) |
| Slot contributions | Shared resources first (gold, fertilizer, wood, stone, `InventoryItems.CORE_RESOURCES`); mining, farming, cooking, fishing and flowers contribute their own entries. |
| Events | `reset` (`Reset.INVENTORY`) |
| State key | `inventory` in `/api/state` |
| Engine methods kept for callers | `engine.open_inventory()` (tests, `tools/prepare_demo.py`), `engine.get_inventory_objects()` |
| Config | `config/game.json` → `interaction.inventory.items_per_page`, `interaction.inventory.hide_zero_items`; page name `pages.inventory` |
| Tests | No dedicated tests. `test_team_audio` uses `open_inventory`. Old-vs-new comparison script used during the split. |

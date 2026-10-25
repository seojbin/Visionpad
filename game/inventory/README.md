# Inventory

The F2 item pages: gold and food first, then everything else, twelve per page. Food can be used from here.

| Item | Value |
|---|---|
| Code | `feature.py` (`Inventory`) |
| Pages | `inventory` (F2 menu, spoken "Inventory. N gold."; icons on the shared grid; Left/Right turn pages) |
| Actions | `inventory_page:-1`, `inventory_page:1` (after the night guard). Food entries carry `use_food:<recipe>` (cooking) |
| Owned engine attributes (save format) | `inventory_page`, `inventory_page_count` |
| Shared attributes written | `current_page` (via `set_page` in `open`), `seed_select_plot_id` (in `open`) |
| Shared attributes read | `resources`, `config`, `paused`, `day_ended`, `inventory_items_per_page`, `inventory_hide_zero_items` |
| Read by other code | `lower_panel_state` (page bar), `perform_action` (step sound on page change) |
| Slot declared | `inventory.items` (order table `order.InventoryItems`) |
| Slot contributions | Shared resources first (gold, fertilizer, wood, stone, `InventoryItems.CORE_RESOURCES`); mining, farming, cooking, fishing and flowers contribute their own entries. |
| Events | `reset` (`Reset.INVENTORY`) |
| State key | `inventory` in `/api/state` |
| Engine methods kept for callers | `engine.open_inventory()` (tests, `engine/tools/prepare_demo.py`), `engine.get_inventory_objects()` |
| Config | `engine/config/game.json` → `interaction.inventory.items_per_page`, `interaction.inventory.hide_zero_items`; page name `pages.inventory` |
| Engine API used | none from other features (entries come through the `inventory.items` slot); core `_perform_action` (Left/Right paging), `leave_activities`, `set_page` |
| Client (web) | `game/inventory/client.js` (page N/M task text) |
| Tests | No dedicated tests. `engine/tests/python/audio/test_team_audio.py` uses `open_inventory`. |

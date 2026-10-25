# Minimap

The F1 map: location nodes and the paths between them, compressed to fit the pad. Selecting a node travels there.

| Item | Value |
|---|---|
| Code | `feature.py` (`Minimap`) |
| Pages | `minimap` (opened with F1 through `toggle_menu`; spoken "Map. Select a place."; Left/Right closes it) |
| Actions | none of its own; nodes carry `travel:<location>`, handled by core navigation |
| Object types | `node` (box, filled when current), `route` (line); hover speech is the label; hover sounds `hover_node`, `hover_route` |
| Owned engine attributes | none |
| Shared attributes read | `config`, `current_location`, `paused`, `sleep_until`, `day_ended` |
| Shared attributes written | `_menu_stack` (clears it when closing), `current_page` (only in the unused `open`) |
| Core helpers used | `compress_axis`, `get_relative_direction`, `draw_filled_square`, `return_to_scene` |
| Config | `config/game.json` → `minimap.locations`, `minimap.routes`; page name `pages.minimap` |
| Tests | No dedicated tests. Old-vs-new comparison script used during the split. |
| Note | `open()` was unused before the split too (docs/refactor/AUDIT.md §2.4); kept for parity. |

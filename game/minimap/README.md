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
| Engine API used | none from other features; core `compress_axis`, `get_relative_direction`, `draw_filled_square`, `point_to_segment_distance`, `return_to_scene`, `leave_activities` |
| Config | `engine/config/game.json` → `minimap.locations`, `minimap.routes`; page name `pages.minimap` |
| Events | none |
| Slots | none |
| Client (web) | none (no `game/minimap/` folder; the game page shows its pages with the shared defaults) |
| Tests | No dedicated tests. The F1 map is used by `tests/python/audio/test_sound_events.py` (menus) and `tests/python/audio/test_audio_flow.py` (travel). |
| Note | `open()` was unused before the split too (docs/refactor/AUDIT.md §2.4); kept for parity. |

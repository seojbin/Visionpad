# Minimap

The F1 map: location nodes and the paths between them, compressed to fit the pad, with Home anchored at the centre. Selecting a node travels there.

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
| Tests | `game/minimap/tests/test_layout.py` checks centring, bounds and topology. The F1 map is used by `engine/tests/python/audio/test_sound_events.py` (menus) and `engine/tests/python/audio/test_audio_flow.py` (travel). |
| Note | `open()` was unused before the split too (follow-up F14); kept for parity. |

Location frames and the filled current location use exact 7×7 bounds. Nodes clear underlying path pixels so routes never pass through the interior.

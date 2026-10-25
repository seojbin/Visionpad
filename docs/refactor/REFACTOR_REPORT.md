# Refactor report

Branch `refactor/modular-structure`. This report is completed at the end of the refactor (structure, path table, before/after results, deviations). Sections are added as phases finish.

## Behavior notes

Places where the refactored code can behave differently from the pre-refactor engine, all outside what a player can reach.

| Topic | Before | After | Reachable in play? |
|---|---|---|---|
| `perform_action("drag_tool:<tool>", obj)` called directly | `pointer_down` handled `drag_tool:` before `perform_action`; a direct `perform_action` call with that string fell through to the generic fallback (speaks the object's label). | Farming registers `drag_tool:` as a normal action, so a direct call picks up the tool (`drag_tool` set, "Watering can. Drag to a plot.") after the same night guard. Pressing an object with that action behaves exactly as before. | No. No object offers a `drag_tool:` action (since before the split), and the HTTP API only sends pointer coordinates and key commands, never action strings. |
| Unreachable code removed vs kept | Several branches could never run (see AUDIT.md §2.4). | Kept as methods for parity where they contain speech lines, so the demo speech list is unchanged (FOLLOWUPS F14). | No. |

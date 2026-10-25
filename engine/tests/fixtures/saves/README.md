# Save fixtures

`v1_day1_farm_started.json` was written by the pre-refactor engine (commit `ea38001`) after: visit village, receive and eat Rowan's soup, receive seeds, plant tomato in `plot_1`, buy carrot seeds, return home (day 1, 52 gold).

`test_save_compat.py` loads it and requires an exact `snapshot()` match. Do not regenerate it to make a failing test pass: a failure means the save format (engine attribute names, types or defaults) changed.

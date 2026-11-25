# Guide

A replayable tutorial opened from the F1 map. Topic buttons explain touch, selection, sweep tasks, keys and the screen layout; the symbol key shows every shared tactile symbol with its name, shape and meaning. Nothing here spends time, gold or items. The reasons and sources are in the root README ("Tactile design rules", "Learning support: the Guide").

| Item | Value |
|---|---|
| Code | `feature.py` (`Guide`; `TOPICS`, `SYMBOL_KEY`, `PAGE_TITLES`) |
| Pages | `guide` (six topic buttons in the icon grid; Left/Right return to the region), `guide_symbols_1` to `guide_symbols_4` (the symbol key: five themed pages of four symbols, the last one *Animals*; Left/Right turn pages, past either end returns to `guide`; the lower panel shows the page position), `guide_animal_cat`, `guide_animal_dog`, `guide_animal_chicken`, `guide_animal_sheep` (animal gallery: the same large drawing as in the game, with a spoken description; Right shows the next animal, Left goes back) |
| Actions | `guide_open`, `guide_topic:<id>` (reads the topic), `guide_symbols` (opens page 1 of the key), `guide_symbol:<symbol>` (reads shape and meaning), `guide_page:<±1>`, `guide_animal:<species>`, `guide_animal_next`, `guide_page_animals`; all run before the night guard and cost nothing |
| Object types | `guide_button` (page symbol, on the map), `guide_topic` (empty frame; the symbol-key topic shows a check), `guide_symbol` (the symbol from `engine/display/icons.py` `SYMBOLS`; food shows the double frame; `animal_*` entries show the pet or pasture icon), `guide_animal` (the large drawing's hit area); hover speech is the object's `tts`; hover sound `hover_resource` |
| Owned engine attributes | none (the key page number is part of the page id) |
| Shared attributes written/read | writes `current_page`, `_menu_stack` (cleared on open), hover via `clear_hover`; reads `sleep_until`, `current_location` |
| Events | none |
| Slots | contributes `minimap.objects` (the Guide button at the map's top left) |
| State keys | none |
| Saves | nothing added; a save made on a guide page reopens that page (`current_page`) |
| Engine API provided/used | provides none; reads `game.pets.patterns` and `game.pasture.feature` drawing tables for the gallery; uses core `back_arrow`, `return_to_scene`, `release_pointer`, `leave_activities`, `clear_hover`, `render`, `response` |
| Config | none |
| Client (web) | `client.js`: task texts for `guide` and the four `guide_symbols_N` pages (script tag in `engine/web/game.html`) |
| Tests | `game/guide/tests/test_guide.py`; the pages are also audited by `engine/tests/python/display/test_tactile_rules.py` |

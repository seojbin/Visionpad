# Research

Upgrades bought from the research chest at home: seed recovery, farm expansion and mineral discovery.

| Item | Value |
|---|---|
| Code | `feature.py` (`Research`) |
| Pages | `research` (spoken name from `engine/config/game.json` `pages.research`; icons on the shared grid) |
| Actions | `open_research`, `research:seed_return`, `research:field_expand`, `research:mineral_luck`, `research:animal_shelter` (after the night guard) |
| Object types | `research` (icon; hover speech lists the cost fields; hover sound `hover_research`) |
| Owned engine attributes (save format) | `research_levels`, `unlocked_plot_count` |
| Shared attributes written | `pasture_goods.wool` (shelter cost);  `resources` coin, copper, stone, iron (via `add_resource`), `current_page` (via `set_page`); spends time with `consume_time("research")` |
| Shared attributes read | `config`, `day_ended`, `resources`, `MINERAL_LABELS` |
| Read by other code | farming (`unlocked_plot_count` → `get_unlocked_plot_defs`, seed recovery chance), mining (`research_levels["mineral_luck"]`), seed selection text |
| Events | `reset` (`Reset.RESEARCH`) |
| State keys | `research_levels`, `unlocked_plot_count` in `/api/state` |
| Config | `engine/config/game.json` → `research.seed_return`, `research.field_expansion`, `research.mineral_luck`, `research.animal_shelter`; `time.action_costs.research` |
| Slots | none |
| Engine API used | none from other features; core `add_resource`, `set_page`, `consume_time`, `night_response`, `night_only_response` |
| Client (web) | none (no `game/research/` folder; the game page shows its pages with the shared defaults) |
| Tests | `game/research/tests/test_shelter.py`; `engine/tests/python/saves/test_save_compat.py`. |

## Animal shelter

Two levels cost 150 gold + 2 wool, then 250 gold + 4 wool. Short hover lists the name and next-level gold/wool cost, just like other research. Detailed inspection states the next level, required gold/wool and “Increased yield”; at the cap it reports level 2 and maximum level. Structured cost fields show the required and owned resources. Research-discount food applies to gold only, and is consumed only on success.

On collecting eggs or wool, each original product rolls once: 15% at level 1 and 30% at level 2. Each successful roll adds one of that product, without recursive bonus rolls. A nest's capacity remains three before collection; research bonuses can make the collected total larger. No detailed probabilities are spoken. The level is stored in the existing `research_levels` dictionary; absent old-save values mean level zero.

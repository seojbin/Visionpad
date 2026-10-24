# Research

Upgrades bought from the research chest at home: seed recovery, farm expansion and mineral discovery.

| Item | Value |
|---|---|
| Code | `feature.py` (`Research`) |
| Pages | `research` (spoken name from `config/game.json` `pages.research`; icons on the shared grid) |
| Actions | `open_research`, `research:seed_return`, `research:field_expand`, `research:mineral_luck` (after the night guard) |
| Object types | `research` (icon; hover speech lists the cost fields; hover sound `hover_research`) |
| Owned engine attributes (save format) | `research_levels`, `unlocked_plot_count` |
| Shared attributes written | `resources` coin, copper, stone, iron (via `add_resource`), `current_page` (via `set_page`); spends time with `consume_time("research")` |
| Shared attributes read | `config`, `day_ended`, `resources`, `MINERAL_LABELS` |
| Read by other code | farming (`unlocked_plot_count` → `get_unlocked_plot_defs`, seed recovery chance), mining (`research_levels["mineral_luck"]`), seed selection text |
| Events | `reset` (`Reset.RESEARCH`) |
| State keys | `research_levels`, `unlocked_plot_count` in `/api/state` |
| Config | `config/game.json` → `research.seed_return`, `research.field_expansion`, `research.mineral_luck`; `time.action_costs.research` |
| Tests | No dedicated tests. Old-vs-new comparison script used during the split (see REFACTOR_REPORT.md). |

# Egg cooking

Fried egg uses one egg and one carrot. Select both ingredients in the kitchen to start. Trace the bouncing egg-cracking path, then the existing eight-petal frying path. Ingredients are consumed only when both steps finish. Eat the dish from inventory to reduce the gold cost of the next successful research by 20%. Material requirements do not change. Failed research does not consume the effect, and the effect does not expire with activity time. Eating another dish replaces it under the existing single-food-effect rule.

| Area | Implementation |
|---|---|
| Code | `game/cook/ingredients.py`; existing `game/cooking/feature.py` runs both stages |
| Pages | Existing recipe_select, ingredient_select, cooking |
| Actions | Existing recipe selection, ingredient selection and food use |
| Object types | Existing recipe, ingredient and food types |
| Owned engine attributes | none |
| Shared attributes written/read | Reads pasture_goods for eggs; cooking completion consumes eggs and carrots and adds fried_egg to foods |
| Events | none |
| Slots | none; existing cooking slots provide the dish |
| State keys | Existing cooking state, including gesture_kind=crack |
| Saves | Existing food inventory and active_buff save paths |
| Engine API provided/used | No new exposed API; existing cooking and research methods |
| Config | `engine/config/game.json` → recipes.fried_egg; interaction.audio.work_gain.crack and work_gain_during_tts.crack |
| Client (web) | `game/cook/audio/crack.mp3`; GameAudio maps crack to the work channel, preserving reward and spatial audio. |
| Tests | `game/cook/tests/test_egg.py`, `game/pasture/tests/test_animal_audio.cjs` |

The shared `pasture-items.png` sprite sheet includes fried egg, steamed egg and fish egg pancake. Only fried egg is a playable recipe; the other two images are reserved for later recipes. Existing cooking code remains in `game/cooking/` to preserve feature registration and saved-game compatibility.

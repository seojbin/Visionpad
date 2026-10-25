# NPC

Rowan's voice and memory: farming/fishing advice from the actual game state, one-time reactions to the latest real result, and the activity log behind them. Talking itself runs the village quest.

| Item | Value |
|---|---|
| Code | `feature.py` (`Npc`); lines in `engine/config/npc.json` |
| Pages | `npc_dialogue` ("Conversation"; unreachable since before the split: nothing sets it) |
| Actions (before the night guard) | `npc:<npc_id>:<topic>` → `npc_action`, which ignores the topic and calls `talk_rowan()` (FOLLOWUPS F1) |
| Object types | `npc_topic`, `npc_marker` (renderers) |
| Owned engine attributes (save format) | `npc_visits`, `dialogue`, `activity_counts`, `activity_serial`, `recent_activity`, `npc_reactions`, `activity_history_complete` |
| Shared attributes read | `day`, `current_location`, `current_page`, `sleep_until`, `day_ended`, `paused`, `resources`, `farm_plots`, `rowan_dialogue` |
| Events | `reset` (`Reset.NPC`); `activity(kind, item, count)` from harvest, cooking, mining, fishing, seafood and tool breaks |
| State key | `dialogue` |
| Saves | Defaults from a fresh engine for six attributes; `activity_history_complete` defaults to False for older saves; a save made on `npc_dialogue` reopens in town |
| Engine API provided | `npc_action`, `record_activity`, `recent_reaction`, `rowan_advice`, `next_rowan_advice`, `npc_voice_profile` |
| Engine API used | `talk_rowan` (village), `draw_shop_npc` (shop, core) |
| Config | `engine/config/npc.json` → `shopkeeper.*` |
| Slots | none |
| Client (web) | `game/npc/client.js` (task text for the unreachable `npc_dialogue` page); texture `game/npc/assets/rowan.png` (Rowan, portrait, equipped rod) |
| Tests | `tests/python/audio/test_gameplay_audio.py`, `tests/python/speech/test_speech.py`, `tests/python/speech/test_demo_speech.py` |

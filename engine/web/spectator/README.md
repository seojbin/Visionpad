# engine/web/spectator — companion window

The read-only companion window. It follows the game state from `/api/state` and draws the
scene; clicking it never changes the game.

> **`display.js`: do not regenerate until drift is resolved.**
> `display.js` is a classic-script bundle built by `engine/tools/build_display.py` from `model.mjs` and
> `viewer.js`, but it has drifted from those sources in both directions (FOLLOWUPS F5).
> Running `python engine/tools/build_display.py` now would drop hand edits that exist only in the bundle.
> Reconcile the bundle and its sources by hand first, then make the build reproducible.

| File | Role |
|---|---|
| `display.js` | Bundle loaded by the game page (`/static/spectator/display.js`); see the warning above |
| `model.mjs`, `viewer.js`, `boot.js` | Module sources of the renderer (`standalone.html`, `demo.html`) |
| `viewer.css` | Companion styles |
| `visual-assets.json` | Texture sheets and crop rectangles; texture paths are relative to this folder |
| `scene-objects.json` | Scene placement of objects and characters |
| `fixtures.json` | Sample states for `demo.html` |
| `assets/` | Shared texture sheets (scenes, items, facilities) |

Feature-only sheets live next to their feature and are referenced from `visual-assets.json`
with `../features/<name>/assets/...`: flower sheets in `game/flowers/assets/`, fish and
fish dishes (`items2.png`) in `game/fishing/assets/`, and the Rowan atlas (`rowan.png`)
in `game/npc/assets/`. Their old `/static/spectator/assets/...` URLs still resolve
(`LEGACY_STATIC` in `engine/server/routes/static.py`).

# engine/web/spectator — companion window

The read-only companion window. It follows the game state from `/api/state` and draws the
scene; clicking it never changes the game.

> **`display.js`: do not regenerate until drift is resolved.**
> `display.js` is a classic-script bundle built by `engine/tools/build_display.py` from `model.mjs` and
> `viewer.js`, but it has drifted from those sources in both directions (follow-up F5).
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

All image sheets live in `engine/web/spectator/assets/`, including fish, fish dishes,
Rowan and flower sheets. `visual-assets.json` references their `assets/` paths.
Old `/static/features/<name>/assets/...` URLs remain available through
`LEGACY_STATIC` in `engine/server/routes/static.py` for cached clients.

The game page retains the frozen `display.js` relay. The detached window loads
`viewer.js` directly as a module, using the same BroadcastChannel snapshots.
No regeneration of `display.js` is needed. Home anchors both minimaps at their
screen centre; village artwork places Rowan to the left and the shop to the right,
matching the lower tactile scene. Artwork dimensions are unchanged.

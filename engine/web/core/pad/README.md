# Dot Pad connection

Self-contained: everything that talks to a physical Dot Pad lives in this folder.

| File | Role |
|---|---|
| `hardware.mjs` | USB pad over Web Serial (`SerialPad`), the Bluetooth button wiring, and the hand-tracking WebSocket client. Loaded by `engine/web/game.html` as a module. |
| `bluetooth-pad.mjs` | Bluetooth pad through Dot Inc.'s DotPadSDK (`BluetoothPad`), imported on demand by `hardware.mjs`. |
| `vendor/` | Put `DotPadSDK-3.0.3.js` and `DotPadSDK-3.0.3.d.ts` here (downloaded by hand, gitignored). `package.json` marks the folder as ES modules. Without the SDK the Bluetooth button reports that it is unavailable; USB and hand tracking still work. |

The page talks to this folder only through `window.DotdewInput` (key and pointer input) and the `dotdew-state` event (frames to draw). The old URLs `/static/hardware.mjs`, `/static/bluetooth-pad.mjs` and `/static/vendor/…` still resolve (`engine/server/routes/static.py`).

Tests: `engine/tests/js/pad/`. Both files cannot load their modules yet and report one known failure each (follow-ups F3, F4).

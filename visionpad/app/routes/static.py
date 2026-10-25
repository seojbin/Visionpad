import mimetypes

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from visionpad.paths import WEB_DIR


# The pad module must arrive as JavaScript. Windows machines whose registry maps .mjs to
# text/plain would otherwise make the browser refuse it (FOLLOWUPS F17).
mimetypes.add_type("text/javascript", ".mjs")

router = APIRouter()

# Files moved during the modular refactor keep answering at their old /static/ URLs, so open
# pages, bookmarks and cached companion windows keep working. Keys ending in "/" map a folder.
LEGACY_STATIC = {
    "game-audio.js": "core/game-audio.js",
    "game-speech.js": "core/game-speech.js",
    "game-keys.js": "core/game-keys.js",
    "hardware.mjs": "core/pad/hardware.mjs",
    "bluetooth-pad.mjs": "core/pad/bluetooth-pad.mjs",
    "vendor/": "core/pad/vendor/",
    "audio/water.mp3": "features/farming/audio/water.mp3",
    "audio/soil.mp3": "features/farming/audio/soil.mp3",
    "audio/crop.mp3": "features/harvest/audio/crop.mp3",
    "audio/cut.mp3": "features/cooking/audio/cut.mp3",
    "audio/cook.mp3": "features/cooking/audio/cook.mp3",
    "audio/pickaxe.mp3": "features/mining/audio/pickaxe.mp3",
    "audio/break.mp3": "features/mining/audio/break.mp3",
    "audio/splash.mp3": "features/fishing/audio/splash.mp3",
    "spectator/assets/items2.png": "features/fishing/assets/items2.png",
    "spectator/assets/rowan.png": "features/npc/assets/rowan.png",
    "spectator/assets/flower-items.png": "features/flowers/assets/flower-items.png",
    "spectator/assets/flower-stages.png": "features/flowers/assets/flower-stages.png",
    "spectator/assets/flower-backgrounds.png": "features/flowers/assets/flower-backgrounds.png",
}


class WebFiles(StaticFiles):
    """Static files from web/, with the pre-refactor locations as fallbacks."""

    def lookup_path(self, path):
        full_path, stat_result = super().lookup_path(path)
        if stat_result is None:
            moved = legacy_path(path.replace("\\", "/"))
            if moved:
                return super().lookup_path(moved)
        return full_path, stat_result


def legacy_path(path):
    if path in LEGACY_STATIC:
        return LEGACY_STATIC[path]
    for old, new in LEGACY_STATIC.items():
        if old.endswith("/") and path.startswith(old):
            return new + path[len(old):]
    return None


def mount(app):
    app.mount(
        "/static",
        WebFiles(directory=str(WEB_DIR)),
        name="static"
    )


@router.get("/")
async def root():
    return FileResponse(str(WEB_DIR / "game.html"))

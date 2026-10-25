import mimetypes
import posixpath

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from engine.paths import GAME_DIR, WEB_DIR


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
    """Static files from engine/web/ and game/<name>/, with the pre-refactor locations as fallbacks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game = StaticFiles(directory=str(GAME_DIR))

    def lookup_path(self, path):
        path = path.replace("\\", "/")
        full_path, stat_result = self.find(path)
        if stat_result is None:
            moved = legacy_path(path)
            if moved:
                return self.find(moved)
        return full_path, stat_result

    def find(self, path):
        feature_path = game_path(path)
        return self.game.lookup_path(feature_path) if feature_path else super().lookup_path(path)


def game_path(path):
    """features/<name>/<file> -> <name>/<file> in game/. Only a feature's client.js, audio/ and assets/
    are public; its Python code and tests are not served."""
    parts = posixpath.normpath(path).split("/", 2)
    if len(parts) == 3 and parts[0] == "features" and (parts[2] == "client.js" or parts[2].startswith(("audio/", "assets/"))):
        return f"{parts[1]}/{parts[2]}"
    return None


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

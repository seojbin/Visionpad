from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from visionpad.paths import WEB_DIR


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

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from visionpad.paths import WEB_DIR


router = APIRouter()


def mount(app):
    app.mount(
        "/static",
        StaticFiles(directory=str(WEB_DIR)),
        name="static"
    )


@router.get("/")
async def root():
    return FileResponse(str(WEB_DIR / "game.html"))

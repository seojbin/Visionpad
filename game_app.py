from pathlib import Path
import json

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from game_engine import GameEngine


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "game_config.json"
WEB_DIR = BASE_DIR / "web"


with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


engine = GameEngine(CONFIG)
app = FastAPI(title="Dotdu Valley")

app.mount(
    "/static",
    StaticFiles(directory=str(WEB_DIR)),
    name="static"
)


class PointerRequest(BaseModel):
    x: float
    y: float


class CommandRequest(BaseModel):
    command: str


@app.get("/")
async def root():
    return FileResponse(str(WEB_DIR / "game.html"))


@app.get("/api/state")
async def get_state():
    return engine.get_state()


@app.post("/api/pointer/move")
async def pointer_move(req: PointerRequest):
    return engine.pointer_move(req.x, req.y)


@app.post("/api/pointer/down")
async def pointer_down(req: PointerRequest):
    return engine.pointer_down(req.x, req.y)


@app.post("/api/pointer/drag")
async def pointer_drag(req: PointerRequest):
    return engine.pointer_drag(req.x, req.y)


@app.post("/api/pointer/up")
async def pointer_up(req: PointerRequest):
    return engine.pointer_up(req.x, req.y)


@app.post("/api/command")
async def command(req: CommandRequest):
    return engine.handle_command(req.command)


@app.post("/api/reset")
async def reset():
    engine.reset()
    return {
        "tts": "게임을 초기화했습니다. 집입니다",
        "state": engine.get_state()
    }

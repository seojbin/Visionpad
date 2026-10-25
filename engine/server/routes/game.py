from fastapi import APIRouter
from pydantic import BaseModel, Field

from engine.server import runtime


router = APIRouter()


class PointerRequest(BaseModel):
    x: float = Field(ge=0, lt=runtime.CONFIG["dotpad"]["width"], allow_inf_nan=False)
    y: float = Field(ge=0, lt=runtime.CONFIG["dotpad"]["height"], allow_inf_nan=False)


class CommandRequest(BaseModel):
    command: str


@router.get("/api/state")
async def get_state():
    return runtime.engine.get_state()


@router.post("/api/pointer/move")
async def pointer_move(req: PointerRequest):
    return runtime.engine.pointer_move(req.x, req.y)


@router.post("/api/pointer/down")
async def pointer_down(req: PointerRequest):
    return runtime.engine.pointer_down(req.x, req.y)


@router.post("/api/pointer/drag")
async def pointer_drag(req: PointerRequest):
    return runtime.engine.pointer_drag(req.x, req.y)


@router.post("/api/pointer/up")
async def pointer_up(req: PointerRequest):
    return runtime.engine.pointer_up(req.x, req.y)


@router.post("/api/command")
async def command(req: CommandRequest):
    return runtime.engine.handle_command(req.command)


@router.post("/api/reset")
async def reset():
    runtime.engine.reset()
    return {
        "tts": "New game. Home.",
        "state": runtime.engine.get_state()
    }


@router.post("/api/visual-tick")
async def visual_tick():
    return runtime.engine.visual_tick()

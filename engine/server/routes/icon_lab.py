"""Icon lab for user testing: the pattern catalog and frames composed with the game's own drawing code.

GET /icon-lab serves the page; it never touches the running game's state.
"""
import pkgutil
import re
from importlib import import_module
from types import SimpleNamespace
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

import game
from engine.config import load_config
from engine.core.render import Rendering
from engine.display.dotpad import DotPad
from engine.display.icons import IconGrid, IconRenderer
from engine.paths import WEB_DIR


router = APIRouter()

WIDTH, HEIGHT, TIME_WIDTH, TIME_HEIGHT = 60, 40, 40, 4
ROW = re.compile(r"[01]+")


def is_rows(value):
    return (isinstance(value, (tuple, list)) and 0 < len(value) <= HEIGHT
            and all(isinstance(row, str) and ROW.fullmatch(row) and len(row) <= WIDTH for row in value))


def module_patterns(module):
    """Module-level dicts whose name ends in PATTERNS: name -> rows, or name -> {sub: rows}."""
    for attr, value in vars(module).items():
        # Aliases of the shared table (village's PATTERNS) are listed once, as shared icons.
        if not attr.endswith("PATTERNS") or not isinstance(value, dict) or value is IconRenderer.PATTERNS:
            continue
        for key, rows in value.items():
            if is_rows(rows):
                yield attr, str(key), list(rows)
            elif isinstance(rows, dict):
                for sub, inner in rows.items():
                    if is_rows(inner):
                        yield attr, f"{key}/{sub}", list(inner)


def catalog():
    entries = [{"group": "shared icons", "source": "engine/display/icons.py", "name": name, "rows": list(rows)}
               for name, rows in IconRenderer.PATTERNS.items()]
    for info in pkgutil.walk_packages(game.__path__, game.__name__ + "."):
        if ".tests" in info.name:
            continue
        module = import_module(info.name)
        feature = info.name.split(".")[1]
        for attr, name, rows in module_patterns(module):
            entries.append({"group": f"{feature} · {attr}", "source": info.name.replace(".", "/") + ".py",
                            "name": name, "rows": rows})
    config = load_config("game")
    for section, items in config.items():
        if not isinstance(items, dict):
            continue
        for key, item in items.items():
            if isinstance(item, dict) and is_rows(item.get("icon")):
                entries.append({"group": f"game.json · {section}", "source": "engine/config/game.json",
                                "name": key, "rows": list(item["icon"])})
    return entries


class Item(BaseModel):
    name: str = ""
    rows: list[str]

    @field_validator("rows")
    @classmethod
    def check_rows(cls, rows):
        if not is_rows(rows):
            raise ValueError(f"rows must be 1-{HEIGHT} strings of 0/1, at most {WIDTH} long")
        return rows


class RenderRequest(BaseModel):
    layout: Literal["grid", "single"] = "single"
    frame: bool = True
    items: list[Item] = Field(default_factory=list, max_length=12)


def compose(req):
    """Draw like IconRenderer: a 12x10 slot frame plus the pattern centred in it."""
    pad = DotPad(WIDTH, HEIGHT)
    host = SimpleNamespace(dotpad=pad)
    icons = IconRenderer(host)
    if req.layout == "grid":
        objects = IconGrid().place([{"id": str(i)} for i in range(len(req.items))], WIDTH, HEIGHT)
    else:
        objects = [{"x": WIDTH // 2, "y": HEIGHT // 2,
                    "width": max(12, len(max(item.rows, key=len)) + 4),
                    "height": max(10, len(item.rows) + 4)} for item in req.items[:1]]
    for obj, item in zip(objects, req.items):
        if req.frame:
            icons.frame(obj)
        Rendering.draw_icon_pattern(host, obj["x"], obj["y"], item.rows)
    return {
        "dots": pad.to_list(), "width": WIDTH, "height": HEIGHT,
        "time_dots": DotPad(TIME_WIDTH, TIME_HEIGHT).to_list(), "time_width": TIME_WIDTH, "time_height": TIME_HEIGHT,
        "slots": [{"x": o["x"], "y": o["y"], "name": item.name} for o, item in zip(objects, req.items)],
    }


@router.get("/icon-lab")
async def icon_lab_page():
    return FileResponse(str(WEB_DIR / "icon-lab.html"))


@router.get("/api/icon-lab/patterns")
async def icon_lab_patterns():
    return catalog()


@router.post("/api/icon-lab/render")
async def icon_lab_render(req: RenderRequest):
    return compose(req)

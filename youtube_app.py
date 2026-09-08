from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import asyncio
import base64
import json
import os
import re

import cv2
import numpy as np
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from youtube_processor import YouTubeProcessor


BASE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = (
    BASE_DIR
    / "youtube_config.json"
)

WEB_DIR = (
    BASE_DIR
    / "web"
)


def load_config():
    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


CONFIG = load_config()

scene_lock = asyncio.Lock()
ocr_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(
    app: FastAPI
):
    print(
        "YouTube processor loading"
    )

    app.state.processor = (
        YouTubeProcessor(
            CONFIG["processor"]
        )
    )

    print(
        "YouTube processor ready"
    )

    yield


app = FastAPI(
    title="VideoBraille YouTube Viewer",
    lifespan=lifespan
)


if WEB_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(
            directory=str(
                WEB_DIR
            )
        ),
        name="static"
    )


class FrameRequest(BaseModel):
    image_base64: str

    timestamp: float = Field(
        ge=0
    )


class YouTubeResolveRequest(
    BaseModel
):
    query: str

    max_results: int | None = Field(
        default=None,
        ge=1,
        le=10
    )


def decode_base64_image(
    value
):
    payload = value.strip()

    if payload.startswith(
        "data:"
    ):
        payload = payload.split(
            ",",
            1
        )[1]

    image_bytes = base64.b64decode(
        payload
    )

    array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    frame = cv2.imdecode(
        array,
        cv2.IMREAD_COLOR
    )

    if frame is None:
        raise ValueError(
            "이미지를 디코딩할 수 없습니다."
        )

    return frame


def extract_youtube_video_id(
    value
):
    text = value.strip()

    if re.fullmatch(
        r"[A-Za-z0-9_-]{11}",
        text
    ):
        return text

    lower = text.lower()

    if (
        lower.startswith(
            "www.youtube.com"
        )
        or lower.startswith(
            "youtube.com"
        )
        or lower.startswith(
            "m.youtube.com"
        )
        or lower.startswith(
            "youtu.be"
        )
    ):
        text = (
            "https://"
            + text
        )

    try:
        parsed = urlparse(
            text
        )
    except Exception:
        return None

    host = (
        parsed.hostname
        or ""
    ).lower()

    if host.endswith(
        "youtu.be"
    ):
        video_id = (
            parsed.path
            .strip("/")
            .split("/")[0]
        )

        if re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id
        ):
            return video_id

    valid_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com"
    }

    if host not in valid_hosts:
        return None

    query = parse_qs(
        parsed.query
    )

    video_id = (
        query.get(
            "v",
            [None]
        )[0]
    )

    if (
        video_id
        and re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id
        )
    ):
        return video_id

    parts = [
        part
        for part
        in parsed.path.split("/")
        if part
    ]

    if (
        len(parts) >= 2
        and parts[0]
        in {
            "shorts",
            "embed",
            "live"
        }
    ):
        video_id = parts[1]

        if re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id
        ):
            return video_id

    return None


def looks_like_youtube_url(
    value
):
    lower = value.lower()

    return (
        "youtube.com" in lower
        or "youtu.be" in lower
        or "youtube-nocookie.com" in lower
    )


def search_youtube(
    query,
    max_results
):
    api_key = os.getenv(
        "YOUTUBE_API_KEY"
    )

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "텍스트 검색에는 "
                "YOUTUBE_API_KEY가 필요합니다."
            )
        )

    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part":
                    "snippet",

                "q":
                    query,

                "type":
                    "video",

                "videoEmbeddable":
                    "true",

                "maxResults":
                    max_results,

                "key":
                    api_key
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=str(e)
        ) from e

    results = []

    for item in data.get(
        "items",
        []
    ):
        video_id = (
            item.get(
                "id",
                {}
            ).get(
                "videoId"
            )
        )

        if not video_id:
            continue

        snippet = item.get(
            "snippet",
            {}
        )

        thumbnails = snippet.get(
            "thumbnails",
            {}
        )

        thumbnail = (
            thumbnails
            .get(
                "medium",
                {}
            )
            .get(
                "url"
            )
        )

        results.append(
            {
                "video_id":
                    video_id,

                "title":
                    snippet.get(
                        "title",
                        ""
                    ),

                "channel_title":
                    snippet.get(
                        "channelTitle",
                        ""
                    ),

                "thumbnail":
                    thumbnail
            }
        )

    return results


@app.get("/")
async def root():
    return FileResponse(
        str(
            WEB_DIR
            / "youtube.html"
        )
    )


@app.get(
    "/api/config"
)
async def client_config():
    capture = CONFIG[
        "capture"
    ]

    return capture


@app.get(
    "/api/health"
)
async def health(
    request: Request
):
    return {
        "status": "ok",
        "processor":
            request.app.state
            .processor.status()
    }


@app.post(
    "/api/reset"
)
async def reset(
    request: Request
):
    request.app.state.processor.reset()

    return {
        "status": "ok"
    }


@app.post(
    "/api/scene-frame"
)
async def scene_frame(
    req: FrameRequest,
    request: Request
):
    try:
        frame = decode_base64_image(
            req.image_base64
        )

        async with scene_lock:
            return await asyncio.to_thread(
                request.app.state
                .processor
                .process_scene_frame,

                frame,
                req.timestamp
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e


@app.post(
    "/api/ocr-frame"
)
async def ocr_frame(
    req: FrameRequest,
    request: Request
):
    try:
        frame = decode_base64_image(
            req.image_base64
        )

        async with ocr_lock:
            return await asyncio.to_thread(
                request.app.state
                .processor
                .process_ocr_frame,

                frame,
                req.timestamp
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e


@app.post(
    "/api/youtube/resolve"
)
async def resolve_youtube(
    req: YouTubeResolveRequest
):
    value = req.query.strip()

    if not value:
        raise HTTPException(
            status_code=400,
            detail=(
                "검색어나 YouTube 주소를 입력하세요."
            )
        )

    video_id = extract_youtube_video_id(
        value
    )

    if video_id:
        return {
            "mode": "url",
            "results": [
                {
                    "video_id":
                        video_id
                }
            ]
        }

    if looks_like_youtube_url(
        value
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "YouTube 주소에서 "
                "video ID를 찾지 못했습니다."
            )
        )

    max_results = (
        req.max_results
        or CONFIG[
            "youtube"
        ][
            "max_results"
        ]
    )

    return {
        "mode":
            "search",

        "results":
            search_youtube(
                value,
                max_results
            )
    }
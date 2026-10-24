import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from visionpad.app import runtime
from visionpad.services.speech import SpeechUnavailable
from visionpad.services.speech_queue import SpeechQueueFull, SpeechSuperseded


router = APIRouter()


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1600)
    profile: str = Field(default="system", pattern="^(system|shopkeeper)$")
    rate: float = Field(default=1.0, ge=0.8, le=1.5, allow_inf_nan=False)
    priority: str = Field(default="action", pattern="^(hover|action|dialogue|background)$")
    client_id: str | None = Field(default=None, pattern="^[A-Za-z0-9-]{1,80}$")
    sequence: int = Field(default=0, ge=0, le=9007199254740991)


class SpeechCancelRequest(BaseModel):
    client_id: str = Field(pattern="^[A-Za-z0-9-]{1,80}$")
    sequence: int = Field(ge=1, le=9007199254740991)


@router.get("/api/speech/voices")
def speech_voices():
    return runtime.speech.catalogue()


@router.post("/api/speech")
async def synthesize_speech(req: SpeechRequest, request: Request):
    speech_jobs = runtime.speech_jobs
    if bool(req.client_id) != bool(req.sequence):
        raise HTTPException(status_code=422, detail="client_id and positive sequence must be provided together")
    job = None
    try:
        job = speech_jobs.submit(req.text, req.profile, req.rate, req.priority, req.client_id, req.sequence)
        while not job.future.done():
            done, _ = await asyncio.wait({job.future}, timeout=0.1)
            if not done and await request.is_disconnected():
                speech_jobs.cancel(job)
                return Response(status_code=204)
        return job.future.result()
    except SpeechSuperseded:
        return Response(status_code=204)
    except SpeechQueueFull as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except asyncio.CancelledError:
        if job:
            speech_jobs.cancel(job)
        raise
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SpeechUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/api/speech/cancel", status_code=204)
async def cancel_speech(req: SpeechCancelRequest):
    runtime.speech_jobs.supersede(req.client_id, req.sequence)
    return Response(status_code=204)


@router.get("/api/speech/audio/{key}.wav")
def speech_audio(key: str):
    try:
        path = runtime.speech.audio_path(key)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Speech audio not found") from error
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Speech audio not found")
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "public, max-age=31536000, immutable"})

"""FastAPI app factory. Run with `uvicorn engine.server.main:app`."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from engine.server import runtime
from engine.server.routes import game, speech, static


def create_app():
    @asynccontextmanager
    async def lifespan(app):
        yield
        await runtime.speech_jobs.close()

    app = FastAPI(title="Dotdew Valley", lifespan=lifespan)
    # Same registration order as the original single-module app.
    static.mount(app)
    app.include_router(speech.router)
    app.include_router(static.router)
    app.include_router(game.router)
    return app


app = create_app()

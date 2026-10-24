"""Deprecated location. The server moved to visionpad.app; run `uvicorn visionpad.app.main:app`.

`uvicorn game_app:app` keeps working. The game objects live in visionpad.app.runtime;
assign there (not here) to replace them.
"""
from visionpad.app.main import app, create_app  # noqa: F401
from visionpad.app.runtime import CONFIG, engine, speech, speech_jobs  # noqa: F401
from visionpad.app.routes.game import *  # noqa: F401,F403
from visionpad.app.routes.speech import *  # noqa: F401,F403

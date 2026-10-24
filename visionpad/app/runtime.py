"""Process-wide game objects shared by the route modules (one game per server)."""
from visionpad.config import load_config
from visionpad.core.engine import GameEngine
from visionpad.paths import ROOT
from visionpad.services.speech import SpeechService
from visionpad.services.speech_queue import SpeechQueue


CONFIG = load_config("game")

engine = GameEngine(CONFIG)
speech = SpeechService(ROOT)
speech_jobs = SpeechQueue(speech)

"""Process-wide game objects shared by the route modules (one game per server)."""
from engine.config import load_config
from engine.core.engine import GameEngine
from engine.paths import ROOT
from engine.services.speech import SpeechService
from engine.services.speech_queue import SpeechQueue


CONFIG = load_config("game")

engine = GameEngine(CONFIG)
speech = SpeechService(ROOT)
speech_jobs = SpeechQueue(speech)

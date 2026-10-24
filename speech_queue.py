"""Deprecated location. Moved to visionpad.services.speech_queue; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.services.speech_queue

sys.modules[__name__] = visionpad.services.speech_queue

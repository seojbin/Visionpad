"""Deprecated location. Moved to visionpad.services.speech; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.services.speech

sys.modules[__name__] = visionpad.services.speech

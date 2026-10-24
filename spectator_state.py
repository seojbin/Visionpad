"""Deprecated location. Moved to visionpad.spectator.state; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.spectator.state

sys.modules[__name__] = visionpad.spectator.state

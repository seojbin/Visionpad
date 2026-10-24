"""Deprecated location. Moved to visionpad.display.dotpad; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.display.dotpad

sys.modules[__name__] = visionpad.display.dotpad

"""Deprecated location. Moved to visionpad.display.keypad; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.display.keypad

sys.modules[__name__] = visionpad.display.keypad

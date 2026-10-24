"""Deprecated location. Moved to visionpad.display.icons; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.display.icons

sys.modules[__name__] = visionpad.display.icons

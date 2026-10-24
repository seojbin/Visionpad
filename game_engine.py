"""Deprecated location. Moved to visionpad.core.engine; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.core.engine

sys.modules[__name__] = visionpad.core.engine

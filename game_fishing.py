"""Deprecated location. Moved to visionpad.features.fishing.mixin; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.fishing.mixin

sys.modules[__name__] = visionpad.features.fishing.mixin

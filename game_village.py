"""Deprecated location. Moved to visionpad.features.village.mixin; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.village.mixin

sys.modules[__name__] = visionpad.features.village.mixin

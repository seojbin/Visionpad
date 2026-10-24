"""Deprecated location. Moved to visionpad.features.flowers.mixin; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.flowers.mixin

sys.modules[__name__] = visionpad.features.flowers.mixin

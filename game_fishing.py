"""Deprecated location. Moved to visionpad.features.fishing.feature; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.fishing.feature

sys.modules[__name__] = visionpad.features.fishing.feature

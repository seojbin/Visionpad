"""Deprecated location. Moved to visionpad.features.village.feature; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.village.feature

sys.modules[__name__] = visionpad.features.village.feature

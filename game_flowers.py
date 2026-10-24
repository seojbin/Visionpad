"""Deprecated location. Moved to visionpad.features.flowers.feature; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.flowers.feature

sys.modules[__name__] = visionpad.features.flowers.feature

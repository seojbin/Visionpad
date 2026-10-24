"""Deprecated location. Moved to visionpad.features.seafood.feature; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.seafood.feature

sys.modules[__name__] = visionpad.features.seafood.feature

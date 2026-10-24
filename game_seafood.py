"""Deprecated location. Moved to visionpad.features.seafood.mixin; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.seafood.mixin

sys.modules[__name__] = visionpad.features.seafood.mixin

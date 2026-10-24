"""Deprecated location. Moved to visionpad.features.npc.mixin; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.npc.mixin

sys.modules[__name__] = visionpad.features.npc.mixin

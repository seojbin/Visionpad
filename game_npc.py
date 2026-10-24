"""Deprecated location. Moved to visionpad.features.npc.feature; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.features.npc.feature

sys.modules[__name__] = visionpad.features.npc.feature

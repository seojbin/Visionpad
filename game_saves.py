"""Deprecated location. Moved to visionpad.services.saves; this alias keeps old imports, launchers and docs working."""
import sys

import visionpad.services.saves

sys.modules[__name__] = visionpad.services.saves

"""Game features. Each subpackage owns one activity and exports `Feature`.

To add a feature, create game/<name>/ with a `Feature` class
(see engine/core/registry.py) and add its name below. Registration follows
this order; hooks that share an `order` value run in this order too.
"""
from importlib import import_module

ENABLED = (
    "pasture",
    "flowers",
    "research",
    "minimap",
    "inventory",
    "npc",
    "village",
    "mining",
    "fishing",
    "seafood",
    "shop",
    "cooking",
    "harvest",
    "farming",
    "home",
)


def load_features():
    return [import_module(f"{__name__}.{name}").Feature for name in ENABLED]

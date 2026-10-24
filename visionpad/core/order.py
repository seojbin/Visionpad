"""Named run order for registry events and slots.

Handlers and contributions run by (order, registration index). Each table below
reproduces an order the game already depends on: random draws (mine before
fishing at reset, fishing before mine in the morning), object order on a page,
and attribute order in save files. Names refer to features; entries for
features that are still part of the core engine document where they will go.

Pass these constants as `order=`; never a bare number.
"""

DEFAULT = 100


class Reset:
    """engine.reset(). Handlers below CORE run before core state is initialised, the rest after it."""
    VILLAGE = 10    # reset_village() ran first, so rowan_* attributes come first in saves
    CORE = 50       # boundary: core resources, plots, minigame and pointer state
    MINING = 60     # regenerate_mine() draws random numbers before the fishing target
    FISHING = 70
    NPC = 80
    FLOWERS = 90


class EndOfDay:
    """Start of the morning transition (finish_sleep), before the day number changes."""
    FLOWERS = 10    # wilting roll before crops grow
    FARMING = 20


class StartOfDay:
    """After the day number changes in finish_sleep."""
    FISHING = 10    # new fishing target, then
    MINING = 20     # new rocks (both draw random numbers)


class BeforeNavigation:
    """First step of travel, return-to-scene and F1/F2/F3 menus."""
    FLOWERS = 10


class HomeObjects:
    """Slot home.objects: appended after bed, research and kitchen."""
    FLOWERS = 10


class HomeSceneObjects:
    """Slot home.scene_objects: between the kitchen hitbox and the roads."""
    FLOWERS = 10


class HomeScene:
    """Slot home.scene: drawn after the furniture."""
    FLOWERS = 10


class InventoryItems:
    """Slot inventory.items, in the order the inventory listed them."""
    CORE_RESOURCES = 10   # gold, fertilizer, wood, stone
    MINING = 20           # pickaxe, copper, iron, diamond
    FARMING = 30          # seeds, then crops
    COOKING = 40          # foods
    FISHING = 50          # fishing rod, fish
    FLOWERS = 60          # morning glory seeds


class ShopBuyItems:
    """Slot shop.buy_items, in the order the buy page listed them."""
    FARMING = 10    # seeds, fertilizer
    MINING = 20     # pickaxe, minerals
    FISHING = 30    # fishing rod
    FLOWERS = 40    # morning glory seeds


class HarvestBonus:
    """Slot harvest.bonus: summed, so order does not change the result."""
    FLOWERS = 10

"""Named run order for registry events and slots.

Handlers and contributions run by (order, registration index). Each table below
reproduces an order the game already depends on: random draws (mine before
fishing at reset, fishing before mine in the morning) and object order on a
page. Save-file key order does not depend on these tables; it is fixed by
SAVE_KEY_ORDER in visionpad/services/saves.py. Names refer to features; entries for
features that are still part of the core engine document where they will go.

Pass these constants as `order=`; never a bare number.
"""

DEFAULT = 1000  # after every named entry


class Reset:
    """engine.reset(): feature handlers run after core state is initialised, in this order."""
    VILLAGE = 10
    INVENTORY = 15
    RESEARCH = 20
    SHOP = 25
    FARMING = 30
    HARVEST = 40
    COOKING = 50
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


class LeaveActivity:
    """leave_activity: clear minigames in the order the engine always cleared them."""
    FARMING = 10    # care minigame (and the plot detail page)
    HARVEST = 20
    COOKING = 30


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


class ShopSellItems:
    """Slot shop.sell_items, in the order the sell page listed them."""
    FARMING = 10    # crops
    COOKING = 20    # foods
    MINING = 30     # minerals
    FISHING = 40    # fish


class HarvestBonus:
    """Slot harvest.bonus: summed, so order does not change the result."""
    FLOWERS = 10

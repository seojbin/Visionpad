"""Feature registry: the single place where features plug into the engine.

State rule
    A feature keeps no state of its own. Every game value stays an attribute on
    the engine with its historical name, because `snapshot()` saves `vars(engine)`
    and `restore_snapshot()` rejects any change in that attribute set. Features
    read and write those attributes through `self.engine` (shared values through
    the helpers in `visionpad.core.state`).

Registering
    Each feature subclasses `Feature` and declares its hooks in `register(reg)`.
    `visionpad.features.ENABLED` lists the features; adding one is one line there.

Ordering
    Lifecycle events and slot contributions run by `(order, registration index)`.
    Orders are named constants from `visionpad.core.order`, one table per event
    or slot; the default is `order.DEFAULT`.

Ownership
    `reg.owns(*names)` declares the engine attributes a feature owns. Two
    features owning one attribute is an error, and every owned attribute must
    exist after `engine.reset()`.

Hotspots (AUDIT.md section 3.4) and the call that replaces each one:
    1 page table, 2 page names, 5 pointer handlers, 8 guidance, 3 page scene  -> page()
    3 object renderers                                                        -> renderer()
    4 action chain                                                            -> action()
    6 hover speech / hover sound                                              -> object_tts(), hover_sfx()
    7 get_state keys, 15 spectator keys                                       -> state(), spectator()
    9 reset, 10 day change, 11 navigation cleanup                             -> on()
    12 save format                                                            -> save_fields()
    13 icon policy                                                            -> icon(), icon_alias()
    14 shop catalogue                                                         -> shop_item() + contribute("shop.buy_items")
    shared page contents (home, inventory, harvest yield)                     -> slot(), contribute()
    attribute ownership                                                       -> owns()
"""
from visionpad.core import order as run_order

EVENTS = {
    "reset": "End of engine.reset(), after core state. Set the feature's engine attributes.",
    "end_of_day": "Start of the morning transition, before crops grow and the day number changes.",
    "start_of_day": "After the day number changes, before the morning page is rendered.",
    "before_navigation": "First step of travel, return-to-scene and F1/F2/F3 menu changes.",
}

# Slots exposed by pages that are still part of the core engine. A feature that
# owns a page declares that page's slots with reg.slot() instead.
CORE_SLOTS = {
    "home.objects": "Extra tactile objects on the home page (daytime only). Provider returns a list of objects.",
    "home.scene_objects": "Home scene hitboxes, inserted after the kitchen and before the roads (daytime only).",
    "home.scene": "Drawing on the home scene after the furniture (daytime only). Provider draws, returns None.",
    "inventory.items": "Inventory entries appended after fish. Provider returns a list of entry dicts.",
    "shop.buy_items": "Shop buy rows appended after the fishing rod: (kind, item_id, label, owned, price).",
    "harvest.bonus": "Integer added to every harvest yield. Provider returns a number.",
}

POINTER_KINDS = ("move", "down", "drag", "up")


class Feature:
    """Base class. One instance per engine; `self.engine` is the only state holder."""
    name = ""

    def __init__(self, engine):
        self.engine = engine

    def register(self, reg):
        raise NotImplementedError


class Page:
    def __init__(self, feature, name=None, objects=None, scene=None, guidance=None,
                 press=None, single_press=False, icon_grid=False, **pointer):
        unknown = set(pointer) - {"pointer_" + kind for kind in POINTER_KINDS}
        if unknown:
            raise TypeError(f"Unknown page hook(s): {', '.join(sorted(unknown))}")
        self.feature, self.name, self.objects, self.scene, self.guidance = feature, name, objects, scene, guidance
        self.press, self.single_press, self.icon_grid = press, single_press, icon_grid
        self.pointer = {kind: pointer.get("pointer_" + kind) for kind in POINTER_KINDS}


class Registry:
    def __init__(self):
        self.features = {}
        self.pages = {}
        self.actions = {}
        self.renderers = {}
        self.tts = {}
        self.hover_sounds = {}
        self.state_providers = {}
        self.spectator_providers = {}
        self.events = {name: [] for name in EVENTS}
        self.slot_docs = dict(CORE_SLOTS)
        self.slot_owners = dict.fromkeys(CORE_SLOTS, "core")
        self.slots = {}
        self.owners = {}
        self.shop_buyers = {}
        self.fixed_price_kinds = set()
        self.icon_patterns = {}
        self.icon_skips = {}
        self.icon_layout_order = {}
        self.icon_aliases = {}
        self.save_transient = {}
        self.save_defaults = []
        self._current = None
        self._sequence = 0

    @classmethod
    def build(cls, engine, feature_classes):
        registry = cls()
        for feature_class in feature_classes:
            feature = feature_class(engine)
            if not feature.name or feature.name in registry.features:
                raise ValueError(f"Feature needs a unique name: {feature_class.__name__}")
            registry.features[feature.name] = feature
            registry._current = feature.name
            feature.register(registry)
        registry._current = None
        undeclared = sorted(set(registry.slots) - set(registry.slot_docs))
        if undeclared:
            raise ValueError(f"Unknown slot(s) {', '.join(undeclared)}; known: {', '.join(registry.slot_docs)}")
        return registry

    def check_owned(self, engine):
        """Every owned attribute must exist on the engine once reset() has run."""
        missing = sorted(name for name in self.owners if not hasattr(engine, name))
        if missing:
            raise ValueError(f"Owned attribute(s) missing after reset: {', '.join(missing)}")

    # ---- registration (called from Feature.register) ----

    def _claim(self, table, key, value, what):
        if key in table:
            raise ValueError(f"{what} {key!r} is already registered")
        table[key] = value

    def page(self, page_id, *, name=None, objects=None, scene=None, guidance=None,
             press=None, single_press=False, icon_grid=False, **pointer):
        """Own a page.
        objects() -> list of tactile objects; name -> spoken page name; scene() draws after the objects;
        guidance() -> (kind, targets, completed, total) for audio_guidance.
        pointer_move/down/drag/up(x, y) run first in the engine's pointer method with raw input (no sleep,
        pause or busy checks) and return a response, or None to continue with the core handler.
        press(x, y) runs inside pointer_down after the core checks and bookkeeping, in place of object
        selection. single_press ignores a new press while the pointer is still held.
        icon_grid places the page's icon objects on the shared twelve-slot grid."""
        page = Page(self._current, name, objects, scene, guidance, press, single_press, icon_grid, **pointer)
        self._claim(self.pages, page_id, page, "Page")

    def action(self, key, handler, *, before_night_guard=False):
        """Own an action. A key ending in ':' is a prefix: handler(arg, obj) gets the text after it.
        An exact key calls handler(None, obj). Only actions that already ignore the night guard set
        before_night_guard=True (the handler then checks day_ended itself)."""
        self._claim(self.actions, key, (handler, before_night_guard), "Action")

    def renderer(self, object_type, draw):
        """draw(obj) puts the object on the dot pad when the icon renderer did not draw it."""
        self._claim(self.renderers, object_type, draw, "Renderer")

    def object_tts(self, object_type, describe):
        """describe(obj) -> short hover text (detail=False)."""
        self._claim(self.tts, object_type, describe, "Object speech")

    def hover_sfx(self, object_type, sound):
        self._claim(self.hover_sounds, object_type, sound, "Hover sound")

    def state(self, key, provider):
        """provider() -> value for get_state()[key]."""
        self._claim(self.state_providers, key, provider, "State key")

    def spectator(self, key, provider):
        """provider(objects) -> value for the companion snapshot."""
        self._claim(self.spectator_providers, key, provider, "Spectator key")

    def on(self, event, handler, order=run_order.DEFAULT):
        if event not in EVENTS:
            raise ValueError(f"Unknown event {event!r}; known: {', '.join(EVENTS)}")
        self.events[event].append((order, self._next(), handler))

    def slot(self, name, description):
        """Declare a slot on a page this feature owns; other features contribute() to it."""
        if name in self.slot_docs:
            raise ValueError(f"Slot {name!r} is already declared by {self.slot_owners[name]}")
        self.slot_docs[name], self.slot_owners[name] = description, self._current

    def contribute(self, slot, provider, order=run_order.DEFAULT):
        """Add to a slot. The slot may be declared by a feature registered later; build() checks it."""
        self.slots.setdefault(slot, []).append((order, self._next(), provider))

    def owns(self, *names):
        for name in names:
            if name in self.owners:
                raise ValueError(f"Attribute {name!r} is owned by both {self.owners[name]} and {self._current}")
            self.owners[name] = self._current

    def shop_item(self, kind, buy, *, market_price=True):
        """buy(item_id) -> response, or None when this feature does not sell that item."""
        self._claim(self.shop_buyers, kind, buy, "Shop kind")
        if not market_price:
            self.fixed_price_kinds.add(kind)

    def icon(self, object_type, *, pattern=None, skip=None, layout_order=None):
        """Draw object_type with the shared icon frame. pattern(obj) -> rows; skip(obj) -> True leaves
        the object to its renderer(); layout_order places it on home/town icon grids."""
        self._claim(self.icon_patterns, object_type, pattern, "Icon")
        if skip:
            self.icon_skips[object_type] = skip
        if layout_order is not None:
            self.icon_layout_order[object_type] = layout_order

    def icon_alias(self, kind, symbol):
        self._claim(self.icon_aliases, kind, symbol, "Icon alias")

    def save_fields(self, *, transient=None, defaults=()):
        """transient: attribute -> value written into every save and after every load.
        defaults: attributes that older saves may lack; filled from a fresh engine on load."""
        for key, value in (transient or {}).items():
            self._claim(self.save_transient, key, value, "Transient save field")
        self.save_defaults.extend(defaults)

    def _next(self):
        self._sequence += 1
        return self._sequence

    # ---- dispatch (called from core) ----

    def run(self, event, *, until=None, since=None):
        """Run handlers in order; until/since restrict to orders below / at or above a boundary."""
        for order, _, handler in sorted(self.events[event], key=lambda entry: entry[:2]):
            if (until is None or order < until) and (since is None or order >= since):
                handler()

    def _providers(self, slot):
        if slot not in self.slot_docs:
            raise ValueError(f"Unknown slot {slot!r}")
        return [provider for _, _, provider in sorted(self.slots.get(slot, []), key=lambda entry: entry[:2])]

    def collect(self, slot):
        items = []
        for provider in self._providers(slot):
            items.extend(provider())
        return items

    def total(self, slot):
        return sum(provider() for provider in self._providers(slot))

    def draw_slot(self, slot):
        for provider in self._providers(slot):
            provider()

    def page_hook(self, page_id, hook):
        page = self.pages.get(page_id)
        return getattr(page, hook) if page else None

    def icon_grid_pages(self):
        return {page_id for page_id, page in self.pages.items() if page.icon_grid}

    def page_name(self, page_id):
        return self.page_hook(page_id, "name")

    def pointer(self, page_id, kind):
        page = self.pages.get(page_id)
        return page.pointer[kind] if page else None

    def action_for(self, action, before_night_guard):
        """(handler, arg) for an owned action in this phase of the chain, else None."""
        entry, arg = self.actions.get(action), None
        if entry is None and ":" in action:
            prefix, arg = action.split(":", 1)
            entry = self.actions.get(prefix + ":")
        if entry is None or entry[1] != before_night_guard:
            return None
        return entry[0], arg

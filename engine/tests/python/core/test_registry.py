"""Registry rules: conflicts, unknown names, ordering and attribute ownership."""
import tempfile
import types
import unittest
from unittest.mock import patch

from engine.config import load_config
from engine.core import order
from engine.core.engine import GameEngine
from engine.core import registry as registry_module
from engine.core.registry import Feature, Registry
from game import load_features
from engine.services.saves import SAVE_KEY_ORDER


def feature(name, register):
    return type(name.title(), (Feature,), {"name": name, "register": lambda self, reg: register(self, reg)})


def build(*features):
    return Registry.build(types.SimpleNamespace(), list(features))


class ConflictTests(unittest.TestCase):
    def test_two_features_cannot_claim_the_same_hook(self):
        claims = {
            "page": lambda reg: reg.page("p"),
            "action": lambda reg: reg.action("go:", lambda arg, obj: None),
            "renderer": lambda reg: reg.renderer("thing", lambda obj: None),
            "state key": lambda reg: reg.state("key", lambda: 1),
            "spectator key": lambda reg: reg.spectator("key", lambda objects: 1),
            "shop kind": lambda reg: reg.shop_item("kind", lambda item: None),
            "icon": lambda reg: reg.icon("thing"),
            "slot": lambda reg: reg.slot("page.items", "Items"),
        }
        for label, claim in claims.items():
            with self.subTest(label), self.assertRaises(ValueError):
                build(feature("a", lambda self, reg: claim(reg)), feature("b", lambda self, reg: claim(reg)))

    def test_feature_names_must_be_unique_and_present(self):
        with self.assertRaises(ValueError):
            build(feature("a", lambda self, reg: None), feature("a", lambda self, reg: None))
        with self.assertRaises(ValueError):
            build(feature("", lambda self, reg: None))

    def test_core_slots_cannot_be_redeclared(self):
        with patch.dict(registry_module.CORE_SLOTS, {"core.items": "Items exposed by a core page"}):
            with self.assertRaises(ValueError):
                build(feature("a", lambda self, reg: reg.slot("core.items", "Again")))


class UnknownNameTests(unittest.TestCase):
    def test_unknown_event_is_rejected_at_registration(self):
        with self.assertRaisesRegex(ValueError, "Unknown event"):
            build(feature("a", lambda self, reg: reg.on("sunset", lambda: None)))

    def test_unknown_slot_is_rejected_after_all_features_register(self):
        with self.assertRaisesRegex(ValueError, "Unknown slot"):
            build(feature("a", lambda self, reg: reg.contribute("nowhere", lambda: [])))

    def test_unknown_page_hook_is_rejected(self):
        with self.assertRaises(TypeError):
            build(feature("a", lambda self, reg: reg.page("p", pointer_hover=lambda x, y: None)))

    def test_collecting_an_undeclared_slot_fails(self):
        with self.assertRaises(ValueError):
            build().collect("nowhere")


class SlotTests(unittest.TestCase):
    def test_a_slot_declared_by_a_later_feature_accepts_earlier_contributions(self):
        registry = build(feature("guest", lambda self, reg: reg.contribute("host.items", lambda: ["guest"])),
                         feature("host", lambda self, reg: reg.slot("host.items", "Host items")))
        self.assertEqual(registry.collect("host.items"), ["guest"])
        self.assertEqual(registry.slot_owners["host.items"], "host")

    def test_a_declared_slot_without_contributions_is_empty(self):
        registry = build(feature("host", lambda self, reg: reg.slot("host.items", "Host items")))
        self.assertEqual(registry.collect("host.items"), [])
        self.assertEqual(registry.total("host.items"), 0)


class OrderingTests(unittest.TestCase):
    def test_events_run_by_order_then_registration(self):
        calls = []
        registry = build(
            feature("a", lambda self, reg: (reg.on("reset", lambda: calls.append("a-late"), order=order.Reset.FLOWERS),
                                            reg.on("reset", lambda: calls.append("a-default")))),
            feature("b", lambda self, reg: (reg.on("reset", lambda: calls.append("b-early"), order=order.Reset.VILLAGE),
                                            reg.on("reset", lambda: calls.append("b-late"), order=order.Reset.FLOWERS))))
        registry.run("reset")
        self.assertEqual(calls, ["b-early", "a-late", "b-late", "a-default"])

    def test_reset_splits_at_the_core_boundary(self):
        calls = []
        registry = build(feature("a", lambda self, reg: (reg.on("reset", lambda: calls.append("before"), order=order.Reset.VILLAGE),
                                                         reg.on("reset", lambda: calls.append("after"), order=order.Reset.MINING))))
        registry.run("reset", until=order.Reset.RESEARCH)
        self.assertEqual(calls, ["before"])
        registry.run("reset", since=order.Reset.RESEARCH)
        self.assertEqual(calls, ["before", "after"])

    def test_slot_contributions_follow_their_order(self):
        registry = build(feature("a", lambda self, reg: reg.contribute("shop.buy_items", lambda: ["flowers"], order=order.ShopBuyItems.FLOWERS)),
                         feature("b", lambda self, reg: reg.contribute("shop.buy_items", lambda: ["farming"], order=order.ShopBuyItems.FARMING)),
                         feature("shop", lambda self, reg: reg.slot("shop.buy_items", "Buy rows")))
        self.assertEqual(registry.collect("shop.buy_items"), ["farming", "flowers"])

    def test_actions_dispatch_by_prefix_or_exact_key_in_their_guard_phase(self):
        registry = build(feature("a", lambda self, reg: (reg.action("go:", lambda arg, obj: ("go", arg), before_night_guard=True),
                                                         reg.action("stay", lambda arg, obj: ("stay", arg)))))
        handler, arg = registry.action_for("go:far:away", before_night_guard=True)
        self.assertEqual(handler(arg, {}), ("go", "far:away"))
        self.assertIsNone(registry.action_for("go:far", before_night_guard=False))
        handler, arg = registry.action_for("stay", before_night_guard=False)
        self.assertEqual(handler(arg, {}), ("stay", None))
        self.assertIsNone(registry.action_for("stay:here", before_night_guard=False))


class OwnershipTests(unittest.TestCase):
    def test_two_features_cannot_own_one_attribute(self):
        with self.assertRaisesRegex(ValueError, "owned by both"):
            build(feature("a", lambda self, reg: reg.owns("shared")), feature("b", lambda self, reg: reg.owns("shared")))

    def test_owned_attributes_must_exist_after_reset(self):
        registry = build(feature("a", lambda self, reg: reg.owns("present", "absent")))
        with self.assertRaisesRegex(ValueError, "absent"):
            registry.check_owned(types.SimpleNamespace(present=1))

    def test_enabled_features_own_existing_saved_attributes(self):
        engine = GameEngine(load_config("game"), save_dir=tempfile.mkdtemp())
        saved = set(engine.snapshot())
        for name, owner in engine.registry.owners.items():
            with self.subTest(attribute=name, feature=owner):
                self.assertIn(name, saved)


def engine_with(*extra_features):
    """A real engine whose feature list has extra test features appended."""
    features = load_features() + list(extra_features)
    with patch("engine.core.engine.load_features", return_value=features):
        return GameEngine(load_config("game"), save_dir=tempfile.mkdtemp())


class SaveOrderTests(unittest.TestCase):
    class Extra(Feature):
        name = "extra"

        def register(self, reg):
            reg.owns("zeta_extra", "alpha_extra")
            reg.on("reset", self.reset)

        def reset(self):
            self.engine.zeta_extra = {"kept": True}
            self.engine.alpha_extra = 3

    def test_new_attributes_follow_the_listed_keys_alphabetically(self):
        features = load_features() + [self.Extra]
        with patch("engine.core.engine.load_features", return_value=features):
            engine = GameEngine(load_config("game"), save_dir=tempfile.mkdtemp())
            keys = list(engine.snapshot())
            listed = [key for key in SAVE_KEY_ORDER if key in keys]
            self.assertEqual(keys[:len(listed)], listed)
            self.assertEqual(keys[len(listed):], ["alpha_extra", "zeta_extra", "random_state"])

    def test_new_attributes_survive_save_and_load(self):
        features = load_features() + [self.Extra]
        with patch("engine.core.engine.load_features", return_value=features):
            engine = GameEngine(load_config("game"), save_dir=tempfile.mkdtemp())
            engine.alpha_extra = 9
            engine.save_game()
            engine.alpha_extra = 0
            engine.open_load_game()
            result = engine.load_game(engine._save_slots[0]["id"])
            self.assertTrue(result["tts"].startswith("Game loaded."))
            self.assertEqual((engine.alpha_extra, engine.zeta_extra), (9, {"kept": True}))


class ExposeTests(unittest.TestCase):
    # Every engine method provided by a feature. A new entry here is a new cross-feature or
    # legacy entry point: review it (AGENTS.md: prefer events or slots).
    EXPECTED = {
        "buy_shop_item": "shop",
        "can_craft_recipe": "cooking",
        "cast_fishing": "fishing",
        "clear_care": "farming",
        "clear_cooking": "cooking",
        "clear_harvest": "harvest",
        "finish_care_minigame": "farming",
        "finish_cooking_success": "cooking",
        "finish_harvest_minigame": "harvest",
        "finish_seafood": "seafood",
        "fishing_config": "fishing",
        "get_cooking_gesture": "cooking",
        "get_effective_seed_return_chance": "farming",
        "get_fertilizer_price": "farming",
        "get_fish_price": "fishing",
        "get_harvest_base_yield": "harvest",
        "get_inventory_objects": "inventory",
        "get_mineral_price": "mining",
        "get_unlocked_plot_defs": "farming",
        "hit_mine_rock": "mining",
        "market_price": "village",
        "next_rowan_advice": "npc",
        "new_plot_state": "farming",
        "npc_action": "npc",
        "npc_voice_profile": "npc",
        "open_calendar": "village",
        "open_cooking_minigame": "cooking",
        "open_inventory": "inventory",
        "open_plot_detail": "farming",
        "open_shop": "shop",
        "plant_seed": "farming",
        "recent_reaction": "npc",
        "record_activity": "npc",
        "rowan_advice": "npc",
        "seafood_ingredient_objects": "seafood",
        "seafood_ready": "seafood",
        "selected_fish": "seafood",
        "sell_shop_item": "shop",
        "start_care_minigame": "farming",
        "start_harvest_minigame": "harvest",
        "submit_rowan_crop": "village",
        "talk_rowan": "village",
        "toggle_fish": "seafood",
        "use_food": "cooking",
    }

    def test_exposed_names_and_owners_are_reviewed(self):
        engine = GameEngine(load_config("game"), save_dir=tempfile.mkdtemp())
        self.assertEqual(engine.registry.api_owners, self.EXPECTED)

    def test_engine_calls_reach_the_exposed_function(self):
        engine = engine_with(feature("probe", lambda self, reg: reg.expose("probe_value", lambda x: ("probe", x))))
        self.assertEqual(engine.probe_value(4), ("probe", 4))
        with self.assertRaises(AttributeError):
            engine.not_exposed_anywhere

    def test_exposed_names_cannot_shadow_engine_methods_or_repeat(self):
        class Host:
            def render(self):
                pass
        with self.assertRaisesRegex(ValueError, "already defined"):
            Registry.build(Host(), [feature("a", lambda self, reg: reg.expose("render", lambda: None))])
        with self.assertRaises(ValueError):
            build(feature("a", lambda self, reg: reg.expose("same", lambda: None)),
                  feature("b", lambda self, reg: reg.expose("same", lambda: None)))


class ArrivalTests(unittest.TestCase):
    def test_arrival_hook_is_stored_on_the_page(self):
        arrival = lambda: "Welcome."
        registry = build(feature("a", lambda self, reg: reg.page("p", arrival=arrival)))
        self.assertIs(registry.page_hook("p", "arrival"), arrival)
        self.assertIsNone(registry.page_hook("other", "arrival"))

    def test_arrival_text_replaces_the_location_name_until_it_returns_none(self):
        engine = GameEngine(load_config("game"), save_dir=tempfile.mkdtemp())
        self.assertEqual(engine.travel_to("town")["tts"], "Village. Rowan would like to meet you.")
        engine.travel_to("home")
        self.assertEqual(engine.travel_to("town")["tts"], "Village")
        self.assertEqual(engine.travel_to("farm")["tts"], "Farm")


if __name__ == "__main__":
    unittest.main()

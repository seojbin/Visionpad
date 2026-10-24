"""Registry rules: conflicts, unknown names, ordering and attribute ownership."""
import tempfile
import types
import unittest

from visionpad.config import load_config
from visionpad.core import order
from visionpad.core.engine import GameEngine
from visionpad.core.registry import Feature, Registry


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
        with self.assertRaises(ValueError):
            build(feature("a", lambda self, reg: reg.slot("home.objects", "Again")))


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
                         feature("b", lambda self, reg: reg.contribute("shop.buy_items", lambda: ["farming"], order=order.ShopBuyItems.FARMING)))
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


if __name__ == "__main__":
    unittest.main()

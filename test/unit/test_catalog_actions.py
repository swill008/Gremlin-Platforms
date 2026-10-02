# -*- coding: utf-8; -*-
# Device-Configuration-Macro Change — add / remove / leaf coverage.

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_BC = _ROOT / "gremlin/ui/binding_catalog.py"

_PLUGIN_TAGS = [
    "map-to-vjoy",
    "map-to-keyboard",
    "map-to-mouse",
    "map-to-xbox",
    "map-to-logical-device",
    "macro",
    "change-mode",
    "load-profile",
    "text-to-speech",
    "run-command",
    "play-sound",
    "response-curve",
    "merge-axis",
    "split-axis",
    "axis-delta",
    "dual-axis-deadzone",
    "hat-buttons",
    "pause-resume",
    "chain",
    "tempo",
    "condition",
    "double-tap",
    "smart-toggle",
    "description",
    "reference",
]


class _Act:
    def __init__(self, tag, name=None, children=None, **kw):
        self.tag = tag
        self.name = name or tag
        self.children = list(children or [])
        for k, v in kw.items():
            setattr(self, k, v)

    def get_actions(self):
        return list(self.children), []


class _Seq:
    def __init__(self, root):
        self.root_action = root


class _Item:
    def __init__(self):
        self.action_sequences = []

    def add_item_binding(self):
        root = _Act("root", name="Root", children=[])
        seq = _Seq(root)
        self.action_sequences.append(seq)

        class _Binding:
            root_action = root

            def insert_action(self, action, where):
                root.children.append(action)

        return _Binding()

    def remove_item_binding(self, seq):
        self.action_sequences.remove(seq)


def _load_helpers():
    """Load catalog helpers without importing PySide6."""
    src = _BC.read_text(encoding="utf-8")
    start = src.index("_WRAPPERS = {")
    end = src.index("@ta.QmlElement")
    ns: dict = {
        "InputType": type("InputType", (), {"JoystickButton": 1}),
        "common": type("common", (), {"input_to_ui_string": staticmethod(lambda t, i: f"Button {i}")}),
        # Destination text comes from gremlin.modules.wiring (tested on its own).
        "wiring": type(
            "wiring",
            (),
            {
                "dest_label": staticmethod(
                    lambda a, short=False: (
                        f"vJoy {a.vjoy_device_id} · Button {a.vjoy_input_id}"
                    )
                )
            },
        ),
    }
    exec(src[start:end], ns)
    return ns


def test_summarize_covers_every_plugin_tag() -> None:
    ns = _load_helpers()
    labels = ns["_TYPE_LABELS"]
    wrappers = ns["_WRAPPERS"]
    for tag in _PLUGIN_TAGS:
        if tag == "root":
            continue
        assert tag in labels or tag in wrappers, tag
        act = _Act(tag, vjoy_device_id=1, vjoy_input_id=1, keys=["A"])
        lab, dest = ns["summarize_action"](act)
        assert lab
        assert dest


def test_one_row_per_sequence_for_each_dest_action() -> None:
    ns = _load_helpers()
    dest_tags = [t for t in _PLUGIN_TAGS if t not in ns["_WRAPPERS"] and t != "root"]
    item = _Item()
    for tag in dest_tags:
        binding = item.add_item_binding()
        binding.insert_action(_Act(tag, vjoy_device_id=1, vjoy_input_id=3), "children")
    rows = ns["sequences_for_item"](item)
    assert [index for index, _lab, _dest in rows] == list(range(len(dest_tags)))
    labels = ns["_TYPE_LABELS"]
    assert [lab for _i, lab, _d in rows] == [labels.get(t, t) for t in dest_tags]


def test_add_then_remove_every_sequence() -> None:
    ns = _load_helpers()
    dest_tags = [t for t in _PLUGIN_TAGS if t not in ns["_WRAPPERS"] and t != "root"]
    item = _Item()
    for tag in dest_tags:
        binding = item.add_item_binding()
        binding.insert_action(_Act(tag, vjoy_device_id=2, vjoy_input_id=1), "children")
        rows = ns["sequences_for_item"](item)
        assert rows[-1][0] == len(item.action_sequences) - 1
    assert len(item.action_sequences) == len(dest_tags)
    # Remove from the middle until empty; rows stay numbered 0..n-1.
    while item.action_sequences:
        mid = len(item.action_sequences) // 2
        item.remove_item_binding(item.action_sequences[mid])
        rows = ns["sequences_for_item"](item)
        assert [index for index, *_ in rows] == list(range(len(item.action_sequences)))
    assert ns["sequences_for_item"](item) == []


def test_wrapper_without_child_is_an_empty_sequence() -> None:
    ns = _load_helpers()
    item = _Item()
    binding = item.add_item_binding()
    binding.insert_action(_Act("tempo", children=[]), "children")
    assert ns["sequences_for_item"](item) == [(0, "Sequence", "Empty")]


def test_wrapper_with_child_shows_the_child() -> None:
    ns = _load_helpers()
    item = _Item()
    binding = item.add_item_binding()
    child = _Act("map-to-vjoy", vjoy_device_id=1, vjoy_input_id=4)
    binding.insert_action(_Act("chain", children=[child]), "children")
    rows = ns["sequences_for_item"](item)
    assert len(rows) == 1
    assert rows[0][1] == ns["_TYPE_LABELS"]["map-to-vjoy"]
    assert "vJoy 1" in rows[0][2]


def test_wrapper_two_dests_stay_one_row() -> None:
    ns = _load_helpers()
    item = _Item()
    binding = item.add_item_binding()
    a = _Act("map-to-vjoy", vjoy_device_id=1, vjoy_input_id=1)
    b = _Act("map-to-keyboard", keys=["A"])
    binding.insert_action(_Act("tempo", children=[a, b]), "children")
    rows = ns["sequences_for_item"](item)
    assert len(rows) == 1
    assert rows[0][1] == "2 actions"
    assert "vJoy 1" in rows[0][2]
    assert rows[0][2].endswith(", A")

# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# Device-Configuration-Macro Change

from types import SimpleNamespace

from gremlin.types import InputType
from gremlin.ui.binding_catalog import collect_leaves, summarize_action


class _Act:
    def __init__(self, tag, **kw):
        self.tag = tag
        self.name = kw.pop("name", tag)
        self.children = kw.pop("children", [])
        for k, v in kw.items():
            setattr(self, k, v)

    def get_actions(self):
        return self.children, ["children"] * len(self.children)


def test_vjoy_summary() -> None:
    a = _Act(
        "map-to-vjoy",
        name="Map to vJoy",
        vjoy_device_id=2,
        vjoy_input_id=1,
        vjoy_input_type=InputType.JoystickAxis,
    )
    label, dest = summarize_action(a)
    assert label == "Map to vJoy"
    assert "vJoy 2" in dest
    assert "X" in dest or "Axis" in dest


def test_keyboard_and_macro_on_one_button() -> None:
    root = _Act(
        "root",
        children=[
            _Act("macro", action_label="Fire group"),
            _Act(
                "map-to-vjoy",
                vjoy_device_id=2,
                vjoy_input_id=4,
                vjoy_input_type=InputType.JoystickButton,
            ),
            _Act("map-to-keyboard", keys=[SimpleNamespace(name="Space")]),
        ],
    )
    leaves = collect_leaves(root)
    tags = [t[0] for t in leaves]
    dests = [t[2] for t in leaves]
    assert tags == ["macro", "map-to-vjoy", "map-to-keyboard"]
    assert "Fire group" in dests
    assert any("Button 4" in d or "button 4" in d.lower() for d in dests)
    assert "Space" in dests


def test_tempo_unwraps_to_leaves() -> None:
    tempo = _Act(
        "tempo",
        children=[_Act("change-mode", _target_modes=["Combat"])],
    )
    leaves = collect_leaves(_Act("root", children=[tempo]))
    assert leaves[0][0] == "change-mode"
    assert "Combat" in leaves[0][2]

# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin/axis_names.py is the one axis-name table (06 S185, Set B) and
every reader takes its words from it."""

from __future__ import annotations

import re
from pathlib import Path

from gremlin import axis_names, common
from gremlin.modules import output, wiring
from gremlin.types import AxisNames, InputType

_ROOT = Path(__file__).resolve().parents[2]


def test_table_words() -> None:
    a = axis_names.AXES
    assert [x.number for x in a] == list(range(1, 9))
    assert [x.long for x in a] == [
        "X Axis",
        "Y Axis",
        "Z Axis",
        "X Rotation",
        "Y Rotation",
        "Z Rotation",
        "Slider 1",
        "Slider 2",
    ]
    assert [x.short for x in a] == ["X", "Y", "Z", "Rx", "Ry", "Rz", "S1", "S2"]
    assert [x.vjoy_config for x in a] == [
        "x",
        "y",
        "z",
        "rx",
        "ry",
        "rz",
        "sl0",
        "sl1",
    ]
    assert [x.usage for x in a] == list(range(0x30, 0x38))


def test_unknown_numbers() -> None:
    assert axis_names.long_name(9) == "Axis 9"
    assert axis_names.short_name(9) == "A9"


def test_readers_use_the_table() -> None:
    for x in axis_names.AXES:
        assert AxisNames.to_string(AxisNames(x.number)) == x.long
        assert common.input_to_ui_string(InputType.JoystickAxis, x.number) == x.long
        assert output.control_label(None, "axis", x.number) == x.long
        assert wiring._input_short("axis", x.number) == x.short
    # A number past the table no longer raises.
    assert common.input_to_ui_string(InputType.JoystickAxis, 9) == "Axis 9"


def test_vjoy_axis_codes_match_the_table() -> None:
    from vjoy import vjoy

    assert [c.value for c in vjoy.AxisCode] == [x.usage for x in axis_names.AXES]
    assert vjoy.VJoyStateCache.axis_lookup == {
        x.number: x.usage for x in axis_names.AXES
    }
    assert {c.value: n for c, n in vjoy.VJoy.axis_equivalence.items()} == {
        x.usage: x.number for x in axis_names.AXES
    }


def _sources() -> dict[str, str]:
    files = [
        p
        for top in ("gremlin", "action_plugins", "vjoy")
        for p in _ROOT.joinpath(top).rglob("*.py")
    ]
    files.append(_ROOT / "qml" / "OutputModuleView.qml")
    return {
        p.relative_to(_ROOT).as_posix(): p.read_text(encoding="utf-8") for p in files
    }


def test_no_other_axis_word_table() -> None:
    # Any second copy of the words (long or short) is a table of its own.
    words = re.compile(r'"(X Rotation|Z Rotation|Slider|Dial|Rx|Rz|S2)"')
    found = sorted(rel for rel, text in _sources().items() if words.search(text))
    assert found == ["gremlin/axis_names.py"]
    for rel, text in _sources().items():
        assert "AXIS_SHORT" not in text, rel
        assert "AXIS_WORDS" not in text, rel


def test_output_view_asks_the_model_for_short_names() -> None:
    from gremlin.ui.module_model import ModuleListModel

    assert ModuleListModel.axisShort(None, 7) == "S1"
    qml = (_ROOT / "qml" / "OutputModuleView.qml").read_text(encoding="utf-8")
    assert "moduleModel.axisShort(hw)" in qml

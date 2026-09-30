# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from gremlin.ui.module_model import collect_bound_names


def test_evo_r_to_vjoy2_and_back() -> None:
    src, dest = collect_bound_names(
        {"AAA": "VKBsim Gladiator EVO R"},
        {2: "vJoy 2"},
        "Xbox 360 Controller",
        [("AAA", "vjoy", 2)],
    )
    assert src["AAA"] == ["vJoy 2"]
    assert dest["vjoy:2"] == ["VKBsim Gladiator EVO R"]


def test_many_to_many_unique_names() -> None:
    src, dest = collect_bound_names(
        {"R": "VKBsim Gladiator EVO R", "S": "VKBSim NXT SEM THQ FSM.GA"},
        {2: "vJoy 2", 3: "vJoy 3"},
        "Xbox 360 Controller",
        [
            ("R", "vjoy", 2),
            ("R", "vjoy", 2),
            ("R", "vjoy", 3),
            ("S", "vjoy", 3),
        ],
    )
    assert src["R"] == ["vJoy 2", "vJoy 3"]
    assert dest["vjoy:3"] == ["VKBsim Gladiator EVO R", "VKBSim NXT SEM THQ FSM.GA"]


def test_xbox_wire_uses_full_name() -> None:
    src, dest = collect_bound_names(
        {"X": "VKBsim Gladiator EVO L"},
        {1: "vJoy 1"},
        "Xbox 360 Controller",
        [("X", "xbox", 1)],
    )
    assert src["X"] == ["Xbox 360 Controller"]
    assert dest["xbox"] == ["VKBsim Gladiator EVO L"]


def test_unwired_stays_empty() -> None:
    src, dest = collect_bound_names(
        {"R": "VKBsim Gladiator EVO R"},
        {1: "vJoy 1"},
        "Xbox 360 Controller",
        [],
    )
    assert src == {}
    assert dest == {}


from pathlib import Path

def test_status_card_always_shows_bound_to() -> None:
    text = Path(__file__).resolve().parents[2].joinpath("qml/StatusCard.qml").read_text(encoding="utf-8")
    assert 'Bound to: [' in text
    assert "Not bound" in text
    assert "visible: target.length" not in text


def test_bound_line_format_in_qml_and_model() -> None:
    main = Path(__file__).resolve().parents[2].joinpath("qml/Main.qml").read_text(encoding="utf-8")
    model = Path(__file__).resolve().parents[2].joinpath("gremlin/ui/module_model.py").read_text(encoding="utf-8")
    assert "Bound to: [Not bound]" in main
    assert "def boundLine" in model
    assert "refreshDestBound" in main

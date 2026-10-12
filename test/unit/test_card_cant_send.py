# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Bindings the program can't send, on the SOURCE device's Home card (03 Home
card, D-05-CANT-SEND): a red outline (kept when the card is picked) and a
red line "⚠ n binding outputs not found" whose tip lists the first 10 as
"<input> (<mode>) → <text>" then "… and n more". The count and list come
from output.cant_send_bindings, grouped by the binding's device id."""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.append(".")

from types import SimpleNamespace

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
from PySide6 import QtCore

from gremlin import config
from gremlin.common import SingletonMetaclass
from gremlin.modules import output
from gremlin.ui import module_model

_HERE = pathlib.Path(__file__).parent
_STICK = "{00000001-0000-0000-0000-000000000000}"
_CLEAN = "{00000002-0000-0000-0000-000000000000}"
_REAL_BINDINGS = output.cant_send_bindings


def _binding(n: int, guid: str = _STICK) -> dict:
    return {
        "device_guid": guid,
        "device_name": "Throttle",
        "input_type": "button",
        "input_id": n,
        "input_label": f"Button {n}",
        "mode": "Default",
        "text": f"vJoy 1's Button {n + 40} is not Found (vJoy 1 has Buttons 1–20).",
    }


def _stick(name: str, guid: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        device_guid=guid,
        vendor_id=1,
        product_id=1,
        button_count=4,
        axis_count=2,
        hat_count=0,
    )


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path):  # noqa: ANN201
    from gremlin import device_initialization

    QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    monkeypatch.delitem(
        SingletonMetaclass._instances, config.Configuration, raising=False
    )
    config.Configuration()
    monkeypatch.setattr(
        device_initialization,
        "physical_devices",
        lambda: [_stick("Throttle", _STICK), _stick("Pedals", _CLEAN)],
    )
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(module_model, "module_exists", lambda _name, _guid="": False)
    monkeypatch.setattr(module_model, "_show_stubs", lambda: True)
    monkeypatch.setattr(module_model, "apply_bound_targets", lambda _rows: None)
    monkeypatch.setattr(module_model.ModuleListModel, "_stacks", lambda _self: [])
    found: list[dict] = []
    monkeypatch.setattr(
        output, "cant_send_bindings", lambda profile=None: list(found), raising=False
    )
    made = module_model.ModuleListModel()
    made.found = found
    return made


def _card(model: module_model.ModuleListModel, slug: str) -> dict:
    return model.cardMap(slug)


def _role(model: module_model.ModuleListModel, slug: str, name: str) -> object:
    roles = {bytes(v).decode(): k for k, v in model.roleNames().items()}
    row = next(i for i, r in enumerate(model._rows) if r.slug == slug)
    return model.data(model.index(row, 0), roles[name])


def test_two_unsendable_bindings_show_on_the_source_card(
    model: module_model.ModuleListModel,
) -> None:
    model.found[:] = [_binding(3), _binding(1)]
    model._reload()
    card = _card(model, "throttle")
    assert card["cantSendCount"] == 2
    assert _role(model, "throttle", "cantSendCount") == 2
    # The provider's order, one line each.
    has = "is not Found (vJoy 1 has Buttons 1–20)."
    assert card["cantSendTip"] == (
        f"Button 3 (Default) → vJoy 1's Button 43 {has}\n"
        f"Button 1 (Default) → vJoy 1's Button 41 {has}"
    )
    assert _role(model, "throttle", "cantSendTip") == card["cantSendTip"]
    # A device with none, and the cards with no bindings, show nothing.
    for slug in ("pedals", "keyboard", "osc", "logical"):
        assert _card(model, slug)["cantSendCount"] == 0, slug
        assert _card(model, slug)["cantSendTip"] == "", slug


def test_more_than_ten_lists_ten_then_and_n_more(
    model: module_model.ModuleListModel,
) -> None:
    model.found[:] = [_binding(n) for n in range(1, 14)]
    model._reload()
    card = _card(model, "throttle")
    assert card["cantSendCount"] == 13
    lines = card["cantSendTip"].split("\n")
    assert len(lines) == 11
    assert lines[0].startswith("Button 1 (Default) → ")
    assert lines[9].startswith("Button 10 (Default) → ")
    assert lines[10] == "… and 3 more"


def test_the_card_follows_an_action_edit(model: module_model.ModuleListModel) -> None:
    model._reload()
    assert _card(model, "throttle")["cantSendCount"] == 0
    changed: list[int] = []
    model.cantSendChanged.connect(lambda: changed.append(1))
    model.found[:] = [_binding(2)]
    # The bindings' owner's notice (D-01-OWNER-NOTICES 1a).
    from gremlin.signal import signal as _signal

    _signal.bindingsChanged.emit()
    assert _card(model, "throttle")["cantSendCount"] == 1
    assert changed == [1]
    # Claims, vJoy driver, Xbox, OSC, Logical Device: the output layer's
    # one notice (D-05-CANT-SEND-LIVE).
    model.found[:] = []
    from gremlin.signal import signal

    signal.cantSendChanged.emit()
    assert _card(model, "throttle")["cantSendCount"] == 0


def test_the_card_reads_the_real_list_from_the_current_profile(
    model: module_model.ModuleListModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through output.cant_send_bindings itself: the profile's binding on the
    Throttle, a stand-in for the vJoy driver's answer only."""
    from gremlin import shared_state
    from gremlin.types import InputType

    monkeypatch.setattr(output, "cant_send_bindings", _REAL_BINDINGS)
    action = SimpleNamespace(get_actions=lambda: ([], []))
    monkeypatch.setattr(
        output, "vjoy_targets", lambda a: [(1, "button", 57)] if a is action else []
    )
    monkeypatch.setattr(
        output,
        "cant_send_text",
        lambda v, k, c: (
            f"vJoy {v}'s Button {c} is not Found (vJoy {v} has Buttons 1–20)."
        ),
    )
    item = SimpleNamespace(
        device_id=_STICK,
        input_type=InputType.JoystickButton,
        input_id=5,
        mode="Default",
        action_sequences=[SimpleNamespace(root_action=action)],
    )
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={_STICK: [item]}),
        raising=False,
    )
    model._reload()
    card = _card(model, "throttle")
    assert card["cantSendCount"] == 1
    assert card["cantSendTip"].endswith(
        "(Default) → vJoy 1's Button 57 is not Found (vJoy 1 has Buttons 1–20)."
    )
    assert _card(model, "pedals")["cantSendCount"] == 0


def test_the_line_counts_in_words() -> None:
    assert module_model.cant_send_line(0) == ""
    assert module_model.cant_send_line(1) == "⚠ 1 binding output not found"
    assert module_model.cant_send_line(2) == "⚠ 2 binding outputs not found"


_RED = "function _red() { return Qt.colorEqual(_card.border.color, Style.danger) }; "

_STEPS = [
    (
        "clean",
        "_card.cantSendCount = 0; _card.cantSendTip = '';"
        " [_card.cantSendShown, _red()].join('|')",
    ),
    (
        "two",
        "_card.cantSendCount = 2; _card.cantSendTip = 'Button 1 (Default) → x';"
        " [_card.cantSendShown, _card.cantSendText,"
        " _red(), _card.border.width].join('|')",
    ),
    (
        "selected",
        "_card.selected = true; [_red(), _card.border.width].join('|')",
    ),
    (
        "focused",
        "_card.selected = false; _card.forceActiveFocus();"
        " [_card.activeFocus, _red(),"
        " _card.border.width].join('|')",
    ),
    ("plain-width", "String(Style.dp(2)) + '|' + String(Style.dp(3))"),
]

_RUNNER = (
    "import sys, importlib.util\n"
    "spec = importlib.util.spec_from_file_location('menus_smoke', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    f"mod.STEPS = {[(name, _RED + code) for name, code in _STEPS]!r}\n"
    "sys.argv = [sys.argv[0], sys.argv[2]]\n"
    "mod.main()\n"
)


def test_status_card_shows_the_red_line_and_outline(tmp_path: pathlib.Path) -> None:
    result = proc_tree.run(
        [sys.executable, "-c", _RUNNER, str(_HERE / "menus_smoke.py"), str(tmp_path)],
        text=True,
        encoding="utf-8",
        timeout=120,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, smoke_report.explain(result)
    assert [line for line in lines if line.startswith("ERROR")] == []
    got = {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }
    two_px, three_px = got["plain-width"].split("|")
    assert got["clean"] == "false|false"
    assert got["two"] == f"true|⚠ 2 binding outputs not found|true|{two_px}"
    # Picked or focused, it stays red; focus shows as a thicker outline.
    assert got["selected"] == f"true|{three_px}"
    assert got["focused"] == f"true|true|{three_px}"

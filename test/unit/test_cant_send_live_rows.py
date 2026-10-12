# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Page rows, the Find bar's "Binding output not found" tick and the Home card follow
the output layer's one notice, signal.cantSendChanged (D-05-CANT-SEND-LIVE):
when what output.cant_send_text / output.cant_send_bindings answer changes
and the notice goes out, the red ⚠ is re-read with no other signal. A
deleted list leaves no connection to the notice behind.

The output functions are stand-ins here; the real sources of the notice are
tested with gremlin/modules/output.py.

Spec: 05 S138 S139, 03 S78a (D-05-CANT-SEND-LIVE).
"""

from __future__ import annotations

import gc
import pathlib
import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import config, plugin_manager, shared_state
from gremlin.common import InputType, SingletonMetaclass
from gremlin.logical_device import LogicalDevice
from gremlin.modules import output
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.ui import module_model

BAD = 99
TEXT = "vJoy 1's Button 99 is not Found (vJoy 1 has Buttons 1–20)."
_STICK = "{00000001-0000-0000-0000-000000000000}"
_NOTICE = QtCore.SIGNAL("cantSendChanged()")


def _flush() -> None:
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()


# -- Page rows and the Find tick (Logical Device page, the base's rows) -----


@pytest.fixture
def bad(monkeypatch: pytest.MonkeyPatch) -> dict[int, str]:
    """vJoy 1's buttons listed here can't be sent, with this text."""
    found: dict[int, str] = {}
    monkeypatch.setattr(
        output, "cant_send_text", lambda v, k, control: found.get(int(control))
    )
    return found


@pytest.fixture
def rows(qapp: object, bad: dict) -> Iterator[Any]:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().load_dict({"controls": [], "groups": []})
    old = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    device = LogicalDevice()
    device.create(InputType.JoystickButton)
    real = profile.get_input_item(
        device.device_guid, InputType.JoystickButton, 1, "Default", True
    )
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = BAD
    action.vjoy_input_type = InputType.JoystickButton
    real.add_item_binding().root_action.insert_action(action, "children")
    model = LogicalLayoutModel()
    try:
        yield model
    finally:
        model.endPane()
        model.deleteLater()
        _flush()
        shared_state.current_profile = old
        LogicalDevice().load_dict({"controls": [], "groups": []})


def _row(model: Any, kind: str) -> dict:  # noqa: ANN401
    return next(row for row in model._rows if row["rowKind"] == kind)


def test_rows_and_find_tick_follow_the_notice(rows: Any, bad: dict) -> None:  # noqa: ANN401
    assert _row(rows, "parent")["cantSend"] == ""
    rows.setCantSendOnly(True)
    assert not [r for r in rows._rows if r["rowKind"] == "parent"]
    # The vJoy device changed under the binding: only the notice goes out.
    bad[BAD] = TEXT
    signal.cantSendChanged.emit()
    assert [r["key"] for r in rows._rows if r["rowKind"] == "parent"] == [
        "parent:button:1"
    ]
    assert TEXT in _row(rows, "parent")["cantSend"]
    assert _row(rows, "child")["cantSend"] == TEXT
    # Fixed again: the ⚠ goes, and the tick shows nothing.
    bad.clear()
    signal.cantSendChanged.emit()
    assert not [r for r in rows._rows if r["rowKind"] == "parent"]
    rows.setCantSendOnly(False)
    assert _row(rows, "parent")["cantSend"] == ""
    assert _row(rows, "child")["cantSend"] == ""


def test_deleted_rows_drop_the_notice_connection(qapp: object) -> None:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().load_dict({"controls": [], "groups": []})
    _flush()
    before = signal.receivers(_NOTICE)
    model = LogicalLayoutModel()
    assert signal.receivers(_NOTICE) > before
    model.deleteLater()
    del model
    _flush()
    assert signal.receivers(_NOTICE) <= before


# -- Home card ---------------------------------------------------------------


def _binding(n: int) -> dict:
    return {
        "device_guid": _STICK,
        "device_name": "Throttle",
        "input_type": "button",
        "input_id": n,
        "input_label": f"Button {n}",
        "mode": "Default",
        "text": f"vJoy 1's Button {n + 40} is not Found (vJoy 1 has Buttons 1–20).",
    }


@pytest.fixture
def cards(
    qapp: object, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Iterator[module_model.ModuleListModel]:
    from gremlin import device_initialization

    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    monkeypatch.delitem(
        SingletonMetaclass._instances, config.Configuration, raising=False
    )
    config.Configuration()
    stick = SimpleNamespace(
        name="Throttle",
        device_guid=_STICK,
        vendor_id=1,
        product_id=1,
        button_count=4,
        axis_count=2,
        hat_count=0,
    )
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: [stick])
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(module_model, "module_exists", lambda _name, _guid="": False)
    monkeypatch.setattr(module_model, "_show_stubs", lambda: True)
    monkeypatch.setattr(module_model, "apply_bound_targets", lambda _rows: None)
    monkeypatch.setattr(module_model.ModuleListModel, "_stacks", lambda _self: [])
    found: list[dict] = []
    monkeypatch.setattr(
        output, "cant_send_bindings", lambda profile=None: list(found), raising=False
    )
    model = module_model.ModuleListModel()
    model.found = found  # type: ignore[attr-defined]
    try:
        yield model
    finally:
        model.deleteLater()
        _flush()


def test_home_card_follows_the_notice(cards: module_model.ModuleListModel) -> None:
    assert cards.cardMap("throttle")["cantSendCount"] == 0
    told: list[int] = []
    cards.cantSendChanged.connect(lambda: told.append(1))
    cards.found[:] = [_binding(2), _binding(3)]  # type: ignore[attr-defined]
    signal.cantSendChanged.emit()
    card = cards.cardMap("throttle")
    assert card["cantSendCount"] == 2
    assert card["cantSendTip"].startswith("Button 2 (Default) → ")
    # The card list's own signal (StatusPage) still says so.
    assert told == [1]
    cards.found[:] = []  # type: ignore[attr-defined]
    signal.cantSendChanged.emit()
    assert cards.cardMap("throttle")["cantSendCount"] == 0
    assert told == [1, 1]


def test_deleted_card_list_drops_the_notice_connection(qtbot) -> None:  # noqa: ANN001
    # A first list may make program-wide helpers: make one before counting.
    first = module_model.ModuleListModel()
    first.deleteLater()
    del first
    _flush()
    before = signal.receivers(_NOTICE)
    model = module_model.ModuleListModel()
    assert signal.receivers(_NOTICE) > before
    model.deleteLater()
    del model
    _flush()
    assert signal.receivers(_NOTICE) <= before

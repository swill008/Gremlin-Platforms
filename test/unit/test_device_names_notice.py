# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""D-01-OWNER-NOTICES (3a): every place that shows a device's name follows
the one "device names changed" notice (signal.deviceNamesChanged, sent by
gremlin.device_aliases): the Device Library rows, the input labels in the
editors (InputIdentifier.label), the device strip (DeviceListModel) and the
DeviceNames relay QML binds to. The tests send the notice themselves, as
device_aliases does after a rename, a forget or a History restore."""

from __future__ import annotations

import importlib.util
import pathlib
import uuid
from collections.abc import Iterator

import pytest
from pytestqt.qtbot import QtBot
from shiboken6 import Shiboken

from gremlin.signal import signal

_HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "device_library_LU_fake_smoke", _HERE / "device_library_LU_fake_smoke.py"
)
assert _spec and _spec.loader
fake_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_mod)

_GUID = uuid.UUID("5DA7C1B0-0000-0000-0000-000000000001")


@pytest.fixture
def aliases(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """The user's device names kept in memory (no settings file)."""
    from gremlin import device_aliases

    saved: dict[str, str] = {}

    def _save(names: dict[str, str]) -> None:
        saved.clear()
        saved.update(names)

    monkeypatch.setattr(device_aliases, "_load", lambda: dict(saved))
    monkeypatch.setattr(device_aliases, "_save", _save)
    yield saved


def _release(obj: object) -> None:
    if Shiboken.isValid(obj):
        Shiboken.delete(obj)


def test_the_device_library_rows_follow_a_rename(qtbot: QtBot) -> None:
    """A rename while the Library is open shows the new name (it used to
    wait for a device change)."""
    from gremlin.ui.device_library_model import DeviceLibraryModel

    lib = fake_mod.FakeLibrary()
    model = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    try:
        model.refresh()
        key = lib.devs[0]["key"]
        old = lib.devs[0]["name"]
        assert any(r.get("key") == key and r["name"] == old for r in model.rows)
        # The Library reads the user's name (device_library.devices ->
        # device_names.display_name): renamed there, then announced.
        lib.devs[0]["name"] = "Renamed throttle"
        with qtbot.waitSignal(model.changed, timeout=2000):
            signal.deviceNamesChanged.emit()
        names = [r["name"] for r in model.rows if r.get("key") == key]
        assert names == ["Renamed throttle"]
    finally:
        _release(model)


def test_an_input_label_follows_a_rename(
    qtbot: QtBot, aliases: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Logical Device selector and the Macro, Condition and Script
    editors show InputIdentifier.label: a rename tells QML to read it again."""
    from gremlin import device_aliases, device_initialization
    from gremlin.types import InputType
    from gremlin.ui.device import InputIdentifier

    monkeypatch.setattr(device_initialization, "shown_name", lambda uid: "Stick")
    ident = InputIdentifier(_GUID, InputType.JoystickButton, 3)
    try:
        assert ident.label == "Stick - Button 3"
        device_aliases.set_alias(str(_GUID), "Left throttle")
        with qtbot.waitSignal(ident.changed, timeout=2000):
            signal.deviceNamesChanged.emit()
        assert ident.label == "Left throttle - Button 3"
        # Forget drops the name; its notice brings the device's own back.
        device_aliases.forget(lambda uid: True)
        with qtbot.waitSignal(ident.changed, timeout=2000):
            signal.deviceNamesChanged.emit()
        assert ident.label == "Stick - Button 3"
    finally:
        _release(ident)


def test_the_device_strip_rereads_its_names(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DeviceListModel's names (twin names, vJoy numbers) are read again on
    the notice; the list itself is not rebuilt."""
    from PySide6 import QtCore

    from gremlin import device_initialization
    from gremlin.ui.device import DeviceListModel

    device_initialization.joystick_devices_initialization()
    model = DeviceListModel()
    try:
        model._change_device_type("all")
        if model.rowCount() == 0:
            pytest.skip("the fake hardware lists no devices")
        name_role = QtCore.Qt.ItemDataRole.UserRole + 1
        with qtbot.assertNotEmitted(model.modelReset):
            with qtbot.waitSignal(model.dataChanged, timeout=2000) as blocker:
                signal.deviceNamesChanged.emit()
        first, last, roles = blocker.args
        assert first.row() == 0 and last.row() == model.rowCount() - 1
        assert name_role in roles
    finally:
        _release(model)


def test_device_names_relays_the_one_notice(
    qtbot: QtBot, aliases: dict[str, str]
) -> None:
    """DeviceNames.changed (the strip and the Device Mapping Editor bind to it) is the
    owner's notice, forget included; no list of its own."""
    from gremlin import device_aliases
    from gremlin.ui import device_names

    first = device_names.DeviceNames()
    second = device_names.DeviceNames()
    try:
        device_aliases.set_alias(str(_GUID), "Left throttle")
        device_aliases.forget(lambda uid: True)
        with qtbot.waitSignals([first.changed, second.changed], timeout=2000):
            signal.deviceNamesChanged.emit()
        assert not hasattr(device_names, "_renamed")
    finally:
        _release(first)
        _release(second)

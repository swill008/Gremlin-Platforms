# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device and the OSC device model keep one InputIdentifier per input
(memory-qml-factory question 5a): opening the action pane again reuses it
instead of adding another child to the model each time, and the one the
backend holds as the current input stays valid."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtQml
from shiboken6 import Shiboken

from gremlin import device_initialization, shared_state
from gremlin.osc import OscDevice
from gremlin.profile import Profile
from gremlin.ui.backend import UIState
from gremlin.ui.device import Device, InputIdentifier
from gremlin.ui.osc_device_model import OscDeviceManagementModel
from test.unit.conftest import get_fake_device_guid

# DeviceBindingsPage._noteCurrentInput, the real call: ask the device for
# the identifier and hand it to uiState.
_PAGE_QML = b"""
import QtQuick
import Gremlin.Device
import Gremlin.UI

Item {
    id: root
    readonly property QtObject device: ModelFactory.create("Device", root, {})
    function noteCurrentInput(index) {
        var ident = device.inputIdentifier(index)
        if (ident)
            uiState.setCurrentInput(ident, index)
    }
}
"""


def _identifiers(model: QtCore.QObject) -> list[InputIdentifier]:
    return [c for c in model.children() if isinstance(c, InputIdentifier)]


@pytest.fixture
def profile(qapp: object) -> Iterator[None]:
    saved = shared_state.current_profile
    shared_state.current_profile = Profile()
    device_initialization.joystick_devices_initialization()
    yield
    shared_state.current_profile = saved


def test_device_returns_the_same_identifier_per_input(profile: None) -> None:
    device = Device()
    device.guid = str(get_fake_device_guid(False))
    try:
        assert device.rowCount() > 2
        first = device.inputIdentifier(0)
        assert device.inputIdentifier(0) is first
        other = device.inputIdentifier(1)
        assert other is not first
        assert (other.input_type, other.input_id) != (
            first.input_type,
            first.input_id,
        )
        assert first.parent() is device
    finally:
        device.deleteLater()


def test_opening_the_pane_n_times_keeps_the_count(profile: None) -> None:
    """The real path: a QML page with a Device calls inputIdentifier and
    hands it to uiState, as DeviceBindingsPage does on every pane open."""
    engine = QtQml.QQmlEngine()
    ui_state = UIState()
    engine.rootContext().setContextProperty("uiState", ui_state)
    component = QtQml.QQmlComponent(engine)
    component.setData(_PAGE_QML, QtCore.QUrl())
    page = component.create()
    assert page is not None, component.errorString()
    try:
        device = page.property("device")
        device.guid = str(get_fake_device_guid(False))
        rows = device.rowCount()
        assert rows > 2
        for index in range(3):
            page.noteCurrentInput(index)
        count = len(_identifiers(device))
        for _ in range(20):
            for index in range(3):
                page.noteCurrentInput(index)
        assert len(_identifiers(device)) == count

        held, index = ui_state._current_input[device._device.device_guid.uuid]
        assert index == 2
        assert Shiboken.isValid(held)
        assert held.isValid
        assert held is device.inputIdentifier(2)
    finally:
        page.deleteLater()
        engine.deleteLater()
        ui_state.deleteLater()


def test_held_identifier_survives_a_device_switch(profile: None) -> None:
    """The backend keeps one current input per device: switching away and
    back must not leave it holding a freed identifier."""
    ui_state = UIState()
    device = Device()
    real = str(get_fake_device_guid(False))
    virtual = str(get_fake_device_guid(True))
    try:
        device.guid = real
        held = device.inputIdentifier(1)
        ui_state.setCurrentInput(held, 1)
        device.guid = virtual
        device.inputIdentifier(1)
        device.guid = real
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        assert Shiboken.isValid(held)
        assert device.inputIdentifier(1) is held
    finally:
        device.deleteLater()
        ui_state.deleteLater()


def test_osc_model_returns_the_same_identifier(qapp: object) -> None:
    from gremlin.ui import osc_device_model

    OscDevice().rows.reset()
    saved = shared_state.current_profile
    shared_state.current_profile = Profile()
    model = OscDeviceManagementModel()
    try:
        row, error = osc_device_model.add_input({"address": "/a"})
        assert row is not None and not error, error
        assert model.rowCount() >= 1
        first = model.inputIdentifier(0)
        assert first.isValid
        count = len(_identifiers(model))
        for _ in range(20):
            assert model.inputIdentifier(0) is first
            model.inputIdentifier(-1)
            model.inputIdentifier(99)
        assert len(_identifiers(model)) == count + 1  # one shared empty one
    finally:
        model.deleteLater()
        OscDevice().rows.reset()
        shared_state.current_profile = saved

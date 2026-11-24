# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""LogicalDeviceSelector reports the user's pick as logicalInputSelected and
never writes its own logicalInputIdentifier (as upstream's Kobold control),
so an outside binding such as `logicalInputIdentifier: modelData.x` stays
in place after a pick and later outside changes still reach the selector.

Spec: 06 section 10 (Logical Device picker).
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtGui, QtQml

from gremlin.logical_device import LogicalDevice
from gremlin.types import InputType

ROOT = pathlib.Path(__file__).resolve().parents[2]

_HOST = b"""
import QtQuick

Item {
    id: host
    property var value: null
    property var picked: null
    property int pickCount: 0

    LogicalDeviceSelector {
        id: _sel
        objectName: "sel"
        validTypes: ["button"]
        logicalInputIdentifier: host.value
        onLogicalInputSelected: (identifier) => {
            host.picked = identifier
            host.pickCount += 1
        }
    }
    function selector() { return _sel }
}
"""


@pytest.fixture
def buttons(qapp: object) -> Iterator[list]:
    if not isinstance(QtCore.QCoreApplication.instance(), QtGui.QGuiApplication):
        # A file that made a plain QCoreApplication at import ran first;
        # Qt Quick items crash without a GUI app.
        pytest.skip("needs a QGuiApplication (another file made a QCoreApplication)")
    device = LogicalDevice()
    device.reset()
    made = [device.create(InputType.JoystickButton) for _ in range(3)]
    yield made
    device.reset()


def _identifier(control: object) -> object:
    from gremlin.ui.device import InputIdentifier

    return InputIdentifier(
        LogicalDevice().device_guid,
        control.type,  # type: ignore[attr-defined]
        control.id,  # type: ignore[attr-defined]
    )


def test_pick_is_a_signal_and_the_outside_binding_survives(buttons: list) -> None:
    import gremlin.ui.device  # noqa: F401  (registers Gremlin.Device)
    import gremlin.ui.model_factory  # noqa: F401  (registers ModelFactory)

    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    engine = QtQml.QQmlEngine()
    engine.addImportPath(str(ROOT / "theme"))
    engine.addImportPath(str(ROOT / "qml"))
    component = QtQml.QQmlComponent(engine)
    component.setData(_HOST, QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "_Host.qml")))
    held = [_identifier(c) for c in buttons]
    host = component.create()
    assert host is not None, component.errorString()
    try:
        selector = host.findChild(QtCore.QObject, "sel")
        assert selector is not None
        model = selector.findChild(gremlin.ui.device.LogicalDeviceSelectorModel)
        assert model is not None

        host.setProperty("value", held[0])
        assert model.property("currentIndex") == 0
        assert host.property("pickCount") == 1  # reported like any selection

        # The user picks the third button (the combo box's onActivated).
        model.setProperty("currentIndex", 2)
        picked = host.property("picked")
        assert (picked.input_type, picked.input_id) == (
            buttons[2].type,
            buttons[2].id,
        )
        # The selector didn't overwrite its own bound property.
        assert selector.property("logicalInputIdentifier") is held[0]

        # The outside value changes: the binding still carries it in.
        host.setProperty("value", held[1])
        assert selector.property("logicalInputIdentifier") is held[1]
        assert model.property("currentIndex") == 1
    finally:
        host.deleteLater()
        engine.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

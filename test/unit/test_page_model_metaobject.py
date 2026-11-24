# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The list pages' models keep one QMetaObject per type (gap
PYSIDE-METAOBJECT, program map page 01).

A signal connected to a plain method (no ``@QtCore.Slot``) of a Python
QObject gives that one object its own QMetaObject: PySide adds the method
as a dynamic slot. QML keeps the property cache it built for a QMetaObject
by its address. A page's model is freed with the page (ModelFactory), its
QMetaObject goes with it, and the next model's can be made at the same
address; QML then reads the new model through the old one's members:
"kindAt is not a function", properties undefined, Connections with no
signal (journey 11 under load, CI run 45320393185).

A decorated slot that a subclass overrides is no fix: PySide then keeps the
connection after the object is deleted, so each model here also drops every
gremlin.signal connection when it is deleted.

Spec: none (no behaviour change; the pages work as specified).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin import shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.ui.hardware_layout import HardwareLayoutModel
from gremlin.ui.keyboard_layout import KeyboardLayoutModel
from gremlin.ui.logical_layout import LogicalLayoutModel
from gremlin.ui.osc_device_model import OscDeviceManagementModel
from gremlin.ui.osc_layout import OscLayoutModel
from test.unit.metaobject_helper import (
    broken_static_metaobjects,
    metaobject_addresses,
    receivers,
    static_address,
)

MODELS: dict[str, Callable[[QtCore.QObject], QtCore.QObject]] = {
    "HardwareLayoutModel": HardwareLayoutModel,
    "KeyboardLayoutModel": KeyboardLayoutModel,
    "LogicalLayoutModel": LogicalLayoutModel,
    "OscLayoutModel": OscLayoutModel,
    "OscDeviceManagementModel": OscDeviceManagementModel,
}


@pytest.fixture
def isolated(
    qapp: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    LogicalDevice().load_dict({"controls": [], "groups": []})
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    yield
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    LogicalDevice().load_dict({"controls": [], "groups": []})


def _receivers() -> dict[str, int]:
    return receivers([("signal", signal)])


@pytest.fixture(scope="module", autouse=True)
def static_metaobjects_still_work() -> Iterator[None]:
    # Nothing here may leave a measured type's staticMetaObject deleted for
    # the tests that run after this module (see metaobject_helper).
    yield
    assert broken_static_metaobjects(MODELS.values()) == []


@pytest.mark.parametrize("name", sorted(MODELS))
def test_one_metaobject_per_type(isolated: None, name: str) -> None:
    # No parent: see metaobject_helper.
    addresses = metaobject_addresses(MODELS[name])
    assert addresses == {static_address(MODELS[name])}, (
        f"{name}: a signal is connected to a method without @QtCore.Slot"
    )


@pytest.mark.parametrize("name", sorted(MODELS))
def test_deleted_model_drops_its_connections(isolated: None, name: str) -> None:
    before = _receivers()
    host = QtCore.QObject()
    model = MODELS[name](host)
    assert _receivers() != before
    shiboken6.delete(host)
    assert not shiboken6.isValid(model)
    after = _receivers()
    grew = {k: after[k] - before[k] for k in after if after[k] != before[k]}
    assert grew == {}, f"{name}: connections kept after delete"

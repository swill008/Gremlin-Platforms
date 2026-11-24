# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The device models keep one QMetaObject per type (gap PYSIDE-METAOBJECT,
program map page 01).

A signal connected to a plain method (no ``@QtCore.Slot``) gives that one
object its own QMetaObject; QML caches a type's members by its QMetaObject
address, and a freed model's address can be reused by the next one (see
test_page_model_metaobject). A deleted model must also leave no connection
behind on gremlin.signal or the EventListener.

Spec: none (no behaviour change).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin import event_handler
from gremlin.signal import signal
from gremlin.ui.device import (
    AxisCalibration,
    Device,
    DeviceAxisSeries,
    DeviceListModel,
    LogicalDeviceSelectorModel,
)
from test.unit.metaobject_helper import (
    broken_static_metaobjects,
    metaobject_addresses,
    receivers,
    static_address,
)

MODELS: dict[str, Callable[[QtCore.QObject | None], QtCore.QObject]] = {
    "AxisCalibration": AxisCalibration,
    "Device": Device,
    "DeviceAxisSeries": DeviceAxisSeries,
    "DeviceListModel": DeviceListModel,
    "LogicalDeviceSelectorModel": LogicalDeviceSelectorModel,
}


@pytest.fixture
def host(qapp: object) -> Iterator[QtCore.QObject]:
    obj = QtCore.QObject()
    yield obj
    if shiboken6.isValid(obj):
        shiboken6.delete(obj)


def _receivers() -> dict[str, int]:
    return receivers(
        [
            ("signal", signal),
            ("listener", event_handler.EventListener()),
        ]
    )


@pytest.fixture(scope="module", autouse=True)
def static_metaobjects_still_work() -> Iterator[None]:
    # Nothing here may leave a measured type's staticMetaObject deleted for
    # the tests that run after this module (see metaobject_helper).
    yield
    assert broken_static_metaobjects(MODELS.values()) == []


@pytest.mark.parametrize("name", sorted(MODELS))
def test_one_metaobject_per_type(qapp: object, name: str) -> None:
    # No parent: see metaobject_helper.
    addresses = metaobject_addresses(MODELS[name])
    assert addresses == {static_address(MODELS[name])}, (
        f"{name}: a signal is connected to a method without @QtCore.Slot"
    )


@pytest.mark.parametrize("name", sorted(MODELS))
def test_deleted_model_drops_its_connections(host: QtCore.QObject, name: str) -> None:
    before = _receivers()
    model = MODELS[name](host)
    assert _receivers() != before
    shiboken6.delete(host)
    assert not shiboken6.isValid(model)
    after = _receivers()
    grew = {k: after[k] - before[k] for k in after if after[k] != before[k]}
    assert grew == {}, f"{name}: connections kept after delete"

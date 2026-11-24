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

import gc
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


def _metaobject(obj: QtCore.QObject) -> int:
    return shiboken6.getCppPointer(obj.metaObject())[0]


def _receivers() -> dict[str, int]:
    out: dict[str, int] = {}
    for name, source in (
        ("signal", signal),
        ("listener", event_handler.EventListener()),
    ):
        meta = source.metaObject()
        for i in range(meta.methodOffset(), meta.methodCount()):
            method = meta.method(i)
            if method.methodType() == QtCore.QMetaMethod.MethodType.Signal:
                sig = bytes(method.methodSignature().data()).decode()
                out[f"{name}.{sig}"] = source.receivers(QtCore.SIGNAL(sig))
    return out


@pytest.mark.parametrize("name", sorted(MODELS))
def test_one_metaobject_per_type(qapp: object, name: str) -> None:
    # No parent here: metaObject() on a parented object, then deleting the
    # parent from C++, leaves the class's staticMetaObject wrapper deleted
    # for the rest of the run (PySide 6.11.2); Python freeing it does not.
    objects = [MODELS[name](None) for _ in range(3)]
    addresses = {_metaobject(obj) for obj in objects}
    del objects
    gc.collect()
    assert len(addresses) == 1, (
        f"{name}: a signal is connected to a method without @QtCore.Slot"
    )
    assert MODELS[name].staticMetaObject.className() == name


@pytest.mark.parametrize("name", sorted(MODELS))
def test_deleted_model_drops_its_connections(
    host: QtCore.QObject, name: str
) -> None:
    before = _receivers()
    model = MODELS[name](host)
    assert _receivers() != before
    shiboken6.delete(host)
    assert not shiboken6.isValid(model)
    after = _receivers()
    grew = {k: after[k] - before[k] for k in after if after[k] != before[k]}
    assert grew == {}, f"{name}: connections kept after delete"

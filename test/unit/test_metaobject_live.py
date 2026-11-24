# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The live value objects keep one QMetaObject per type (gap
PYSIDE-METAOBJECT, program map page 01).

A signal (a timer's timeout included) connected to a plain method of a
Python QObject gives that one object its own QMetaObject; QML caches by
its address, so a freed object's address reused by a new one is read
through the old type. See test_page_model_metaobject.py.

Spec: none (no behaviour change).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin.signal import signal
from gremlin.ui.live_input import DeviceLiveState
from gremlin.ui.pair_live import PairLiveThrottle

TYPES: dict[str, Callable[[QtCore.QObject], QtCore.QObject]] = {
    "DeviceLiveState": DeviceLiveState,
    "PairLiveThrottle": PairLiveThrottle,
}


def _metaobject(obj: QtCore.QObject) -> int:
    return shiboken6.getCppPointer(obj.metaObject())[0]


def _receivers() -> dict[str, int]:
    meta = signal.metaObject()
    out: dict[str, int] = {}
    for i in range(meta.methodOffset(), meta.methodCount()):
        method = meta.method(i)
        if method.methodType() == QtCore.QMetaMethod.MethodType.Signal:
            sig = bytes(method.methodSignature().data()).decode()
            out[sig] = signal.receivers(QtCore.SIGNAL(sig))
    return out


@pytest.mark.parametrize("name", sorted(TYPES))
def test_one_metaobject_per_type(qapp: object, name: str) -> None:
    host = QtCore.QObject()
    try:
        objs = [TYPES[name](host) for _ in range(3)]
        addresses = {_metaobject(o) for o in objs}
        assert len(addresses) == 1, (
            f"{name}: a signal is connected to a method without @QtCore.Slot"
        )
    finally:
        shiboken6.delete(host)


@pytest.mark.parametrize("name", sorted(TYPES))
def test_deleted_object_drops_its_connections(qapp: object, name: str) -> None:
    before = _receivers()
    host = QtCore.QObject()
    obj = TYPES[name](host)
    shiboken6.delete(host)
    assert not shiboken6.isValid(obj)
    after = _receivers()
    grew = {k: after[k] - before[k] for k in after if after[k] != before[k]}
    assert grew == {}, f"{name}: connections kept after delete"

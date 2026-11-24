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

from collections.abc import Callable, Iterator

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin.signal import signal
from gremlin.ui.live_input import DeviceLiveState
from gremlin.ui.pair_live import PairLiveThrottle
from test.unit.metaobject_helper import (
    broken_static_metaobjects,
    metaobject_addresses,
    receivers,
    static_address,
)

TYPES: dict[str, Callable[[QtCore.QObject], QtCore.QObject]] = {
    "DeviceLiveState": DeviceLiveState,
    "PairLiveThrottle": PairLiveThrottle,
}


def _receivers() -> dict[str, int]:
    return receivers([("signal", signal)])


@pytest.fixture(scope="module", autouse=True)
def static_metaobjects_still_work() -> Iterator[None]:
    # Nothing here may leave a measured type's staticMetaObject deleted for
    # the tests that run after this module (see metaobject_helper).
    yield
    assert broken_static_metaobjects(TYPES.values()) == []


@pytest.mark.parametrize("name", sorted(TYPES))
def test_one_metaobject_per_type(qapp: object, name: str) -> None:
    # No parent: see metaobject_helper.
    addresses = metaobject_addresses(TYPES[name])
    assert addresses == {static_address(TYPES[name])}, (
        f"{name}: a signal is connected to a method without @QtCore.Slot"
    )


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

# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Device Bindings models take their device-store listener with them when
they go: page switches don't pile up listeners, even while the store never
fires (memory probe, claude/audits/2026-11-24-upstream-since-fork/memory.md).

Spec: none (no behaviour change).
"""

from __future__ import annotations

import gc
from collections.abc import Iterator

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin.modules import store

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _flush() -> None:
    QtCore.QCoreApplication.sendPostedEvents(
        None, QtCore.QEvent.Type.DeferredDelete
    )
    QtCore.QCoreApplication.processEvents()
    gc.collect()


def test_deleted_models_leave_no_store_listeners() -> None:
    """Deleted as a page unload does (deleteLater)."""
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    before = len(store._pending_listeners)
    for _ in range(5):
        model = HardwareLayoutModel()
        model.deleteLater()
        _flush()
    del model
    _flush()
    assert len(store._pending_listeners) == before


def test_destroyed_cpp_object_leaves_no_store_listener() -> None:
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    before = len(store._pending_listeners)
    model = HardwareLayoutModel()
    assert len(store._pending_listeners) == before + 1
    shiboken6.delete(model)
    _flush()
    assert len(store._pending_listeners) == before


def test_a_live_model_keeps_its_listener() -> None:
    from gremlin.ui.hardware_layout import HardwareLayoutModel

    before = len(store._pending_listeners)
    model = HardwareLayoutModel()
    _flush()
    assert len(store._pending_listeners) == before + 1
    model.deleteLater()
    _flush()

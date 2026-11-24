# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The module models keep one QMetaObject per type (gap PYSIDE-METAOBJECT,
program map page 01).

A signal connected to a plain method (no ``@QtCore.Slot``) of a Python
QObject gives that one object its own QMetaObject. QML caches what it read
from a QMetaObject by address; a freed model's address can be reused by the
next one, which QML then reads through the old type ("X is not a function").
See test_page_model_metaobject.py for the page models.

Covers DriverInputModel, ModuleListModel (module_model.py) and
ModuleClaimedInputModel (module_inputs.py), made with a parent as the
ModelFactory makes them.

Spec: none (no behaviour change; the pages work as specified).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import shiboken6
from PySide6 import QtCore

from gremlin import event_handler, shared_state
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.ui.module_inputs import ModuleClaimedInputModel
from gremlin.ui.module_model import DriverInputModel, ModuleListModel

MODELS: dict[str, Callable[[QtCore.QObject], QtCore.QObject]] = {
    "DriverInputModel": DriverInputModel,
    "ModuleListModel": ModuleListModel,
    "ModuleClaimedInputModel": ModuleClaimedInputModel,
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
    yield


def _metaobject(obj: QtCore.QObject) -> int:
    return shiboken6.getCppPointer(obj.metaObject())[0]


def _receivers() -> dict[str, int]:
    out: dict[str, int] = {}
    owners = (("signal", signal), ("listener", event_handler.EventListener()))
    for name, owner in owners:
        meta = owner.metaObject()
        for i in range(meta.methodOffset(), meta.methodCount()):
            method = meta.method(i)
            if method.methodType() == QtCore.QMetaMethod.MethodType.Signal:
                sig = bytes(method.methodSignature().data()).decode()
                out[f"{name}.{sig}"] = owner.receivers(QtCore.SIGNAL(sig))
    return out


def _make_and_delete(name: str) -> None:
    host = QtCore.QObject()
    MODELS[name](host)
    shiboken6.delete(host)


@pytest.mark.parametrize("name", sorted(MODELS))
def test_one_metaobject_per_type(isolated: None, name: str) -> None:
    host = QtCore.QObject()
    try:
        made = [MODELS[name](host) for _ in range(3)]
        addresses = {_metaobject(m) for m in made}
        assert len(addresses) == 1, (
            f"{name}: a signal is connected to a method without @QtCore.Slot"
        )
    finally:
        shiboken6.delete(host)


@pytest.mark.parametrize("name", sorted(MODELS))
def test_deleted_model_drops_its_connections(isolated: None, name: str) -> None:
    # A first model may make program-wide helpers that stay connected for
    # the whole process: make one before counting.
    _make_and_delete(name)
    before = _receivers()
    host = QtCore.QObject()
    model = MODELS[name](host)
    assert _receivers() != before
    shiboken6.delete(host)
    assert not shiboken6.isValid(model)
    after = _receivers()
    grew = {k: after[k] - before[k] for k in after if after[k] > before[k]}
    assert grew == {}, f"{name}: connections kept after delete"

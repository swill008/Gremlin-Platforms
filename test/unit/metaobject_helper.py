# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Reading QMetaObjects in tests without breaking later ones (gap
PYSIDE-METAOBJECT, program map page 01).

PySide 6.11.2: ``obj.metaObject()`` read from Python on an object that a
C++ parent later deletes leaves the class's ``staticMetaObject`` wrapper
deleted for the rest of the process ("Internal C++ object
(PySide6.QtCore.QMetaObject) already deleted") when the object's meta
object is the class's own, as it is for a type whose connected methods are
all ``@QtCore.Slot``. An object with no parent, deleted directly or freed
by Python, leaves it working, as does reading ``type(obj).staticMetaObject``
(checked with a script, 2026-11-23).
"""

from __future__ import annotations

import gc
from collections.abc import Callable, Iterable
from typing import Any

import shiboken6
from PySide6 import QtCore


def metaobject_addresses(
    make: Callable[..., QtCore.QObject], count: int = 3
) -> set[int]:
    """The QMetaObject addresses of ``count`` objects made with no parent,
    each deleted afterwards."""
    objects = [make(None) for _ in range(count)]
    try:
        return {shiboken6.getCppPointer(o.metaObject())[0] for o in objects}
    finally:
        for obj in objects:
            if shiboken6.isValid(obj):
                shiboken6.delete(obj)
        del objects
        gc.collect()


def static_address(cls: Any) -> int:  # noqa: ANN401
    return shiboken6.getCppPointer(cls.staticMetaObject)[0]


def receivers(owners: Iterable[tuple[str, QtCore.QObject]]) -> dict[str, int]:
    """Connection counts of every signal the owners declare, read through
    the class's meta object."""
    out: dict[str, int] = {}
    for name, owner in owners:
        meta = type(owner).staticMetaObject
        for i in range(meta.methodOffset(), meta.methodCount()):
            method = meta.method(i)
            if method.methodType() == QtCore.QMetaMethod.MethodType.Signal:
                sig = bytes(method.methodSignature().data()).decode()
                out[f"{name}.{sig}"] = owner.receivers(QtCore.SIGNAL(sig))
    return out


def broken_static_metaobjects(types: Iterable[Any]) -> list[str]:
    """Names of the types whose staticMetaObject no longer works."""
    broken = []
    for cls in types:
        try:
            cls.staticMetaObject.className()
        except RuntimeError:
            broken.append(cls.__name__)
    return broken

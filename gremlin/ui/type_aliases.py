# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys
from typing import (
    TypeVar,
    cast,
)

from PySide6 import (
    QtCore,
    QtQml,
)

T = TypeVar("T")

# Every ta.QmlElement type by its QML name: what ModelFactory.create makes.
QML_TYPES: dict[str, type] = {}
# Names two different classes registered; ModelFactory refuses them.
QML_AMBIGUOUS: set[str] = set()


def QmlElement(cls: type[T]) -> type[T]:
    """Type-preserving QML element registration decorator.

    Replacement for the @QtQml.QmlElement decorator which breaks type
    annotations. Records the type for ModelFactory; a type on
    model_factory.FACTORY_ONLY is registered uncreatable in QML.
    """
    from gremlin.ui import model_factory

    frame = sys._getframe(1)
    uri = frame.f_globals["QML_IMPORT_NAME"]
    major = frame.f_globals.get("QML_IMPORT_MAJOR_VERSION", 1)
    minor = frame.f_globals.get("QML_IMPORT_MINOR_VERSION", 0)
    name = cls.__name__
    if name in model_factory.FACTORY_ONLY:
        QtQml.qmlRegisterUncreatableType(
            cls,
            uri,
            major,
            minor,
            # The stubs say bytes; PySide6 6.11 accepts only str here.
            name,  # pyright: ignore[reportArgumentType]
            model_factory.UNCREATABLE_REASON.format(name=name),  # pyright: ignore[reportArgumentType]
        )
    else:
        QtQml.qmlRegisterType(cls, uri, major, minor, name)
    known = QML_TYPES.get(name)
    same = known is None or (known.__module__, known.__qualname__) == (
        cls.__module__,
        cls.__qualname__,
    )
    if not same or name in QML_AMBIGUOUS:
        QML_AMBIGUOUS.add(name)
        QML_TYPES.pop(name, None)
    else:
        QML_TYPES[name] = cls
    return cast(type[T], cls)


MI = QtCore.QModelIndex
PMI = QtCore.QPersistentModelIndex
OQO = QtCore.QObject | None
ModelIndex = MI | PMI

# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The program reads no object's QMetaObject from Python where the object's
C++ parent deletes it later (gap PYSIDE-METAOBJECT, program map page 01).

PySide 6.11.2: ``obj.metaObject()`` returns the class's own QMetaObject for
a type with no dynamic slots; when a C++ parent then deletes the object,
the class's ``staticMetaObject`` wrapper is left deleted for the rest of
the process (see metaobject_helper). A QML item is a child of its window.
ActionModel._report_edits still reads self.metaObject(): reading
type(self).staticMetaObject there instead broke the action editor matrix
(superClass() of an already-deleted wrapper; full run 2026-11-23 23:12),
so that call stays as it was (gap PYSIDE-METAOBJECT).

Spec: none (no behaviour change).
"""

from __future__ import annotations

import gc
import uuid
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore, QtQml, QtQuick

from gremlin.ui import control_windows
from test.unit.metaobject_helper import broken_static_metaobjects

_GUID = uuid.UUID("{99999999-2222-3333-4444-555555555555}")


def _delete_later(obj: QtCore.QObject) -> None:
    obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


# --- control API window calls ------------------------------------------------

_QML = b"""
import QtQuick
import QtQuick.Controls.Basic
Window {
    visible: false
    width: 200; height: 200
    property int clicks: 0
    property int argClicks: 0
    Column {
        Button { objectName: "button"; text: "B"; onClicked: clicks += 1 }
        Item { objectName: "bare"; width: 10; height: 10 }
        Item {
            objectName: "argClick"; width: 10; height: 10
            function click(a) { argClicks += 1 }
        }
        TextField { objectName: "field"; text: "x" }
    }
}
"""


_components: list[QtQml.QQmlComponent] = []


def _make_window(engine: QtQml.QQmlEngine) -> QtCore.QObject:
    component = QtQml.QQmlComponent(engine)
    component.setData(_QML, QtCore.QUrl("file:///meta_safe.qml"))
    win = component.create()
    assert win is not None, component.errors()
    # The test deletes it, not the JavaScript collector.
    QtQml.QQmlEngine.setObjectOwnership(
        win, QtQml.QQmlEngine.ObjectOwnership.CppOwnership
    )
    _components.append(component)
    return win


@pytest.fixture
def engine(qapp: object) -> Iterator[QtQml.QQmlEngine]:
    engine = QtQml.QQmlEngine()
    yield engine
    _delete_later(engine)


@pytest.fixture
def window(engine: QtQml.QQmlEngine) -> Iterator[QtCore.QObject]:
    win = _make_window(engine)
    yield win
    _delete_later(win)


def _item(win: QtCore.QObject, name: str) -> QtQuick.QQuickItem:
    item = win.findChild(QtQuick.QQuickItem, name)
    assert item is not None, name
    return item


def _twice_then_closed(
    engine: QtQml.QQmlEngine, act: Callable[[QtQuick.QQuickItem], object]
) -> list[str]:
    """``act`` on a plain Item (its meta object is QQuickItem's own) in two
    windows, both deleted after; then the types whose staticMetaObject is
    broken."""
    QtQuick.QQuickItem.staticMetaObject.className()
    windows = [_make_window(engine) for _ in range(2)]
    for win in windows:
        act(_item(win, "bare"))
    for win in windows:
        _delete_later(win)
    del win, windows
    gc.collect()
    return broken_static_metaobjects([QtQuick.QQuickItem])


def test_a_click_leaves_the_item_meta_object_working(
    engine: QtQml.QQmlEngine,
) -> None:
    assert _twice_then_closed(engine, control_windows._click) == []


def test_a_click_still_calls_click_only_when_it_takes_no_arguments(
    window: QtCore.QObject,
) -> None:
    control_windows._click(_item(window, "button"))
    assert window.property("clicks") == 1
    # click(a) is not click(): the item gets a mouse press instead.
    control_windows._click(_item(window, "argClick"))
    assert window.property("argClicks") == 0


def test_typing_still_finishes_the_edit(window: QtCore.QObject) -> None:
    field = _item(window, "field")
    finished: list[int] = []
    field.editingFinished.connect(lambda: finished.append(1))  # type: ignore[attr-defined]
    assert control_windows._type_into(field, "abc")
    assert field.property("text") == "abc"
    assert finished

# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""ModelFactory (claude/plans/memory-qml-factory.md): QML-made Python objects
are built in Python, parented to their QML item and freed with it."""

from __future__ import annotations

import gc
import threading
import weakref
from collections.abc import Iterator

import pytest
import shiboken6
from PySide6 import QtCore, QtQml

import gremlin.ui.profile  # noqa: F401  # Gremlin.Profile for the QML snippets
from gremlin import threads
from gremlin.ui import model_factory
from gremlin.ui import type_aliases as ta

QML_IMPORT_NAME = "Gremlin.FactoryTest"
QML_IMPORT_MAJOR_VERSION = 1

# Every FactoryProbe made, weakly: finding them with findChildren would itself
# keep the wrapper (PySide records the found children on the caller).
_made: list[weakref.ref[FactoryProbe]] = []


@ta.QmlElement
class FactoryProbe(QtCore.QObject):
    """Records the order its properties are set in."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        _made.append(weakref.ref(self))
        self.order: list[str] = []
        self._a = ""
        self._b = 0

    def _set_a(self, value: str) -> None:
        self.order.append("a")
        self._a = value

    def _set_b(self, value: int) -> None:
        self.order.append("b")
        self._b = value

    a = QtCore.Property(str, lambda self: self._a, _set_a, notify=changed)
    b = QtCore.Property(int, lambda self: self._b, _set_b, notify=changed)


def _load(
    engine: QtQml.QQmlEngine, body: str
) -> tuple[QtQml.QQmlComponent, QtCore.QObject | None]:
    component = QtQml.QQmlComponent(engine)
    imports = ("QtQuick", "Gremlin.UI", "Gremlin.Profile", "Gremlin.FactoryTest")
    source = "".join(f"import {name}\n" for name in imports) + body + "\n"
    component.setData(source.encode(), QtCore.QUrl("factory_test.qml"))
    return component, component.create()


@pytest.fixture
def engine(qapp: object) -> Iterator[QtQml.QQmlEngine]:
    eng = QtQml.QQmlEngine()
    yield eng
    eng.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def _destroy(obj: QtCore.QObject) -> None:
    obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()


def test_registry_holds_qml_element_types(qapp: object) -> None:
    assert ta.QML_TYPES["FactoryProbe"] is FactoryProbe
    assert "ModeListModel" in ta.QML_TYPES


def test_qml_create_parents_to_item(engine: QtQml.QQmlEngine) -> None:
    component, root = _load(
        engine,
        "Item { id: _root\n"
        "  readonly property ModeListModel _modes:\n"
        '    ModelFactory.create("ModeListModel", _root, {})\n'
        "  readonly property bool made: _modes !== null }",
    )
    assert root is not None, [e.toString() for e in component.errors()]
    assert root.property("made") is True
    made = root.findChildren(gremlin.ui.profile.ModeListModel)
    assert len(made) == 1 and made[0].parent() is root
    assert (
        QtQml.QQmlEngine.objectOwnership(made[0])
        == QtQml.QQmlEngine.ObjectOwnership.CppOwnership
    )
    _destroy(root)


def test_freed_with_item_no_shell_left(engine: QtQml.QQmlEngine) -> None:
    component, root = _load(
        engine,
        "Item { id: _root\n"
        "  readonly property FactoryProbe _p:\n"
        '    ModelFactory.create("FactoryProbe", _root, { a: "x" }) }',
    )
    assert root is not None, [e.toString() for e in component.errors()]
    gone = _made[-1]
    held = gone()
    assert held is not None and held.parent() is root
    _destroy(root)
    # The C++ object went with the item...
    assert not shiboken6.isValid(held)
    # ...and nothing in Python keeps the wrapper (its __dict__) alive.
    del held
    gc.collect()
    assert gone() is None


@pytest.mark.parametrize(
    ("literal", "order"),
    [('{ b: 2, a: "x" }', ["b", "a"]), ('{ a: "x", b: 2 }', ["a", "b"])],
)
def test_props_set_in_literal_order(
    engine: QtQml.QQmlEngine, literal: str, order: list[str]
) -> None:
    component, root = _load(
        engine,
        "Item { id: _root\n"
        "  readonly property FactoryProbe _p:\n"
        f'    ModelFactory.create("FactoryProbe", _root, {literal}) }}',
    )
    assert root is not None, [e.toString() for e in component.errors()]
    probe = _made[-1]()
    assert probe is not None
    assert probe.order == order
    assert (probe.property("a"), probe.property("b")) == ("x", 2)
    _destroy(root)


def test_unknown_type_is_a_clear_error(engine: QtQml.QQmlEngine) -> None:
    item = QtCore.QObject()
    with pytest.raises(ValueError, match="unknown type 'NoSuchType'"):
        model_factory.make("NoSuchType", item)
    with pytest.raises(ValueError, match="no property 'nope'"):
        model_factory.make("FactoryProbe", item, {"nope": 1})
    with pytest.raises(ValueError, match="parent is required"):
        model_factory.make("FactoryProbe", None)
    assert item.findChildren(FactoryProbe) == []

    warnings: list[str] = []
    engine.warnings.connect(lambda errs: warnings.extend(e.toString() for e in errs))
    component, root = _load(
        engine,
        "Item { id: _root\n"
        '  readonly property var _x: ModelFactory.create("NoSuchType", _root)\n'
        "  readonly property bool isNull: _x === null || _x === undefined }",
    )
    assert root is not None, [e.toString() for e in component.errors()]
    assert root.property("isNull") is True
    assert any("unknown type 'NoSuchType'" in w for w in warnings), warnings
    _destroy(root)
    _destroy(item)


def test_off_main_thread_refused(qapp: object) -> None:
    result: list[BaseException] = []

    def call() -> None:
        try:
            model_factory.make("FactoryProbe", None)
        except BaseException as e:  # noqa: BLE001
            result.append(e)

    worker = threading.Thread(target=call, name="factory-test", daemon=True)
    worker.start()
    worker.join(timeout=5.0)
    assert not worker.is_alive()
    assert len(result) == 1 and isinstance(result[0], threads.WrongThread)


def test_factory_only_type_fails_at_qml_load(
    engine: QtQml.QQmlEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(model_factory, "FACTORY_ONLY", frozenset({"FactoryOnlyProbe"}))

    @ta.QmlElement
    class FactoryOnlyProbe(QtCore.QObject):
        pass

    component, root = _load(engine, "Item { FactoryOnlyProbe {} }")
    assert root is None
    assert any("made by ModelFactory" in e.toString() for e in component.errors())

    component, root = _load(
        engine,
        "Item { id: _root\n"
        "  readonly property FactoryOnlyProbe _p:\n"
        '    ModelFactory.create("FactoryOnlyProbe", _root) }',
    )
    assert root is not None, [e.toString() for e in component.errors()]
    assert len(root.findChildren(FactoryOnlyProbe)) == 1
    _destroy(root)

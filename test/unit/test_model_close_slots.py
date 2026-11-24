# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""QML reaches a Python object's method only through its meta-object: a
plain Python method called as `_model.close()` from QML does nothing (a
TypeError in the log at most). Health's and Search's close() weren't Slots,
so a closed Health window stayed on gremlin.health's listeners and a closed
Search window on SearchIndex's on_change, each keeping its model alive
(test_leaks.py's stage-2 rounds). Here: close() reached the way QML reaches
it unhooks both, DialogSearch.qml calls it on closing, and a guard that
every method QML calls on a ModelFactory-made object is in that type's
meta-object (Slot, signal or inherited Qt method)."""

from __future__ import annotations

import importlib
import pathlib
import re
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import health, search_index
from gremlin.ui import health_model
from gremlin.ui.health_model import HealthModel
from gremlin.ui.search_model import SearchModel

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _qml_call(obj: QtCore.QObject, name: str) -> bool:
    """name() the way QML calls it: through the meta-object."""
    return bool(QtCore.QMetaObject.invokeMethod(obj, name))


@pytest.fixture
def index(tmp_path: pathlib.Path) -> Iterator[search_index.SearchIndex]:
    made = search_index.SearchIndex(folder=tmp_path, library=False)
    yield made


def test_closing_health_removes_its_listener(
    qapp: object,
    index: search_index.SearchIndex,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_model, "_watching", True)
    health.attach(index)
    try:
        model = HealthModel(index=index)
        listener = model._health_changed_any_thread
        assert listener in health._listeners
        assert _qml_call(model, "close")
        assert listener not in health._listeners
        model.deleteLater()
    finally:
        health._reset_for_tests()


def test_closing_search_unhooks_the_index(
    qapp: object, index: search_index.SearchIndex
) -> None:
    model = SearchModel(index=index)
    assert index._on_change == model._index_changed_any_thread
    assert _qml_call(model, "close")
    assert index._on_change is None
    model.deleteLater()


def test_an_older_search_window_closing_keeps_the_newer_ones_hook(
    qapp: object, index: search_index.SearchIndex
) -> None:
    old = SearchModel(index=index)
    new = SearchModel(index=index)
    old.close()
    assert index._on_change == new._index_changed_any_thread
    new.close()
    old.deleteLater()
    new.deleteLater()


def test_the_search_window_closes_its_model() -> None:
    text = (_ROOT / "qml" / "DialogSearch.qml").read_text("utf-8")
    assert re.search(r"(?m)^\s*onClosing:\s*_model\.close\(\)", text)


# +-------------------------------------------------------------------------
# | Guard: methods QML calls on factory-made objects are meta-methods

_PY_FOLDERS = ("gremlin", "action_plugins", "theme")
_QML_FOLDERS = ("qml", "action_plugins", "theme")
_DECORATED = re.compile(r"@ta\.QmlElement\s*\n(?:\s*@.*\n)*\s*class\s+(\w+)")
_FACTORY_PROP = re.compile(
    r"property\s+[\w.]+\s+(\w+)\s*:\s*ModelFactory\.create\(\s*[\"'](\w+)[\"']"
)


def _modules() -> dict[str, str]:
    out: dict[str, str] = {}
    for folder in _PY_FOLDERS:
        for path in (_ROOT / folder).rglob("*.py"):
            text = path.read_text("utf-8", "replace")
            module = ".".join(path.relative_to(_ROOT).with_suffix("").parts)
            module = module.removesuffix(".__init__")
            for name in _DECORATED.findall(text):
                out[name] = module
    return out


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)//[^\"'\n]*$", "", text)


def _meta_names(cls: type) -> set[str]:
    meta = cls.staticMetaObject  # type: ignore[attr-defined]
    names = {
        bytes(meta.method(i).name().data()).decode()
        for i in range(meta.methodCount())
    }
    names |= {meta.property(i).name() for i in range(meta.propertyCount())}
    return names


def test_qml_calls_on_factory_objects_are_meta_methods() -> None:
    """`<id>.name(` in a QML file, where <id> is a property made by
    ModelFactory.create("Type"), and Type defines name as a plain Python
    method (not a Slot): QML can't call it."""
    modules = _modules()
    bad: list[str] = []
    for folder in _QML_FOLDERS:
        for path in sorted((_ROOT / folder).rglob("*.qml")):
            text = _strip_comments(path.read_text("utf-8", "replace"))
            for prop, type_name in _FACTORY_PROP.findall(text):
                if type_name not in modules:
                    continue
                cls = getattr(importlib.import_module(modules[type_name]), type_name)
                meta = _meta_names(cls)
                called = set(re.findall(rf"\b{re.escape(prop)}\.(\w+)\s*\(", text))
                for name in sorted(called):
                    attr = getattr(cls, name, None)
                    if callable(attr) and name not in meta:
                        rel = path.relative_to(_ROOT).as_posix()
                        bad.append(f"{rel}: {prop}.{name}() on {type_name}")
    assert bad == [], "not Slots, so QML can't call them:\n" + "\n".join(bad)

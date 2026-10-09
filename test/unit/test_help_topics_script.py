# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Help book must load: a syntax slip in any chapter leaves the Help
window empty (it failed to open after one, caught only by a window test).
qml/help/index.js joins the chapters; qml/help_topics.js keeps the old entry
points over it (01 S128)."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtQml

from test.unit import help_book

_QML = Path(__file__).resolve().parents[2] / "qml"
_LOADER = """
import QtQml
import "%s" as Book
import "%s" as Old
QtObject {
    property var chapters: Book.chapters()
    property var book: Book.topics("")
    property var buttonMap: Book.topics("button-map")
    property var found: Book.find(Book.topics("")[3].id)
    property var notFound: Book.find("no-such-topic")
    property int oldAll: Old.topics().length
    property int oldButtonMap: Old.buttonMapTopics().length
    property int oldLibrary: Old.deviceLibraryTopics().length
}
"""


def _load() -> QtCore.QObject:
    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine)
    component.setData(
        (_LOADER % ((_QML / "help" / "index.js").as_uri(),
                    (_QML / "help_topics.js").as_uri())).encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(_QML / "loader.qml")),
    )
    obj = component.create()
    assert obj is not None, component.errorString()
    obj.setParent(engine)
    engine.setParent(QtCore.QCoreApplication.instance())
    return obj


def _value(obj: QtCore.QObject, name: str) -> list[dict]:
    value = obj.property(name)
    return list(value.toVariant() if hasattr(value, "toVariant") else value)


def _one(obj: QtCore.QObject, name: str) -> dict | None:
    value = obj.property(name)
    value = value.toVariant() if hasattr(value, "toVariant") else value
    return None if value is None else dict(value)


# The engine needs the application object (pytest-qt's qapp).
def test_every_chapter_loads(qapp: QtCore.QCoreApplication) -> None:
    obj = _load()
    chapters = _value(obj, "chapters")
    assert len(chapters) == 9
    for chapter in chapters:
        assert help_book.chapter_topics(chapter["id"]), chapter["id"]


def test_topics_carry_their_chapter(qapp: QtCore.QCoreApplication) -> None:
    obj = _load()
    titles = {c["id"]: c["title"] for c in _value(obj, "chapters")}
    for topic in _value(obj, "book"):
        assert titles[topic["chapterId"]] == topic["chapter"]
    assert {t["chapterId"] for t in _value(obj, "buttonMap")} == {"button-map"}
    found = _one(obj, "found")
    assert found is not None
    assert found["id"] == _value(obj, "book")[3]["id"]
    assert _one(obj, "notFound") is None


def test_the_old_entry_points_read_the_book(qapp: QtCore.QCoreApplication) -> None:
    obj = _load()
    assert obj.property("oldAll") == len(_value(obj, "book")) > 10
    assert obj.property("oldButtonMap") == len(_value(obj, "buttonMap")) > 0
    assert obj.property("oldLibrary") == len(
        help_book.chapter_topics("device-library")) > 0

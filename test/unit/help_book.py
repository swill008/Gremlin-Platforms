# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Help book (qml/help/index.js, 01 S128) as the program loads it: the
QML engine imports index.js, which imports every chapter."""

from __future__ import annotations

import functools
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "qml" / "help" / "index.js"

_LOADER = """
import QtQml
import "%s" as Book
QtObject {
    property var chapters: Book.chapters()
    property var topics: Book.topics("")
}
"""


def _plain(value: object) -> list:
    if hasattr(value, "toVariant"):
        return value.toVariant()
    return list(value)  # type: ignore[call-overload]


@functools.lru_cache(maxsize=1)
def load() -> tuple[list[dict], list[dict]]:
    """(chapters, topics) of the whole book; needs a Qt application."""
    from PySide6 import QtCore, QtQml

    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine)
    component.setData(
        (_LOADER % INDEX.as_uri()).encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "help" / "loader.qml")),
    )
    obj = component.create()
    assert obj is not None, component.errorString()
    chapters = [dict(c) for c in _plain(obj.property("chapters"))]
    topics = [dict(t) for t in _plain(obj.property("topics"))]
    for topic in topics:
        topic["related"] = list(topic.get("related") or [])
    obj.deleteLater()
    return chapters, topics


def text(markup: str) -> str:
    """Visible text of a topic body."""
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def chapter_topics(chapter_id: str) -> list[dict]:
    return [t for t in load()[1] if t["chapterId"] == chapter_id]


def book_text() -> str:
    """Every topic's title and text, one topic per paragraph."""
    return "\n\n".join(t["title"] + "\n" + text(t["body"]) for t in load()[1])


def book_html() -> str:
    return "\n\n".join(t["body"] for t in load()[1])


def find(*titles: str) -> dict:
    """The first topic with one of these titles (old and new names)."""
    by_title = {t["title"].casefold(): t for t in load()[1]}
    for title in titles:
        topic = by_title.get(title.casefold())
        if topic is not None:
            return topic
    raise AssertionError(f"no Help topic titled {titles}")

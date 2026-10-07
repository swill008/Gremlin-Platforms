# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/help_topics.js must run: a syntax slip there leaves the Help window
empty (it failed to open after one, caught only by a window test)."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtQml

_SCRIPT = Path(__file__).resolve().parents[2] / "qml" / "help_topics.js"


def _run(call: str) -> QtQml.QJSValue:
    source = "\n".join(
        "" if line.startswith(".") else line
        for line in _SCRIPT.read_text(encoding="utf-8").splitlines()
    )
    engine = QtQml.QJSEngine()
    result = engine.evaluate(source + "\n" + call, str(_SCRIPT))
    assert not result.isError(), result.toString()
    return result


# The engine needs the application object (pytest-qt's qapp).
def test_the_guide_topics_build(qapp: QtCore.QCoreApplication) -> None:
    assert _run("topics().length").toInt() > 10


def test_the_button_map_topics_build(qapp: QtCore.QCoreApplication) -> None:
    assert _run("buttonMapTopics().length").toInt() > 0

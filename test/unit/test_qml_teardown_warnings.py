# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Closing a page leaves no Qt warnings behind (QML-WARN, user console
2026-10-10).

1. The OSC Monitor panel (qml/OscMonitorPanel.qml) destroyed while it
   holds the port releases it without overwriting its ``active`` binding
   (no "qt.qml.binding.removal" message).
2. The Configuration page (qml/ConfigurationPage.qml) destroyed while its
   delayed "show the current input" call is pending runs nothing of it
   afterwards (no "QQmlVMEMetaObject: Internal error" or "showIndex ... is
   not a function").

A journey (test/journeys/_harness.py): the real program off-screen with a
temporary USERPROFILE and fake hardware; Qt's messages are captured with a
message handler. The OSC port is a fake (no socket).

Spec: none (no behaviour change).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402

STICK = "pJoy Pro"
_PAGE_URL = (ROOT / "qml" / "ConfigurationPage.qml").as_uri()


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _before(j: Journey) -> None:
    j.input_module(STICK)
    j.vjoy_module()


class _FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def hold_open(self, token: str) -> bool:
        self.calls.append("hold")
        return True

    def release_open(self, token: str) -> None:
        self.calls.append("release")


def story(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin.ui import osc_monitor_model as mm

    messages: list[str] = []
    previous = None

    def handler(kind: Any, context: Any, text: str) -> None:  # noqa: ANN401
        messages.append(str(text))
        if previous is not None:
            previous(kind, context, text)

    previous = QtCore.qInstallMessageHandler(handler)
    QtCore.QLoggingCategory.setFilterRules("qt.qml.binding.removal.info=true")

    runtime = _FakeRuntime()
    mm._runtime = lambda: runtime  # type: ignore[assignment]

    # 1. The OSC Monitor panel, unfolded (holds the port), then destroyed.
    made = j.ev(
        "(function() {"
        " var win = Qt.createQmlObject('import QtQuick; import QtQuick.Window;"
        " Window { width: 900; height: 500; visible: true }', _root, 'oschost');"
        " var c = Qt.createComponent('OscMonitorPanel.qml');"
        " if (c.status !== Component.Ready) return 'error: ' + c.errorString();"
        " var p = c.createObject(win.contentItem, { folded: false });"
        " if (!p) return 'error: not made';"
        " return win })()"
    )
    j.out["oscMade"] = "ok" if hasattr(made, "metaObject") else str(made)
    j.settle()
    j.out["oscHeld"] = list(runtime.calls)
    j.ev("destroy()", made)
    for _ in range(10):
        j.settle()
    j.out["oscReleased"] = list(runtime.calls)

    # 2. The Configuration page: a device change schedules the delayed
    # call; the page goes away before it runs.
    guid = str(j.stick(STICK).device_guid.uuid)
    for attempt in range(3):
        # Hosted in a Loader as Main hosts it (_configPageLoader).
        host = j.ev(
            "Qt.createQmlObject('import QtQuick; import QtQuick.Window;"
            " Window { width: 1200; height: 800; visible: true;"
            " property alias page: _l.item;"
            " function unload() { _l.active = false }"
            " Loader { id: _l; anchors.fill: parent;"
            f' source: \"{_PAGE_URL}\" }} }}\', _root, \'cfghost\')'.replace("}}", "}")
        )
        j.wait_until(lambda: host.property("page"), "the hosted ConfigurationPage")
        page = host.property("page")
        j.out[f"cfgMade{attempt}"] = "ok" if hasattr(page, "metaObject") else str(page)
        j.ev(f"setDevice({guid!r}, {STICK!r}); true", page)
        j.settle()
        # A device change queues the delayed call; the Loader unloads the
        # page before it runs.
        j.ev(f"setDevice({guid!r}, {STICK + ' '!r}); true", page)
        j.ev("unload(); true", host)
        for _ in range(10):
            j.settle()

    QtCore.qInstallMessageHandler(previous)
    j.out["messages"] = messages


def main() -> None:
    from _harness import Journey as _J

    _J(_before).run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


def _bad(messages: list[str]) -> list[str]:
    marks = (
        "binding.removal",
        "Overwriting binding",
        "invalid context",
        "is not a function",
        "OscMonitorPanel.qml",
        "ConfigurationPage.qml",
    )
    return [m for m in messages if any(k in m for k in marks)]


def test_closing_pages_leaves_no_qt_warnings(tmp_path: pathlib.Path) -> None:
    out = run_journey(pathlib.Path(__file__), tmp_path)
    assert "error" not in out, (out.get("error"), out.get("traceback"))
    assert step(out, "oscMade") == "ok"
    assert step(out, "oscHeld") == ["hold"]
    assert step(out, "oscReleased") == ["hold", "release"]
    assert step(out, "cfgMade0") == "ok"
    assert _bad(step(out, "messages")) == []

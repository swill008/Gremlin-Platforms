# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Send OSC editor in the real program off-screen (D-09-OSC-OUTPUT):
a stick button's pane opened, Send OSC added as Add Action adds it, the
address typed with real key events, Add Value clicked. test_osc_output.py
runs it in its own process with a fresh user folder (journey harness).

    python test/unit/send_osc_editor_smoke.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey  # noqa: E402


def _shown(item) -> bool:  # noqa: ANN001
    p = item
    while p is not None:
        if not p.isVisible() or p.opacity() == 0:
            return False
        p = p.parentItem()
    return True


def story(j: Journey) -> None:
    from PySide6 import QtCore, QtGui, QtQuick

    out = j.out
    j.win.setWidth(1600)
    j.win.setHeight(950)
    j.QTest.qWait(300)
    catalog = j.open_configuration("pjoy_pro")
    page = j.ev("catalogPane()")
    hid = j.device_index(catalog, "button", 1)
    j.ev(f"openAdvancedPane({hid}); true", page)
    j.wait_until(lambda: catalog.paneModel is not None, "the pane")
    root = j.wait_until(lambda: j.pane_actions(catalog)[0], "the root action")
    root.appendAction("Send OSC", "children")

    def named(name: str):  # noqa: ANN202
        return next(
            (
                it for it in j.walk(j.win.contentItem())
                if it.objectName() == name and _shown(it)
            ),
            None,
        )

    field = j.wait_until(lambda: named("sendOscAddress"), "the Send OSC editor")
    out["editor"] = True
    action = j.pane_actions(catalog)[1]
    out["targets"] = [c["name"] for c in action.targetChoices]

    # Real mouse and key events: click the address field, type.
    j.QTest.qWait(800)  # the pane has slid in
    window = field.window()
    window.setProperty("visible", True)
    window.requestActivate()
    j.wait_until(lambda: QtGui.QGuiApplication.focusWindow() is window, "focus")
    centre = field.mapToScene(QtCore.QPointF(field.width() / 2, field.height() / 2))
    j.QTest.mouseClick(
        window, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier,
        centre.toPoint(),
    )
    j.QTest.qWait(100)
    j.wait_until(lambda: field.hasActiveFocus(), "the address field's focus")
    for ch in "/fire":
        j.QTest.keyClick(
            window,
            QtCore.Qt.Key(ord(ch.upper())),
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
    j.QTest.qWait(100)
    out["typed-address"] = action.address

    add = named("sendOscAddValue")
    assert isinstance(add, QtQuick.QQuickItem)
    j.click(add)
    j.QTest.qWait(100)
    out["values-after-add"] = len(action.values)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


if __name__ == "__main__":
    main()

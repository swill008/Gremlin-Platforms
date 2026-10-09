# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S134 (D-01-LEAVE-TEXT): a text box being typed in is left by Esc or a
press outside it, keeping what was typed; gremlin/ui/leave_text.py is the
one owner for every window.

Needs a QGuiApplication with real (off-screen) windows, which can't share a
process with the unit tests' QCoreApplication, so the checks run in a child
process (this file run as a script) and each test reads its result.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_QML = r"""
import QtQuick
import QtQuick.Controls

Window {
    id: win
    width: 640; height: 480
    visible: true
    property string savedField: ""
    property string savedArea: ""
    property string savedSeenByButton: "-"
    property int buttonClicks: 0
    property int popupClicks: 0
    property bool renameCancelled: false

    // As EscapeCloses.qml: Esc closes the window.
    Shortcut { sequences: [StandardKey.Cancel]; onActivated: win.close() }

    TextField {
        objectName: "field"; x: 10; y: 10; width: 200; height: 30
        onEditingFinished: win.savedField = text
    }
    ScrollView {
        x: 10; y: 60; width: 200; height: 80
        TextArea {
            objectName: "area"
            onActiveFocusChanged: if (!activeFocus) win.savedArea = text
        }
    }
    Button {
        objectName: "button"; x: 300; y: 10; width: 100; height: 30
        focusPolicy: Qt.NoFocus
        onClicked: { win.savedSeenByButton = win.savedField; win.buttonClicks++ }
    }
    TextField {
        objectName: "rename"; x: 10; y: 160; width: 200; height: 30
        text: "Original"
        Keys.onEscapePressed: (event) => {
            text = "Original"; win.renameCancelled = true; event.accepted = true
        }
    }
    TextField {
        objectName: "readonly"; x: 10; y: 210; width: 200; height: 30
        readOnly: true; text: "fixed"
    }
    Popup {
        objectName: "popup"; x: 300; y: 200; width: 150; height: 80
        focus: false; modal: false; closePolicy: Popup.NoAutoClose
        Button {
            objectName: "popupButton"; anchors.fill: parent
            focusPolicy: Qt.NoFocus
            onClicked: win.popupClicks++
        }
    }
}
"""

_QML_DIALOG = r"""
import QtQuick
import QtQuick.Controls

Window {
    id: win
    width: 640; height: 480
    visible: true
    property string saved: ""
    property int menuClicks: 0
    Dialog {
        objectName: "dialog"; x: 100; y: 100; width: 300; height: 200
        modal: true; closePolicy: Popup.NoAutoClose
        TextField {
            objectName: "dialogField"; x: 10; y: 10; width: 200; height: 30
            onEditingFinished: win.saved = text
        }
    }
    // A popup stacked above the dialog, as the box's right-click menu.
    Popup {
        objectName: "menu"; x: 450; y: 300; width: 150; height: 80
        focus: false; modal: false; closePolicy: Popup.NoAutoClose
        Button {
            objectName: "menuButton"; anchors.fill: parent
            focusPolicy: Qt.NoFocus
            onClicked: win.menuClicks++
        }
    }
}
"""

_QML_OPTED_OUT = r"""
import QtQuick
import QtQuick.Controls

Window {
    id: win
    width: 400; height: 300
    visible: true
    property bool leaveTextOnEscape: false
    property int escapes: 0
    // As Module Setup: Esc does nothing (sticks send it).
    Shortcut { sequence: "Esc"; onActivated: win.escapes++ }
    TextField { objectName: "field"; x: 10; y: 10; width: 200; height: 30 }
}
"""


def _child() -> None:
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest

    app = QtGui.QGuiApplication(sys.argv)
    if os.environ.get("LEAVE_TEXT_TEST_OFF") != "1":
        import gremlin.ui.leave_text

        keep = gremlin.ui.leave_text.install(app)  # noqa: F841
    app.setQuitOnLastWindowClosed(False)
    engines: list[QtQml.QQmlApplicationEngine] = []
    Qt = QtCore.Qt
    folder = pathlib.Path(sys.argv[2])

    def result(name: str, value: object) -> None:
        print("RESULT", name, value)
        sys.stdout.flush()

    def spin(ms: int = 30) -> None:
        deadline = QtCore.QDeadlineTimer(ms)
        while not deadline.hasExpired():
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)

    def load(text: str, name: str) -> QtQuick.QQuickWindow:
        path = folder / name
        path.write_text(text, encoding="utf-8")
        engine = QtQml.QQmlApplicationEngine(app)
        engines.append(engine)
        engine.load(QtCore.QUrl.fromLocalFile(str(path)))
        window = engine.rootObjects()[0]
        assert isinstance(window, QtQuick.QQuickWindow)
        window.requestActivate()
        deadline = QtCore.QDeadlineTimer(5000)
        while not window.isActive() and not deadline.hasExpired():
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        spin(50)
        return window

    def item(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem:
        found = window.findChild(QtQuick.QQuickItem, name)
        assert found is not None, name
        return found

    def centre(it: QtQuick.QQuickItem) -> QtCore.QPoint:
        return it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2)).toPoint()

    def click(window: QtQuick.QQuickWindow, pos: QtCore.QPoint) -> None:
        QtTest.QTest.mouseClick(
            window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos
        )
        spin()

    def escape(window: QtQuick.QQuickWindow) -> None:
        QtTest.QTest.keyClick(window, Qt.Key.Key_Escape)
        spin()

    def type_into(
        window: QtQuick.QQuickWindow, it: QtQuick.QQuickItem, text: str
    ) -> None:
        it.forceActiveFocus()
        spin()
        for char in text:
            QtTest.QTest.keyClick(window, char)
        spin()

    win = load(_QML, "leave.qml")
    blank = QtCore.QPoint(500, 400)
    field, area = item(win, "field"), item(win, "area")

    # Press on a blank spot leaves a TextField and a TextArea, text kept.
    type_into(win, field, "abc")
    result("typed_focus", field.hasActiveFocus())
    click(win, blank)
    result("blank_field", (field.hasActiveFocus(), win.property("savedField")))
    type_into(win, area, "notes")
    click(win, blank)
    result("blank_area", (area.hasActiveFocus(), win.property("savedArea")))

    # Press inside the box (and in its own scroll area) keeps it.
    type_into(win, area, "x")
    click(win, centre(area))
    result("inside_area", area.hasActiveFocus())
    click(win, blank)

    # Press on another control: the box is left and saved first, and the
    # control still gets the click.
    field.setProperty("text", "")
    type_into(win, field, "button")
    click(win, centre(item(win, "button")))
    result(
        "other_control",
        (
            field.hasActiveFocus(),
            win.property("buttonClicks"),
            win.property("savedSeenByButton"),
        ),
    )

    # Esc leaves the box, text kept, and doesn't close the window.
    field.setProperty("text", "")
    type_into(win, field, "esc")
    escape(win)
    result(
        "escape_field",
        (field.hasActiveFocus(), win.property("savedField"), win.isVisible()),
    )

    # A box's own Esc (a Rename's cancel) still cancels.
    rename = item(win, "rename")
    type_into(win, rename, " changed")
    escape(win)
    result(
        "escape_cancel",
        (
            rename.property("text"),
            win.property("renameCancelled"),
            rename.hasActiveFocus(),
            win.isVisible(),
        ),
    )

    # A read-only box is not a box being typed in: Esc goes to the window
    # (checked last, it closes it); a press elsewhere leaves its focus alone.
    readonly = item(win, "readonly")
    readonly.forceActiveFocus()
    spin()
    click(win, blank)
    result("readonly_press", readonly.hasActiveFocus())

    # A press on an open popup doesn't take the box's focus away, and the
    # popup's control still gets the click.
    popup = win.findChild(QtCore.QObject, "popup")
    assert popup is not None
    QtCore.QMetaObject.invokeMethod(popup, "open")
    spin(100)
    type_into(win, field, "p")
    click(win, centre(item(win, "popupButton")))
    result("popup_press", (field.hasActiveFocus(), win.property("popupClicks")))
    QtCore.QMetaObject.invokeMethod(popup, "close")
    spin(100)

    # Where Esc closes the window: the first Esc leaves the box, the second
    # closes the window.
    type_into(win, field, "q")
    escape(win)
    first = (field.hasActiveFocus(), win.isVisible())
    escape(win)
    result("escape_twice", (first, win.isVisible()))

    # In a modal Dialog: a press on the dialog's blank space or on the
    # dimmed area outside it leaves the box; one on another popup above
    # (the box's right-click menu) keeps it.
    dwin = load(_QML_DIALOG, "dialog.qml")
    dialog = dwin.findChild(QtCore.QObject, "dialog")
    assert dialog is not None
    QtCore.QMetaObject.invokeMethod(dialog, "open")
    spin(100)
    dfield = item(dwin, "dialogField")
    type_into(dwin, dfield, "in")
    click(dwin, QtCore.QPoint(300, 260))
    result("dialog_blank", (dfield.hasActiveFocus(), dwin.property("saved")))
    type_into(dwin, dfield, "out")
    click(dwin, QtCore.QPoint(20, 450))
    result("dialog_dimmer", (dfield.hasActiveFocus(), dwin.property("saved")))
    menu = dwin.findChild(QtCore.QObject, "menu")
    assert menu is not None
    QtCore.QMetaObject.invokeMethod(menu, "open")
    spin(100)
    type_into(dwin, dfield, "m")
    click(dwin, centre(item(dwin, "menuButton")))
    result("dialog_menu", (dfield.hasActiveFocus(), dwin.property("menuClicks")))

    # Opted out (Module Setup): Esc does nothing, a press away still leaves.
    out = load(_QML_OPTED_OUT, "opted_out.qml")
    out_field = item(out, "field")
    type_into(out, out_field, "name")
    escape(out)
    result(
        "opted_out_escape",
        (out_field.hasActiveFocus(), out.property("escapes"), out.isVisible()),
    )
    click(out, QtCore.QPoint(300, 250))
    result("opted_out_press", out_field.hasActiveFocus())

    print("done")
    sys.stdout.flush()
    os._exit(0)


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    tmp_path = tmp_path_factory.mktemp("leave_text")
    run = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), "child", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_CONTROLS_STYLE": "Basic",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
            "PYTHONPATH": str(_ROOT),
        },
    )
    lines = run.stdout.splitlines()
    assert "done" in lines, run.stdout[-3000:] + run.stderr[-3000:]
    return dict(
        tuple(line.split(" ", 2)[1:]) for line in lines if line.startswith("RESULT ")
    )


def test_press_on_blank_space_leaves_a_text_field(found: dict[str, str]) -> None:
    assert found["typed_focus"] == "True"
    assert found["blank_field"] == "(False, 'abc')"


def test_press_on_blank_space_leaves_a_text_area(found: dict[str, str]) -> None:
    assert found["blank_area"] == "(False, 'notes')"


def test_press_inside_the_box_keeps_it(found: dict[str, str]) -> None:
    assert found["inside_area"] == "True"


def test_press_on_another_control_leaves_and_the_control_acts(
    found: dict[str, str],
) -> None:
    # Saved before the button acted; the button got its click.
    assert found["other_control"] == "(False, 1, 'button')"


def test_escape_leaves_the_box_and_keeps_the_text(found: dict[str, str]) -> None:
    assert found["escape_field"] == "(False, 'esc', True)"


def test_escape_still_cancels_where_the_box_cancels(found: dict[str, str]) -> None:
    assert found["escape_cancel"] == "('Original', True, False, True)"


def test_escape_twice_where_escape_closes_the_window(found: dict[str, str]) -> None:
    assert found["escape_twice"] == "((False, True), False)"


def test_opted_out_window_escape_does_nothing(found: dict[str, str]) -> None:
    # The window's own Esc shortcut takes it; the box keeps the focus.
    assert found["opted_out_escape"] == "(True, 1, True)"


def test_opted_out_window_press_away_still_leaves(found: dict[str, str]) -> None:
    assert found["opted_out_press"] == "False"


def test_read_only_box_is_ignored(found: dict[str, str]) -> None:
    assert found["readonly_press"] == "True"


def test_press_on_an_open_popup_keeps_the_box(found: dict[str, str]) -> None:
    assert found["popup_press"] == "(True, 1)"


def test_modal_dialog_press_on_its_blank_space_leaves_the_box(
    found: dict[str, str],
) -> None:
    assert found["dialog_blank"] == "(False, 'in')"


def test_modal_dialog_press_on_the_dimmed_area_leaves_the_box(
    found: dict[str, str],
) -> None:
    assert found["dialog_dimmer"] == "(False, 'inout')"


def test_modal_dialog_press_on_a_popup_above_keeps_the_box(
    found: dict[str, str],
) -> None:
    assert found["dialog_menu"] == "(True, 1)"


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "child":
    sys.path.insert(0, str(_ROOT))
    _child()

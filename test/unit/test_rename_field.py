# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S135 (D-01-ONE-RENAME): the one inline Rename box, qml/RenameField.qml.

Opens focused with the whole name selected; Enter or leaving it (a click
away, 01 S134) saves once; Esc cancels; an empty or unchanged name isn't
saved; ended() follows every edit with open already false.

Real QML off-screen with the real leave_text filter (01 S134) installed and
real Qt key/mouse events. Needs a QGuiApplication, so the checks run in a
child process (this file run as a script) and each test reads its result.
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
import "%QMLDIR%"

Window {
    id: win
    width: 640; height: 480
    visible: true
    property var saves: []
    property int ends: 0
    property bool openAtEnd: true
    property int closes: 0

    // As EscapeCloses.qml: Esc closes the window.
    Shortcut { sequences: [StandardKey.Cancel]; onActivated: win.closes++ }

    Label {
        objectName: "label"; x: 10; y: 10
        text: _rename.name; visible: !_rename.open
    }
    RenameField {
        id: _rename
        objectName: "rename"
        x: 10; y: 10; width: 300; height: 30
        name: "Original"
        onRenamed: (newName) => {
            var s = win.saves.slice(); s.push(newName); win.saves = s
            name = newName
        }
        onEnded: { win.ends++; win.openAtEnd = open }
    }
    Button {
        objectName: "button"; x: 400; y: 10; width: 100; height: 30
        focusPolicy: Qt.NoFocus
    }
}
"""


def _child() -> None:
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest

    app = QtGui.QGuiApplication(sys.argv[:1])
    import gremlin.ui.leave_text

    keep = gremlin.ui.leave_text.install(app)  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    Qt = QtCore.Qt
    folder = pathlib.Path(sys.argv[2])

    def result(name: str, value: object) -> None:
        print("RESULT", name, value)
        sys.stdout.flush()

    def spin(ms: int = 30) -> None:
        deadline = QtCore.QDeadlineTimer(ms)
        while not deadline.hasExpired():
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)

    path = folder / "rename.qml"
    qml_dir = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml")).toString()
    path.write_text(_QML.replace("%QMLDIR%", qml_dir), encoding="utf-8")
    engine = QtQml.QQmlApplicationEngine(app)
    engine.addImportPath(str(_ROOT / "theme"))
    engine.warnings.connect(
        lambda ws: [print("QMLWARN", w.toString()) for w in ws]
    )
    engine.load(QtCore.QUrl.fromLocalFile(str(path)))
    roots = engine.rootObjects()
    assert roots, "rename.qml failed to load"
    win = roots[0]
    assert isinstance(win, QtQuick.QQuickWindow)
    win.requestActivate()
    deadline = QtCore.QDeadlineTimer(5000)
    while not win.isActive() and not deadline.hasExpired():
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
    spin(50)

    field = win.findChild(QtQuick.QQuickItem, "rename")
    assert field is not None

    def state() -> tuple:
        return (
            list(win.property("saves").toVariant()),  # a QJSValue array
            win.property("ends"),
            field.property("open"),
            field.isVisible(),
        )

    def start() -> None:
        QtCore.QMetaObject.invokeMethod(field, "start")
        spin()

    def type_text(text: str) -> None:
        for char in text:
            QtTest.QTest.keyClick(win, char)
        spin()

    def key(k: QtCore.Qt.Key) -> None:
        QtTest.QTest.keyClick(win, k)
        spin()

    def click(pos: QtCore.QPoint) -> None:
        QtTest.QTest.mouseClick(
            win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos
        )
        spin()

    blank = QtCore.QPoint(500, 400)

    # Closed to start with.
    result("closed_at_start", (field.property("open"), field.isVisible()))

    # Opens focused with the whole name selected.
    start()
    result(
        "opened",
        (
            field.property("open"),
            field.isVisible(),
            field.hasActiveFocus(),
            field.property("selectedText"),
            field.property("text"),
        ),
    )
    # Typing replaces it; Enter saves once.
    type_text("Alpha")
    result("typed", field.property("text"))
    key(Qt.Key.Key_Return)
    result("enter", state())
    result("enter_open_at_end", win.property("openAtEnd"))
    click(blank)
    result("enter_then_click", state())

    # Reopen: a click away saves once; a second click saves nothing more.
    start()
    result("reopened", (field.hasActiveFocus(), field.property("selectedText")))
    type_text("Beta")
    click(blank)
    result("click_away", state())
    click(blank)
    result("click_away_twice", state())

    # A click on another control saves once too.
    start()
    type_text("Gamma")
    click(QtCore.QPoint(450, 25))
    result("click_button", state())

    # Esc cancels: nothing saved, even after the focus loss; the window's
    # Esc shortcut doesn't run.
    start()
    type_text("Nope")
    key(Qt.Key.Key_Escape)
    result("escape", state())
    result("escape_closes", win.property("closes"))
    result("escape_open_at_end", win.property("openAtEnd"))
    result("escape_name", field.property("name"))
    click(blank)
    result("escape_then_click", state())

    # Empty isn't saved.
    start()
    key(Qt.Key.Key_Backspace)
    result("empty_text", repr(field.property("text")))
    key(Qt.Key.Key_Return)
    result("empty", state())
    result("empty_name", field.property("name"))

    # Spaces only count as empty; unchanged isn't saved.
    start()
    type_text("   ")
    key(Qt.Key.Key_Return)
    start()
    key(Qt.Key.Key_Return)
    result("blank_and_unchanged", state())

    # Trimmed before it is saved.
    start()
    type_text("  Delta  ")
    key(Qt.Key.Key_Return)
    result("trimmed", state())

    # The owner closing it mid-edit cancels.
    start()
    type_text("Epsilon")
    field.setProperty("open", False)
    spin()
    result("owner_close", state())

    print("done")
    sys.stdout.flush()
    os._exit(0)


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    tmp_path = tmp_path_factory.mktemp("rename_field")
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


def test_closed_until_opened(found: dict[str, str]) -> None:
    assert found["closed_at_start"] == "(False, False)"


def test_opens_focused_with_the_whole_name_selected(found: dict[str, str]) -> None:
    assert found["opened"] == "(True, True, True, 'Original', 'Original')"


def test_typing_replaces_the_name(found: dict[str, str]) -> None:
    assert found["typed"] == "Alpha"


def test_enter_saves_once_and_ends(found: dict[str, str]) -> None:
    assert found["enter"] == "(['Alpha'], 1, False, False)"
    assert found["enter_open_at_end"] == "False"
    assert found["enter_then_click"] == "(['Alpha'], 1, False, False)"


def test_reopen_selects_the_new_name(found: dict[str, str]) -> None:
    assert found["reopened"] == "(True, 'Alpha')"


def test_click_away_saves_once(found: dict[str, str]) -> None:
    assert found["click_away"] == "(['Alpha', 'Beta'], 2, False, False)"
    assert found["click_away_twice"] == "(['Alpha', 'Beta'], 2, False, False)"


def test_click_on_another_control_saves_once(found: dict[str, str]) -> None:
    assert found["click_button"] == "(['Alpha', 'Beta', 'Gamma'], 3, False, False)"


def test_escape_cancels_and_the_focus_loss_saves_nothing(
    found: dict[str, str],
) -> None:
    assert found["escape"] == "(['Alpha', 'Beta', 'Gamma'], 4, False, False)"
    assert found["escape_open_at_end"] == "False"
    assert found["escape_name"] == "Gamma"
    assert found["escape_closes"] == "0"
    assert found["escape_then_click"] == found["escape"]


def test_empty_name_is_not_saved(found: dict[str, str]) -> None:
    assert found["empty_text"] == "''"
    assert found["empty"] == "(['Alpha', 'Beta', 'Gamma'], 5, False, False)"
    assert found["empty_name"] == "Gamma"


def test_blank_or_unchanged_name_is_not_saved(found: dict[str, str]) -> None:
    assert found["blank_and_unchanged"] == (
        "(['Alpha', 'Beta', 'Gamma'], 7, False, False)"
    )


def test_saved_name_is_trimmed(found: dict[str, str]) -> None:
    assert found["trimmed"] == "(['Alpha', 'Beta', 'Gamma', 'Delta'], 8, False, False)"


def test_owner_closing_mid_edit_cancels(found: dict[str, str]) -> None:
    assert found["owner_close"] == (
        "(['Alpha', 'Beta', 'Gamma', 'Delta'], 9, False, False)"
    )


if __name__ == "__main__" and sys.argv[1:2] == ["child"]:
    _child()

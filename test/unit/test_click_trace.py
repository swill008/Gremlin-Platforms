# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

# ONE-TIME (tracker OT-5): temporary click trace for the dead right-click
# report; remove after the fix (the whole file).

"""The temporary click trace (gremlin/ui/click_trace.py, tracker OT-5): with
Tracing on and the Trace tab's Mouse row ticked, a press on the Device
Mapping Editor window writes a CLICK line with the event, button, window,
position and item under the point, then an "after" line with the grabber,
all as MOUSE lines; with Tracing off or Mouse unticked nothing is written
and the filter is not installed; other windows are not traced; the Mouse
tick is saved; the Mouse filter shows them alone."""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore, QtGui, QtQuick
from pytestqt.qtbot import QtBot

from gremlin import trace, util
from gremlin.ui import click_trace


@pytest.fixture(autouse=True)
def _fresh(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    trace.set_mouse(False)
    yield
    trace.set_mouse(False)
    trace._reset_for_tests()
    # The windows' deleteLater runs now, so no test sees another's window.
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    click_trace.dispose()
    assert click_trace._hook not in trace._hooks


@pytest.fixture
def gui_app(qapp: QtCore.QCoreApplication) -> QtCore.QCoreApplication:
    """Windows need a QGuiApplication: an earlier test in the same process
    may have made a plain QCoreApplication, and making a window then ends the
    process (seen in the full run, part unit-5)."""
    if not isinstance(qapp, QtGui.QGuiApplication):
        pytest.skip("a plain QCoreApplication is running: no window can be made")
    return qapp


class _Probe(QtQuick.QQuickItem):
    def __init__(self, parent: QtQuick.QQuickItem) -> None:
        super().__init__(parent)
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.AllButtons)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:  # noqa: N802
        ev.accept()


def _window(title: str) -> QtQuick.QQuickWindow:
    win = QtQuick.QQuickWindow()
    win.setTitle(title)
    win.resize(200, 150)
    probe = _Probe(win.contentItem())
    probe.setObjectName("probeItem")
    probe.setSize(QtCore.QSizeF(200, 150))
    return win


def _press(win: QtQuick.QQuickWindow, button: QtCore.Qt.MouseButton) -> None:
    p = QtCore.QPointF(40, 30)
    ev = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonPress, p, win.mapToGlobal(p), button, button,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    QtCore.QCoreApplication.sendEvent(win, ev)
    rel = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease, p, win.mapToGlobal(p), button,
        QtCore.Qt.MouseButton.NoButton, QtCore.Qt.KeyboardModifier.NoModifier,
    )
    QtCore.QCoreApplication.sendEvent(win, rel)


def _clicks() -> list[str]:
    return [line[3] for line in trace.lines() if line[3].startswith(click_trace.PREFIX)]


def _mouse_lines() -> list[str]:
    return [line[3] for line in trace.lines() if line[2] == trace.MOUSE]


def test_on_writes_press_line_with_fields(
    gui_app: QtCore.QCoreApplication, qtbot: QtBot
) -> None:
    ct = click_trace.install(gui_app)
    win = _window("Device Mapping Editor — Rig")
    try:
        trace.set_mouse(True)
        trace.set_enabled(True)
        assert ct.watched() == 1
        _press(win, QtCore.Qt.MouseButton.RightButton)
        qtbot.waitUntil(lambda: any(" after: " in t for t in _clicks()), timeout=2000)
        lines = _clicks()
        press = next(t for t in lines if t.startswith("CLICK press "))
        assert "button=R" in press
        assert "window='Device Mapping Editor — Rig'" in press
        assert "pos=(40,30)" in press
        assert "probeItem" in press
        assert "t=" in press
        assert any(t.startswith("CLICK release ") for t in lines)
        hit = next(t for t in lines if t.startswith("CLICK press hit 1/"))
        fields = ("probeItem", "parent=", "z=", "rect=(0,0 200x150)", "enabled=")
        for field in (*fields, "buttons=", "hover="):
            assert field in hit, (field, hit)
        assert any(t.startswith("CLICK press boxes: ") for t in lines)
        after = next(t for t in lines if t.startswith("CLICK press after: "))
        assert "grabber=" in after and "focusWindow=" in after
        # Every click line is a MOUSE line, none an EVENT line.
        assert _mouse_lines() == lines
        assert "  MOUSE  CLICK press " in (
            pathlib.Path(util.logs_dir()) / "trace.log"
        ).read_text(encoding="utf-8")
        assert (pathlib.Path(util.logs_dir()) / "trace.log").exists()
    finally:
        trace.set_enabled(False)
        win.deleteLater()


def test_off_writes_nothing_and_filter_is_out(
    gui_app: QtCore.QCoreApplication, qtbot: QtBot
) -> None:
    ct = click_trace.install(gui_app)
    win = _window("Device Mapping Editor")
    try:
        assert ct.watched() == 0
        _press(win, QtCore.Qt.MouseButton.RightButton)
        qtbot.wait(20)
        ct.line("x")
        ct.menu("closed", "Device Mapping Editor")
        assert _clicks() == []
        # On, then off again: the filter is removed and nothing more is written.
        trace.set_mouse(True)
        trace.set_enabled(True)
        trace.set_enabled(False)
        assert ct.watched() == 0
        before = len(_clicks())
        _press(win, QtCore.Qt.MouseButton.LeftButton)
        qtbot.wait(20)
        assert len(_clicks()) == before
    finally:
        win.deleteLater()


def test_other_windows_not_traced_and_menu_close_reason(
    gui_app: QtCore.QCoreApplication, qtbot: QtBot
) -> None:
    ct = click_trace.install(gui_app)
    other = _window("Gremlin Platforms")
    ed = _window("Device Mapping Editor")
    try:
        trace.set_mouse(True)
        trace.set_enabled(True)
        _press(other, QtCore.Qt.MouseButton.RightButton)
        ct.menu("opened", "Gremlin Platforms")
        qtbot.wait(20)
        assert _clicks() == []
        esc = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_Escape,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        QtCore.QCoreApplication.sendEvent(ed, esc)
        ct.menu("closed", "Device Mapping Editor")
        assert any("menu closed" in t and "reason=Esc" in t for t in _clicks())
        ct.closingFor("item chosen: Copy")
        ct.menu("closed", "Device Mapping Editor")
        assert _clicks()[-1].endswith("reason=item chosen: Copy")
    finally:
        trace.set_enabled(False)
        other.deleteLater()
        ed.deleteLater()


def test_one_trace_per_app_and_dispose_removes_everything(
    gui_app: QtCore.QCoreApplication, qtbot: QtBot
) -> None:
    first = click_trace.install(gui_app)
    assert click_trace.install(gui_app) is first
    assert trace._hooks.count(click_trace._hook) == 1
    win = _window("Device Mapping Editor")
    try:
        trace.set_mouse(True)
        trace.set_enabled(True)
        assert first.watched() == 1
        click_trace.dispose()
        assert first.watched() == 0
        assert click_trace.current() is None
        assert click_trace._hook not in trace._hooks
        before = len(_clicks())
        _press(win, QtCore.Qt.MouseButton.RightButton)
        qtbot.wait(20)
        assert len(_clicks()) == before
    finally:
        trace.set_enabled(False)
        win.deleteLater()


def test_mouse_unticked_writes_nothing_even_while_tracing(
    gui_app: QtCore.QCoreApplication, qtbot: QtBot
) -> None:
    ct = click_trace.install(gui_app)
    win = _window("Device Mapping Editor")
    try:
        assert not trace.mouse_ticked()  # off by default
        trace.set_enabled(True)
        assert ct.watched() == 0
        assert not ct.property("on")
        _press(win, QtCore.Qt.MouseButton.RightButton)
        ct.line("x")
        ct.menu("closed", "Device Mapping Editor")
        qtbot.wait(20)
        assert _clicks() == [] and _mouse_lines() == []
        # Ticked while tracing: the filter goes on and lines come.
        trace.set_mouse(True)
        assert ct.watched() == 1
        _press(win, QtCore.Qt.MouseButton.RightButton)
        qtbot.waitUntil(
            lambda: any(" after: " in t for t in _mouse_lines()), timeout=2000
        )
        # Unticked again: the filter comes off, nothing more is written.
        trace.set_mouse(False)
        assert ct.watched() == 0
        before = len(_mouse_lines())
        _press(win, QtCore.Qt.MouseButton.LeftButton)
        qtbot.wait(20)
        assert len(_mouse_lines()) == before
    finally:
        trace.set_enabled(False)
        win.deleteLater()


def test_mouse_tick_is_saved() -> None:
    from gremlin import config

    trace.set_mouse(True)
    assert config.Configuration().value("debug", "trace", "mouse") == "on"
    trace._reset_for_tests()  # a fresh start reads it back
    assert trace.mouse_ticked()
    assert not trace.mouse_on()  # tracing itself always starts off
    trace.set_mouse(False)
    trace._reset_for_tests()
    assert not trace.mouse_ticked()


def test_mouse_filter_shows_mouse_lines_alone(
    qapp: QtCore.QCoreApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import trace_model

    monkeypatch.setattr(trace_model, "_devices", lambda: [])  # no device read
    trace.set_mouse(True)
    trace.set_enabled(True)
    trace.event("Profile Start")
    trace.click(click_trace.PREFIX + "press x")
    tab = trace_model.TraceView()
    tab.refresh()
    assert "Mouse" in tab.property("pointNames")
    shown = lambda: [r[2] for r in tab._lines.rows]  # noqa: E731, SLF001
    assert trace.MOUSE in shown() and trace.EVENT in shown()
    for name in trace_model.POINTS:
        tab.setPoint(name, name == "Mouse")
    assert set(shown()) == {trace.MOUSE}
    tab.setPoint("Mouse", False)
    tab.setPoint("Event", True)
    assert trace.MOUSE not in shown() and trace.EVENT in shown()
    # The Mouse row in the tick list, and its slot.
    tree = tab._tree  # noqa: SLF001
    row = next(r for r in tree._rows if r["kind"] == "mouse")  # noqa: SLF001
    assert row["text"].startswith("Mouse") and row["check"] == 2
    tab.setMouse(False)
    row = next(r for r in tree._rows if r["kind"] == "mouse")  # noqa: SLF001
    assert row["check"] == 0 and not trace.mouse_ticked()

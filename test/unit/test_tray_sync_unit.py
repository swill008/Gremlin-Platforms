# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""SystemTrayIcon's one tray truth (01 S174, S175, S85, D-01-TRAY-TRUTH),
with a stand-in window and every Windows call stubbed. The real-window
checks are in test_tray_window_sync.py."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from PySide6 import QtCore, QtGui, QtTest

Visibility = QtGui.QWindow.Visibility
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


class _Window(QtCore.QObject):
    visibilityChanged = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.mode = Visibility.Windowed
        self.calls: list[object] = []

    def visibility(self) -> Visibility:
        return self.mode

    def isVisible(self) -> bool:
        return self.mode != Visibility.Hidden

    def setVisibility(self, mode: Visibility) -> None:
        self.calls.append(mode)
        self.mode = mode
        self.visibilityChanged.emit(mode)

    def hide(self) -> None:
        self.setVisibility(Visibility.Hidden)

    def raise_(self) -> None:
        pass

    def requestActivate(self) -> None:
        pass


class _Backend(QtCore.QObject):
    activityChanged = QtCore.Signal()
    quitRequested = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.gremlinActive = False
        self.engine = None


@pytest.fixture
def tray(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    from gremlin.ui import system_tray

    gui = system_tray.win32gui
    for name, fake in {
        "Shell_NotifyIcon": lambda *a: None,
        "LoadImage": lambda *a: 101,
        "RegisterWindowMessage": lambda _n: 49999,
        "RegisterClass": lambda _wc: 7,
        "CreateWindowEx": lambda *a: 55,
        "DestroyWindow": lambda *a: None,
        "UnregisterClass": lambda *a: None,
        "DestroyIcon": lambda *a: None,
    }.items():
        monkeypatch.setattr(gui, name, fake)
    monkeypatch.setattr(system_tray.win32api, "GetModuleHandle", lambda _n: 3)
    monkeypatch.setattr(system_tray.win32api, "GetSystemMetrics", lambda _n: 16)
    monkeypatch.setattr(system_tray, "_register_display_notify", lambda _h: 0)
    memory = system_tray.tray_memory
    monkeypatch.setattr(memory, "let_hidden_window_release_graphics", lambda w: None)
    ok = {"enter": True, "leave": True}
    monkeypatch.setattr(memory, "enter_tray", lambda w, e: ok["enter"])
    monkeypatch.setattr(memory, "leave_tray", lambda w: ok["leave"])
    notes: list[str] = []
    warnings: list[str] = []
    monkeypatch.setattr(system_tray, "_note", notes.append)
    monkeypatch.setattr(system_tray, "_warn", warnings.append)
    backend = _Backend()
    monkeypatch.setattr(system_tray, "Backend", lambda: backend)
    values: dict[tuple[str, ...], object] = {
        ("global", "general", "minimize-to-tray"): True,
        ("global", "internal", "tray-notice-shown"): True,
    }
    settings = SimpleNamespace(
        exists=lambda *key: tuple(key) in values,
        value=lambda *key: values[tuple(key)],
        set=lambda *kv: values.__setitem__(tuple(kv[:-1]), kv[-1]),
    )
    monkeypatch.setattr(system_tray, "Configuration", lambda: settings)
    window = _Window()
    icon = system_tray.SystemTrayIcon(window)  # type: ignore[arg-type]
    QtTest.QTest.qWait(20)
    yield SimpleNamespace(
        icon=icon,
        window=window,
        notes=notes,
        warnings=warnings,
        ok=ok,
        module=system_tray,
    )
    icon.release_resources()
    window.removeEventFilter(icon)


def test_minimize_hides_after_the_minimize_has_finished(tray: SimpleNamespace) -> None:
    tray.window.setVisibility(Visibility.Minimized)
    assert tray.window.mode == Visibility.Minimized  # not inside the signal
    QtTest.QTest.qWait(30)
    assert tray.window.mode == Visibility.Hidden
    assert tray.icon._trayed is True
    assert "tray: entered (minimize)" in tray.notes


def test_trayed_follows_only_a_taken_call(tray: SimpleNamespace) -> None:
    tray.ok["enter"] = False
    tray.window.hide()
    QtTest.QTest.qWait(30)
    assert tray.icon._trayed is False
    assert tray.warnings and "hiding to the tray failed" in tray.warnings[0]


def test_tray_click_leaves_the_tray_with_its_cause(tray: SimpleNamespace) -> None:
    import win32con

    tray.icon._toggle_visibility()
    QtTest.QTest.qWait(30)
    assert "tray: entered (tray menu)" in tray.notes
    tray.icon._system_tray_event_cb(55, tray.module._WM_TRAY, 0, win32con.WM_LBUTTONUP)
    QtTest.QTest.qWait(30)
    assert tray.icon._trayed is False
    assert "tray: left (tray click)" in tray.notes


def test_windows_showing_the_hidden_window_is_adopted(
    tray: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    tray.window.hide()
    QtTest.QTest.qWait(30)
    assert tray.icon._trayed is True
    # Windows shows the window; Qt still has it hidden.
    monkeypatch.setattr(tray.icon, "_native_state", lambda: (True, False))
    tray.icon.main_hwnd = 1234
    msg = ctypes.wintypes.MSG()
    msg.hWnd = 1234
    msg.message = tray.module._WM_SHOWWINDOW
    msg.wParam = 1
    handled = tray.icon._native_filter.nativeEventFilter(
        QtCore.QByteArray(b"windows_generic_MSG"), ctypes.addressof(msg)
    )
    assert handled == (False, 0)
    assert tray.window.mode == Visibility.Hidden  # queued, not in the message
    QtTest.QTest.qWait(30)
    assert tray.window.mode == Visibility.Windowed
    assert tray.icon._trayed is False
    assert "tray: left (Windows showed it)" in tray.notes
    assert tray.warnings == [
        "shown by Windows while hidden to the tray; showing it and loading its pages"
    ]


def test_filter_ignores_other_windows(tray: SimpleNamespace) -> None:
    tray.window.hide()
    QtTest.QTest.qWait(30)
    tray.icon.main_hwnd = 1234
    msg = ctypes.wintypes.MSG()
    msg.hWnd = 999
    msg.message = tray.module._WM_SHOWWINDOW
    msg.wParam = 1
    tray.icon._native_filter.nativeEventFilter(
        b"windows_generic_MSG", ctypes.addressof(msg)
    )
    QtTest.QTest.qWait(30)
    assert tray.window.mode == Visibility.Hidden
    assert tray.icon._trayed is True


def test_power_messages_are_recorded(tray: SimpleNamespace) -> None:
    cb = tray.icon._power_broadcast_cb
    assert cb(55, tray.module._WM_POWERBROADCAST, tray.module._PBT_APMSUSPEND, 0) == 1
    cb(55, tray.module._WM_POWERBROADCAST, tray.module._PBT_APMRESUMEAUTOMATIC, 0)
    assert tray.notes[-2:] == ["sleeping", "resumed"]

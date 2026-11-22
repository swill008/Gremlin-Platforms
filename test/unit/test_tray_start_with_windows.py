# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Tray menu item "Start with Windows" (01 S194): checked from the start-up
entry each time the menu opens, a click flips it. A fake start-up module
stands in; the real registry is never touched."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from gremlin.ui import system_tray


@pytest.fixture
def entry(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    state = {"on": False, "fail": False, "raise_read": False, "off_in_windows": False}
    calls: list[bool] = []
    opened: list[int] = []

    def get_state(store: object = None) -> str:
        if state["raise_read"]:
            raise OSError("registry unavailable")
        if state["off_in_windows"]:
            return "off_in_windows"
        return "on" if state["on"] else "off"

    def open_settings() -> bool:
        opened.append(1)
        return True

    def is_enabled(store: object = None) -> bool:
        if state["raise_read"]:
            raise OSError("registry unavailable")
        return state["on"]

    def set_enabled(on: bool, store: object = None) -> bool:
        calls.append(on)
        if state["fail"]:
            return False
        state["on"] = on
        return True

    module = types.ModuleType("gremlin.startup_entry")
    module.state = get_state  # type: ignore[attr-defined]
    module.open_windows_startup_settings = open_settings  # type: ignore[attr-defined]
    module.is_enabled = is_enabled  # type: ignore[attr-defined]
    module.set_enabled = set_enabled  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.startup_entry", module)
    import gremlin

    monkeypatch.setattr(gremlin, "startup_entry", module, raising=False)
    return SimpleNamespace(state=state, calls=calls, opened=opened)


def _tray() -> system_tray.SystemTrayIcon:
    tray = system_tray.SystemTrayIcon.__new__(system_tray.SystemTrayIcon)
    tray._hwnd = 5
    tray._window = SimpleNamespace(isVisible=lambda: True)
    tray._backend = SimpleNamespace(gremlinActive=False)
    return tray


def _menu_items(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int, str]]:
    items: list[tuple[int, int, str]] = []
    gui = system_tray.win32gui
    monkeypatch.setattr(gui, "CreatePopupMenu", lambda: 9)
    monkeypatch.setattr(
        gui,
        "AppendMenu",
        lambda _m, flags, ident, text: items.append((flags, ident, text)),
    )
    monkeypatch.setattr(gui, "SetForegroundWindow", lambda _h: None)
    monkeypatch.setattr(gui, "TrackPopupMenu", lambda *a: None)
    monkeypatch.setattr(gui, "DestroyMenu", lambda _m: None, raising=False)
    monkeypatch.setattr(gui, "PostMessage", lambda *a: None, raising=False)
    return items


def _start_item(items: list[tuple[int, int, str]]) -> tuple[int, int, str]:
    return next(i for i in items if i[1] == system_tray._ID_START_WITH_WINDOWS)


def test_item_sits_above_the_separator_before_exit(
    entry: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _menu_items(monkeypatch)
    _tray()._show_menu(0, 0)
    ids = [i[1] for i in items]
    position = ids.index(system_tray._ID_START_WITH_WINDOWS)
    assert items[position][2] == "Start with Windows"
    assert ids[position + 1] == 0 and ids[position + 2] == system_tray._ID_QUIT


@pytest.mark.parametrize("on", [False, True])
def test_tick_follows_the_entry_each_time_the_menu_opens(
    entry: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, on: bool
) -> None:
    import win32con

    items = _menu_items(monkeypatch)
    entry.state["on"] = on
    _tray()._show_menu(0, 0)
    assert bool(_start_item(items)[0] & win32con.MF_CHECKED) is on
    items.clear()
    entry.state["on"] = not on
    _tray()._show_menu(0, 0)
    assert bool(_start_item(items)[0] & win32con.MF_CHECKED) is (not on)


def test_click_flips_the_entry_both_ways(entry: SimpleNamespace) -> None:
    tray = _tray()
    tray._toggle_start_with_windows()
    assert entry.state["on"] is True
    tray._toggle_start_with_windows()
    assert entry.state["on"] is False
    assert entry.calls == [True, False]


def test_command_id_reaches_the_toggle(
    entry: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(system_tray.win32api, "LOWORD", lambda w: w)
    _tray()._handle_context_menu_cb(5, 0, system_tray._ID_START_WITH_WINDOWS, 0)
    assert entry.state["on"] is True


def test_start_up_failures_never_break_the_tray(
    entry: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    import win32con

    items = _menu_items(monkeypatch)
    entry.state["raise_read"] = True
    _tray()._show_menu(0, 0)
    assert not _start_item(items)[0] & win32con.MF_CHECKED
    _tray()._toggle_start_with_windows()  # no exception
    entry.state["raise_read"] = False
    entry.state["on"] = False
    entry.state["fail"] = True
    _tray()._toggle_start_with_windows()
    assert entry.state["on"] is False


def test_off_in_windows_shows_unticked_and_click_opens_settings(
    entry: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    import win32con

    items = _menu_items(monkeypatch)
    entry.state["off_in_windows"] = True
    _tray()._show_menu(0, 0)
    flags, _ident, text = _start_item(items)
    assert not flags & win32con.MF_CHECKED
    assert text == "Start with Windows"
    _tray()._toggle_start_with_windows()
    assert entry.opened == [1]
    assert entry.calls == []  # nothing written

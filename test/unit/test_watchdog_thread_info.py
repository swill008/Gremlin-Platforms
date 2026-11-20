# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The freeze report's thread facts (gremlin/watchdog.py; 01 S113): the window
thread's kernel and user CPU time over half a second, and the windows and
low-level hooks that live on it."""

from __future__ import annotations

import sys

sys.path.append(".")

import logging
import re
import threading
import time
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore

from gremlin import watchdog

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def _helper(
    target: Callable[[threading.Event, threading.Event], None],
) -> tuple[threading.Thread, threading.Event]:
    stop = threading.Event()
    ready = threading.Event()
    t = threading.Thread(target=target, args=(stop, ready), name="ti-helper")
    t.start()
    assert ready.wait(5.0)
    return t, stop


def _ms(text: str) -> tuple[int, int]:
    m = re.search(r"kernel (\d+) ms, user (\d+) ms", text)
    assert m, text
    return int(m.group(1)), int(m.group(2))


def test_a_spinning_thread_shows_user_time_and_a_sleeping_one_almost_none() -> None:
    def spin(stop: threading.Event, ready: threading.Event) -> None:
        ready.set()
        while not stop.is_set():
            sum(range(1000))

    def sleep(stop: threading.Event, ready: threading.Event) -> None:
        ready.set()
        stop.wait(5.0)

    t, stop = _helper(spin)
    try:
        busy = watchdog.cpu_block(t.native_id)
    finally:
        stop.set()
        t.join(5.0)
    t, stop = _helper(sleep)
    try:
        idle = watchdog.cpu_block(t.native_id)
    finally:
        stop.set()
        t.join(5.0)
    assert busy.startswith("Main thread CPU over 0.5 s: kernel ")
    assert "% of one core)" in busy
    assert _ms(busy)[1] > 100
    assert sum(_ms(idle)) < 50


def test_a_hidden_window_on_the_thread_is_listed_by_class() -> None:
    import win32gui

    made: list[int] = []

    def make(stop: threading.Event, ready: threading.Event) -> None:
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = "TiHiddenWindowClass"  # pyright: ignore
        wc.lpfnWndProc = {}  # pyright: ignore
        atom = win32gui.RegisterClass(wc)
        made.append(win32gui.CreateWindow(atom, "x", 0, 0, 0, 0, 0, 0, 0, 0, None))
        ready.set()
        stop.wait(5.0)
        win32gui.DestroyWindow(made[0])

    t, stop = _helper(make)
    try:
        text = watchdog.windows_block(t.native_id)
    finally:
        stop.set()
        t.join(5.0)
    first = text.splitlines()[0]
    assert re.match(r"Main thread windows: \d+ \(", first)
    assert "TiHiddenWindowClass: 1" in first


def test_the_hooks_line_says_where_the_hooks_live() -> None:
    text = watchdog.hooks_block(threading.get_native_id())
    assert text.startswith("Low-level hooks on the main thread: ")


def test_a_bad_thread_gives_not_available_lines() -> None:
    assert "not available (" in watchdog.cpu_block(0xFFFFFFF0)
    assert "not available (" in watchdog.windows_block(0xFFFFFFF0)


def test_the_freeze_report_has_the_blocks_after_the_native_stack(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, text in (
        ("wait_chain_block", "Main thread wait chain: x"),
        ("native_stack_block", "Main thread native stack: y"),
        ("cpu_block", "Main thread CPU over 0.5 s: z"),
    ):
        monkeypatch.setattr(watchdog, name, lambda *a, t=text: t)
    done = threading.Event()
    real = watchdog.windows_block

    def spy(tid: int | None = None) -> str:
        out = real(tid)
        done.set()
        return out

    monkeypatch.setattr(watchdog, "windows_block", spy)
    caplog.set_level(logging.WARNING, logger="system")
    dog = watchdog.Watchdog(threshold_s=0.2)
    dog.start()
    try:
        assert done.wait(10.0)
        time.sleep(0.1)
    finally:
        dog.stop()
    text = caplog.text
    for a, b in (
        ("Main thread native stack", "Main thread CPU over"),
        ("Main thread CPU over", "Main thread windows:"),
        ("Main thread windows:", "Low-level hooks on the main thread:"),
    ):
        assert text.index(a) < text.index(b)

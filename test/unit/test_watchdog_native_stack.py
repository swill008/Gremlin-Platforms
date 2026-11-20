# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The freeze report's native stack (gremlin/watchdog.py; 01 S113): two
samples of the main thread's native stack, each frame named by the nearest
export of its module, so a busy (not waiting) freeze names the busy code."""

from __future__ import annotations

import sys

sys.path.append(".")

import ctypes
import logging
import platform
import threading
import time
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import watchdog

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or platform.machine().upper() not in ("AMD64", "X86_64"),
    reason="Windows x64 only",
)


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def _native_waiter(ms: int) -> tuple[threading.Thread, list[float]]:
    """A helper thread asleep in kernel32!Sleep; records when it finished."""
    took: list[float] = []

    def run() -> None:
        start = time.monotonic()
        ctypes.windll.kernel32.Sleep(ms)
        took.append(time.monotonic() - start)

    t = threading.Thread(target=run, name="ns-helper")
    t.start()
    while not t.native_id:
        pass
    time.sleep(0.2)  # let it reach Sleep
    return t, took


def test_sampling_a_blocked_thread_names_windows_frames_and_resumes_it() -> None:
    t, took = _native_waiter(1500)
    try:
        frames = watchdog.sample_native_stack(t.native_id)
    finally:
        t.join(5.0)
    joined = "\n".join(frames)
    assert any(m in joined for m in ("ntdll.dll!", "KERNELBASE.dll!", "KERNEL32.DLL!"))
    assert "python3" in joined.lower()  # walked up into the interpreter
    assert not t.is_alive()  # resumed: Sleep(1500) ended on time
    assert took and took[0] < 3.0


def test_the_block_has_two_samples_and_the_thread_finishes_on_time() -> None:
    t, took = _native_waiter(1500)
    try:
        text = watchdog.native_stack_block(t.native_id)
    finally:
        t.join(5.0)
    lines = text.splitlines()
    assert lines[0] == "Main thread native stack (Windows, 2 samples):"
    assert "  Sample 1:" in lines and "  Sample 2:" in lines
    assert not t.is_alive() and took and took[0] < 3.0


def test_an_export_address_is_named_by_its_export() -> None:
    k32 = ctypes.WinDLL("kernel32")
    get_proc = k32.GetProcAddress
    get_proc.restype = ctypes.c_void_p
    get_proc.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    k32.GetModuleHandleW.restype = ctypes.c_void_p
    module = k32.GetModuleHandleW("kernel32.dll")
    addr = get_proc(module, b"GetTickCount")
    name = watchdog.name_address(addr)
    assert name.lower().endswith("!gettickcount+0x0")
    assert name.lower().startswith(("kernel32.dll!", "kernelbase.dll!"))
    assert watchdog.name_address(addr + 3).lower().endswith("!gettickcount+0x3")


def test_a_bad_thread_id_gives_the_not_available_line() -> None:
    text = watchdog.native_stack_block(0xFFFFFFF0)
    assert text.startswith("Main thread native stack: not available (")


def test_the_own_thread_is_refused() -> None:
    text = watchdog.native_stack_block(threading.get_native_id())
    assert text.startswith("Main thread native stack: not available (")


def test_the_freeze_report_includes_the_native_stack_after_the_wait_chain(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        watchdog, "wait_chain_block", lambda: "Main thread wait chain (Windows):\n  Com"
    )
    done = threading.Event()
    real = watchdog.native_stack_block

    def spy(*args: object, **kwargs: object) -> str:
        out = real(*args, **kwargs)  # the pytest main thread: real sampling
        done.set()
        return out

    monkeypatch.setattr(watchdog, "native_stack_block", spy)
    caplog.set_level(logging.WARNING, logger="system")
    dog = watchdog.Watchdog(threshold_s=0.2)
    dog.start()
    try:
        # no main loop runs here: the beats stop; keep this thread in native
        # code (Sleep) so the sample has something to walk
        deadline = time.monotonic() + 10.0
        while not done.is_set() and time.monotonic() < deadline:
            ctypes.windll.kernel32.Sleep(50)
    finally:
        dog.stop()
    assert done.is_set()
    text = caplog.text
    assert "Main thread native stack (Windows, 2 samples):" in text
    assert text.index("Main thread wait chain") < text.index("Main thread native stack")

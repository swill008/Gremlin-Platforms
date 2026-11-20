# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The three emergency exits end the process with _end_at_once (01 S154,
user 2026-11-19), not os._exit, so Qt's DLL unload never runs."""

from __future__ import annotations

import ast
import pathlib
import sys
from typing import NoReturn

import pytest

import joystick_gremlin

_SRC = (pathlib.Path(__file__).resolve().parents[2] / "joystick_gremlin.py").read_text(
    encoding="utf-8"
)


def _calls_os_exit(func_name: str) -> list[int]:
    tree = ast.parse(_SRC)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return [
                c.lineno
                for c in ast.walk(node)
                if isinstance(c, ast.Call)
                and isinstance(c.func, ast.Attribute)
                and c.func.attr == "_exit"
            ]
    raise AssertionError(func_name)


def test_main_and_release_timeout_do_not_call_os_exit_directly() -> None:
    # Only the normal quit's final os._exit(0) stays in main().
    assert len(_calls_os_exit("main")) == 1
    assert _calls_os_exit("_release_timed_out") == []


def test_release_timed_out_ends_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    ends = []
    monkeypatch.setattr(joystick_gremlin, "_end_at_once", ends.append)
    joystick_gremlin._release_timed_out()
    assert ends == [0]


def test_startup_failure_ends_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    ends = []

    class _Done(Exception):
        pass

    def end(code: int) -> NoReturn:
        ends.append(code)
        raise _Done

    monkeypatch.setattr(joystick_gremlin, "_startup_failure", ("boom", "details"))
    monkeypatch.setattr(joystick_gremlin, "_log_startup_failure", lambda *a: None)
    monkeypatch.setattr(joystick_gremlin, "tell_could_not_start", lambda *a: None)
    monkeypatch.setattr(joystick_gremlin, "_end_at_once", end)
    with pytest.raises(_Done):
        joystick_gremlin.main()
    assert ends == [1]


def test_app_build_failure_ends_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    ends = []

    class _Done(Exception):
        pass

    def end(code: int) -> NoReturn:
        ends.append(code)
        raise _Done

    def boom(*a: object, **k: object) -> NoReturn:
        raise RuntimeError("no app")

    monkeypatch.setattr(joystick_gremlin, "_startup_failure", None)
    monkeypatch.setattr(joystick_gremlin, "_no_hooks_offscreen", lambda: None)
    monkeypatch.setattr(joystick_gremlin, "_check_second_copy", lambda: (None, True))
    monkeypatch.setattr(joystick_gremlin.gremlin.qt_log, "install", lambda *a: None)
    monkeypatch.setattr(joystick_gremlin, "JoystickGremlinApp", boom)
    monkeypatch.setattr(joystick_gremlin, "_log_startup_failure", lambda *a: None)
    monkeypatch.setattr(joystick_gremlin, "tell_could_not_start", lambda *a: None)
    monkeypatch.setattr(joystick_gremlin.gremlin.threads, "shutdown", lambda **k: None)
    monkeypatch.setattr(
        joystick_gremlin.gremlin.deferred_write, "flush_all", lambda: None
    )
    monkeypatch.setattr(joystick_gremlin.logging, "shutdown", lambda: None)
    monkeypatch.setattr(joystick_gremlin, "_end_at_once", end)
    with pytest.raises(_Done):
        joystick_gremlin.main()
    assert ends == [1]


@pytest.mark.skipif(sys.platform != "win32", reason="TerminateProcess")
def test_helper_flushes_and_terminates(monkeypatch: pytest.MonkeyPatch) -> None:
    import ctypes

    calls = []

    class _K32:
        class GetCurrentProcess:
            restype = None

            def __new__(cls) -> int:  # type: ignore[misc]
                return 123

        @staticmethod
        def TerminateProcess(handle: int, code: int) -> None:
            calls.append(("term", handle, code))

    class _Win:
        kernel32 = _K32

    monkeypatch.setattr(ctypes, "windll", _Win, raising=False)
    monkeypatch.setattr(
        joystick_gremlin.os, "_exit", lambda code: calls.append(("exit", code))
    )
    joystick_gremlin._end_at_once(7)
    assert calls[0] == ("term", 123, 7)
    assert calls[1] == ("exit", 7)

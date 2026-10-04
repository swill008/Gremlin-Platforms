# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""No error goes unrecorded (gremlin/error_report.py).

An error inside a program thread went to the console only, which the
installed program doesn't have. Now it is logged with the thread's name.
Top-level errors are logged and shown as before, and also reach a console.
A hard crash writes the stacks to crash.log in the logs folder.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import os
import pathlib
import subprocess
import threading

import pytest

import joystick_gremlin
from gremlin import error_report, threads

_ROOT = pathlib.Path(__file__).parents[2]


def _fail() -> None:
    raise RuntimeError("something broke in a thread")


def test_an_error_in_a_thread_is_logged_with_its_name(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(threading, "excepthook", error_report.thread_exception_hook)
    monkeypatch.setattr(sys, "stderr", None)  # like the installed program
    threads.start("failing work", _fail).join(2.0)
    assert "Error in Gremlin-Platforms: failing work" in caplog.text
    assert "something broke in a thread" in caplog.text


def test_a_thread_ending_with_system_exit_is_not_an_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(threading, "excepthook", error_report.thread_exception_hook)

    def leave() -> None:
        raise SystemExit

    threads.start("leaving", leave).join(2.0)
    assert "Error in" not in caplog.text


def test_a_top_level_error_is_logged_shown_and_passed_on(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    shown: list[tuple[str, str]] = []
    passed_on: list[type[BaseException]] = []
    monkeypatch.setattr(
        joystick_gremlin.gremlin.signal, "display_error",
        lambda message, details: shown.append((message, details)),
    )
    monkeypatch.setattr(sys, "__excepthook__", lambda kind, *_: passed_on.append(kind))
    try:
        raise ValueError("top level")
    except ValueError as e:
        joystick_gremlin.exception_hook(type(e), e, e.__traceback__)
    assert "Unhandled exception" in caplog.text and "top level" in caplog.text
    assert shown and "top level" in shown[0][1]
    assert passed_on == [ValueError]


def test_without_a_console_nothing_is_passed_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    passed_on: list[object] = []
    monkeypatch.setattr(sys, "__excepthook__", lambda *a: passed_on.append(a))
    monkeypatch.setattr(sys, "stderr", None)
    error_report.pass_on(ValueError, ValueError("x"), None)
    assert passed_on == []


def test_the_crash_log_is_turned_on_in_the_logs_folder(tmp_path: pathlib.Path) -> None:
    # In its own process: faulthandler is per process, and pytest has it on.
    code = (
        "import faulthandler, pathlib, sys\n"
        "sys.path.insert(0, '.')\n"
        "faulthandler.disable()\n"
        "from gremlin import error_report\n"
        f"path = error_report.enable_crash_log(pathlib.Path({str(tmp_path)!r}))\n"
        "print('PATH', path, faulthandler.is_enabled())\n"
        "print('AGAIN', error_report.enable_crash_log(pathlib.Path('.')))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=_ROOT, capture_output=True, text=True,
        timeout=60, env=dict(os.environ),
    )
    assert f"PATH {tmp_path / 'crash.log'} True" in result.stdout, result.stderr
    assert "AGAIN None" in result.stdout  # already on: left alone
    assert (tmp_path / "crash.log").exists()

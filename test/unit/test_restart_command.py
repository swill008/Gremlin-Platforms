# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from gremlin.util import restart_command


def test_packaged_exe_restarts_itself_with_the_same_arguments() -> None:
    program, args = restart_command(
        ["gremlin_platforms.exe", "--profile", "a.xml"],
        r"C:\app\joystick_gremlin.py",
        True,
        r"C:\app\gremlin_platforms.exe",
    )
    assert program == r"C:\app\gremlin_platforms.exe"
    assert args == ["--profile", "a.xml"]


def test_source_run_restarts_python_with_the_script() -> None:
    program, args = restart_command(
        ["joystick_gremlin.py", "--enable"],
        r"E:\repo\joystick_gremlin.py",
        False,
        r"C:\venv\Scripts\python.exe",
    )
    assert program == r"C:\venv\Scripts\python.exe"
    assert args == [r"E:\repo\joystick_gremlin.py", "--enable"]

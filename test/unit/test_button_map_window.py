# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map window loads, and its dialogs open, without QML errors."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_HERE = pathlib.Path(__file__).parent

# Pictures that only exist in a full checkout with the stock photos.
_IGNORED = ("vkb_gladiator_rig.jpg",)


def test_window_and_dialogs_open_cleanly(tmp_path: pathlib.Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_HERE / "button_map_window_smoke.py"), str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stderr[-2000:]
    problems = [
        line
        for line in lines
        if line.startswith(("ERROR", "WARN"))
        and not any(name in line for name in _IGNORED)
    ]
    assert problems == []

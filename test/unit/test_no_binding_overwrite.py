# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""No "Overwriting binding" warning when the program starts and the Button
Map opens: a property is never set over its own binding (the user saw one
for the Button Map card's chipRows, 2026-10-09). Spec: none (no behaviour
change)."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_SMOKE = pathlib.Path(__file__).resolve().parent / "no_binding_overwrite_smoke.py"
_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_no_binding_is_overwritten_opening_the_button_map(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(tmp_path),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        QT_LOGGING_RULES="qt.qml.binding.removal.info=true",
        PYTHONIOENCODING="utf-8",
    )
    done = subprocess.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    out = done.stdout + done.stderr
    assert "done" in done.stdout.splitlines(), out[-3000:]
    bad = [line for line in out.splitlines() if "Overwriting binding" in line]
    assert bad == [], bad

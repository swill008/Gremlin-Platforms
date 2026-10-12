# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""No qt.qml.binding.removal line ("Overwriting binding") when the main
window and the main tool windows open: Help on a topic with program links,
the Device Mapping Editor, Options and the list windows. A `({})` / `([])`
starting value is a binding, and a later assignment logged one (DialogHelp
_linkReasons, 2026-10-12). Runs no_binding_removal_smoke.py in its own
process with a fresh user folder. Spec: none (no behaviour change)."""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

_SMOKE = pathlib.Path(__file__).resolve().parent / "no_binding_removal_smoke.py"
_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_no_binding_removal_opening_the_main_windows(tmp_path: pathlib.Path) -> None:
    (tmp_path / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(tmp_path),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        QT_LOGGING_RULES="qt.qml.binding.removal.info=true",
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, str(_SMOKE)], cwd=_ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", timeout=150,
    )
    out = done.stdout + done.stderr
    lines = done.stdout.splitlines()
    assert "done" in lines, out[-3000:]
    # The Help step reached a topic with an Open › / Show me › link.
    topic = [ln for ln in lines if ln.startswith("HELP_TOPIC ")]
    assert topic and topic[0].strip() != "HELP_TOPIC", out[-3000:]
    bad = [line for line in out.splitlines() if "Overwriting binding" in line]
    assert bad == [], bad

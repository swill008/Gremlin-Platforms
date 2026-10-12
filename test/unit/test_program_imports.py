# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""joystick_gremlin.py loads on its own, as the built program does.

The other tests import gremlin modules before joystick_gremlin, which hides
an import order problem in it: 1.0.18 did not start (a circular import
between gremlin.osc_persist and gremlin.ui.backend) while every test passed.
"""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]


def test_program_loads_in_a_fresh_process(tmp_path: pathlib.Path) -> None:
    env = dict(os.environ)
    env["USERPROFILE"] = str(tmp_path)
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = proc_tree.run(
        [sys.executable, "-c", "import joystick_gremlin"],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, smoke_report.explain(result)

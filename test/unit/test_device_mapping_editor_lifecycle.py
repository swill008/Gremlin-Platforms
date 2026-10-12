# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor loads only when opened and leaves nothing behind when
closed: the window is destroyed, the shared command list (Gremlin.Menus)
holds none of its commands, and opening it again and again does not make
the program grow."""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).parent


def test_device_mapping_editor_leaves_nothing_behind() -> None:
    result = proc_tree.run(
        [sys.executable, str(_HERE / "device_mapping_editor_lifecycle_smoke.py")],
        text=True,
        encoding="utf-8",
        timeout=180,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, smoke_report.explain(result)
    assert not [line for line in lines if line.startswith("ERROR")]
    results = dict(
        line.split(" ", 2)[1:] for line in lines if line.startswith("RESULT ")
    )
    memory = {
        line.split()[1]: float(line.split()[2])
        for line in lines
        if line.startswith("MEM ")
    }
    # No Command Palette (07 S100): no commands in the shared list; its own
    # small windows open, and close with it.
    assert results["during"] == "0"
    assert results["shortcuts"] == "True"
    assert results["options"] == "True"
    for cycle in range(3):
        assert results[f"opened{cycle}"] == "True"
        assert results[f"gone{cycle}"] == "True"
        assert results[f"left{cycle}"] == "0"
    # Opening and closing it again does not pile memory up.
    assert memory["closed2"] - memory["closed0"] < 8

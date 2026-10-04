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
    results = {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }
    # Menus show only what can be used: no device, no editing tools...
    assert results["file-menu"].split("|")[-2:] == ["---", "Close"]
    assert "Save" not in results["file-menu"]
    assert "Export PDF" not in results["file-menu"]
    # ...and with a device, its exports, never two separators in a row.
    with_device = results["file-menu-device"].split("|")
    assert "Edit Mapping" in with_device and "Save" not in with_device
    # Every print and export is in Print & Export, the File menu's one entry.
    assert "Print & Export…" in with_device
    for gone in ("Export PDF…", "Export PNG…", "Export JPG…", "Print…",
                 "Export Modes…", "Light Page for Exports"):
        assert gone not in with_device
    assert all(
        not (a == "---" and b == "---") for a, b in zip(with_device, with_device[1:])
    )
    assert with_device[0] != "---" and with_device[-1] != "---"
    # An edit can be undone; after Cancel there is nothing left to undo.
    assert results["undo-after-cancel"] == "true false"
    # A map without a photo frame value is not rescaled or rewritten.
    assert results["plain-file"] == "true true"
    # Ctrl+V pastes a picture copied after the last chip copy; a dropped
    # picture is centred on the drop point with its own 4:1 shape.
    assert results["paste-picture"] == "1 image"
    assert results["drop-picture"] == "true 0.30 0.60 4.0"
    # Entering Edit leaves nothing to undo or save (BM11).
    assert results["edit-is-clean"] == "false false"
    # Copy Button Map from Device outside Edit: Undo brings the old map
    # back (BM9).
    assert results["copy-undo"] == "c1 p1"
    # Ctrl+S while typing keeps the typed text (BM15).
    assert results["save-while-typing"] == "['typed']"
    # A typed hex sets the colour, and the field shows it in full (BM17).
    assert results["typed-hex"] == "#aabbcc #aabbcc"

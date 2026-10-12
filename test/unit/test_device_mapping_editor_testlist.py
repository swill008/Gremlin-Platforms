# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor, D-TESTLIST-1 items 3 and 4 (07 S138): the view-only
banner's two texts and its "File › Device" link; an edit's just-added picture
is let go before the edit's temporary folder goes (the CI warning
"RigDrawItem.qml:419 Cannot open .../cache/edit/<id>/added/wide_1.png")."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).resolve().parent


def _run(tmp_path: pathlib.Path) -> tuple[dict, list[str]]:
    result = proc_tree.run(
        [
            sys.executable,
            str(_HERE / "device_mapping_editor_testlist_smoke.py"),
            str(tmp_path),
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"},
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stderr[-2000:]
    assert not [line for line in lines if line.startswith("ERROR")], lines
    results = {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }
    warns = [line for line in lines if line.startswith("WARN")]
    return results, warns


def test_banner_and_edit_pictures(tmp_path: pathlib.Path) -> None:
    results, warns = _run(tmp_path)
    # No device chosen: how to choose one; "File › Device" is a link.
    none = json.loads(results["banner-none"])
    assert none["banner"] is True
    assert none["text"] + none["deviceText"] + none["tail"] == (
        "No device chosen. Choose one from File › Device, then File › Edit "
        "Mapping to edit its device map."
    )
    assert none["device"] is True and none["edit"] is False
    # The link opens the File menu with its Device list out.
    opened, after = results["device-link"].split(" ", 1)
    assert json.loads(opened) == {"ok": True, "file": True, "device": True}
    assert json.loads(after) == {"file": True, "device": True}
    # A device chosen: today's text with the Edit Mapping link.
    chosen = json.loads(results["banner-device"])
    assert chosen["text"] + "Edit Mapping" + chosen["tail"] == (
        "View only. To edit this device map, choose File › Edit Mapping."
    )
    assert chosen["device"] is False and chosen["edit"] is True
    # A picture dropped and the edit discarded at once: the editor no longer
    # loads it from the folder that went, and nothing warns.
    dropped = json.loads(results["drop-discard"])
    assert dropped["ok"] is True and dropped["count"] == 1
    assert json.loads(results["held-missing"]) == []
    assert not [w for w in warns if "Cannot open" in w], warns

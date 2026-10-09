# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Button Map editor off-screen through commands that follow a
waiting run of edits (07 S55: one undo step per command) and prints the
results as JSON. test_rig_undo_steps.py runs it in its own process.

    python test/unit/rig_undo_steps_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore  # noqa: E402

Key = QtCore.Qt.Key


def _ids(s: h.Session) -> list[str]:
    return [n["id"] for n in s.state()["nodes"]]


def main() -> None:
    s = h.Session(Path(os.environ.get("TEMP", ".")), "undo_steps")
    out: dict[str, object] = {}
    h._load(s, "evo_r")
    # Runs stay open until end_run(), so "within the pause" holds on any PC.
    s.hold_runs()

    # Arrow nudges, then (before they pause) a drawing: two undo steps.
    s.call("setSelection", ["b3"])
    start = s.node("b3")["chipFx"]
    at0 = s.call_prop("histAt")
    for _ in range(3):
        s.key(Key.Key_Right)
    nudged = s.node("b3")["chipFx"]
    waiting = s.call_prop("stepWaiting")
    ids_before = _ids(s)
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.35), s.point(0.15, 0.48))
    s.call("setDrawTool", "")
    drawn = s.state()["selected"][0]
    out["nudge-draw"] = {
        "waiting": waiting,
        "moved": nudged != start,
        "steps": s.call_prop("histAt") - at0,
    }
    s.call("undo")
    out["nudge-draw"]["undo1"] = {
        "drawing-gone": drawn not in _ids(s) and _ids(s) == ids_before,
        "nudge-kept": s.node("b3")["chipFx"] == nudged,
    }
    s.call("undo")
    out["nudge-draw"]["undo2"] = {"nudge-undone": s.node("b3")["chipFx"] == start}
    s.end_run()

    # Color picker drag, then a plain field change: two undo steps.
    s.call("setSelection", ["b3"])
    at0 = s.call_prop("histAt")
    color0 = s.node("b3").get("color")
    for i in range(5):
        s.call("applyFieldLive", "color", f"#30{i:02X}50")
    s.call("applyField", "chipSize", 31)
    out["live-field"] = {"steps": s.call_prop("histAt") - at0}
    s.call("undo")
    n = s.node("b3")
    out["live-field"]["undo1"] = [n.get("color"), n.get("chipSize")]
    s.call("undo")
    out["live-field"]["undo2"] = s.node("b3").get("color") == color0
    s.end_run()

    # The run's own step lands when it pauses, holding the state after it.
    at0 = s.call_prop("histAt")
    s.call("setSelection", ["b3"])
    s.key(Key.Key_Down)
    s.key(Key.Key_Down)
    moved = s.node("b3")["chipFy"]
    s.end_run()
    out["pause"] = {"steps": s.call_prop("histAt") - at0}
    s.call("undo")
    s.call("redo")
    out["pause"]["redo-state"] = s.node("b3")["chipFy"] == moved

    # Add Callout for a chip: one undo step, and one Undo removes it.
    chip = s.call("placedId", "btn", 6)
    ids_before = _ids(s)
    at0 = s.call_prop("histAt")
    s.call("addCalloutFor", chip)
    added = s.state()["selected"][0]
    out["callout"] = {
        "added": added not in ids_before,
        "tail": s.node(added).get("tail"),
        "chip": chip,
        "steps": s.call_prop("histAt") - at0,
    }
    s.call("undo")
    out["callout"]["undo-removes"] = _ids(s) == ids_before

    # Nudges, then Add Callout before the pause: the callout's Undo leaves
    # the nudges.
    s.call("setSelection", [chip])
    s.key(Key.Key_Left)
    nudged = s.node(chip)["chipFx"]
    ids_before = _ids(s)
    s.call("addCalloutFor", chip)
    s.call("undo")
    out["nudge-callout"] = {
        "callout-gone": _ids(s) == ids_before,
        "nudge-kept": s.node(chip)["chipFx"] == nudged,
    }

    out["warnings"] = s.warnings
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

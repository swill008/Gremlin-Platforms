# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen through three audit fixes and
prints what it saw as one "FIXSEL {json}" line (test_dme_audit_fix_sel.py
runs it in its own process):

- Paste lands in the plane being edited (07 S116, S119, S121).
- Backspace while drawing a path takes back its last point (07 S134).
- A table cell target left stale by Undo or another table is dropped.

    python test/unit/dme_audit_fix_sel_smoke.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from planes_editor_smoke import _rect  # noqa: E402
from PySide6 import QtCore  # noqa: E402
from rig_editor_harness import Session, _load  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402

TARGET = ["tableRow", "tableCol", "tableExtra"]


def _table(id_: str, fx: float, fy: float) -> dict:
    return dict(_rect(id_, fx, fy), shape="table", fw=0.2, fh=0.12)


def main() -> None:
    out: dict = {}
    s = Session(Path("."), "fixsel")
    s.hold_runs()
    _load(s, "evo_r")
    doc = s.state()["nodes"] + [
        _rect("bgA", 0.02, 0.80, "background"),
        _rect("fgR", 0.60, 0.80),
        _table("tA", 0.10, 0.10),
        _table("tB", 0.50, 0.10),
    ]
    s.js("setNodes", json.dumps(doc))
    s.wait(400)
    s.call("seedHist")

    def target() -> list:
        return [s.call_prop(k) for k in TARGET]

    def planes(ids: list) -> list:
        return [s.node(i).get("plane", "") for i in ids]

    # 1. Paste: a copied background item pasted in Foreground mode.
    before = {n["id"] for n in s.state()["nodes"]}
    s.call("setSelection", [])
    s.call("pasteNodes", [s.node("bgA")], 0.01, 0.01)
    sel = s.state()["selected"]
    out["paste_fg_new"] = [i for i in sel if i not in before]
    out["paste_fg_planes"] = planes(sel)
    out["paste_fg_in_edit_plane"] = [s.call("inEditPlane", s.node(i)) for i in sel]
    # ... and a foreground item pasted in Background mode.
    s.set_prop("editPlane", "background")
    s.call("pasteNodes", [s.node("fgR")], 0.01, 0.01)
    sel = s.state()["selected"]
    out["paste_bg_planes"] = planes(sel)
    out["paste_bg_in_edit_plane"] = [s.call("inEditPlane", s.node(i)) for i in sel]
    s.set_prop("editPlane", "foreground")

    # 2. Backspace while drawing a path, with a chip selected.
    chip = next(n["id"] for n in s.state()["nodes"] if n.get("kind") == "btn")
    s.call("setSelection", [chip])
    s.call("setDrawTool", "path")
    for fx, fy in ((0.1, 0.6), (0.2, 0.7), (0.3, 0.6)):
        p = s.point(fx, fy)
        s.call("pathClick", p.x(), p.y())
    n_nodes = len(s.state()["nodes"])
    out["path_before"] = len(s.call_prop("pathDraft"))
    s.key(QtCore.Qt.Key.Key_Backspace)
    out["path_after"] = len(s.call_prop("pathDraft"))
    ids = [n["id"] for n in s.state()["nodes"]]
    out["path_chip_kept"] = chip in ids and len(ids) == n_nodes
    s.call("cancelPath")
    s.call("setDrawTool", "")

    # 3a. Spawn Empty Cell, Undo: Delete then deletes the table.
    s.call("setSelection", ["tA"])
    s.call("seedHist")
    s.call("spawnEmptyCell")
    s.end_run()
    out["spawned_extras"] = len(s.node("tA").get("extras") or [])
    s.call("undo")
    s.wait(100)
    s.call("setSelection", ["tA"])
    out["after_undo_extras"] = len(s.node("tA").get("extras") or [])
    try:
        out["after_undo_valid"] = s.call("tableTargetValid")
    except Exception as error:  # noqa: BLE001  (old code: no such function)
        out["after_undo_valid"] = repr(error)
    out["delete_result"] = s.call("deleteSelected")
    out["tA_gone"] = not any(n["id"] == "tA" for n in s.state()["nodes"])

    # 3b. A cell target on one table does not carry to another.
    s.call("setSelection", ["tB"])
    s.set_prop("tableRow", 0)
    s.set_prop("tableCol", 1)
    s.call("setSelection", ["fgR", "tB"])
    out["same_table_kept"] = target()
    s.call("setSelection", ["bgA"])
    s.call("setSelection", ["tB"])
    out["other_selection_reset"] = target()

    out["warnings"] = sorted(set(s.warnings))
    print("FIXSEL " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

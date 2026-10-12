# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen for a Shift/Ctrl+right-click on an
item that isn't selected: the item joins the selection, so the menu and its
rows act on what the menu names. Prints the results as JSON;
test_dme_audit_fix_ptr.py runs it in its own process.

    python test/unit/dme_audit_fix_ptr_smoke.py <folder>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore  # noqa: E402

Q = QtCore.Qt


def _menu(s: h.Session) -> dict:
    model = s.call("menuModel")
    assert isinstance(model, dict)
    return {"kind": model.get("kind"), "title": model.get("title")}


def _sel(s: h.Session) -> dict:
    st = s.state()
    return {"selected": st["selected"], "ids": s.call_prop("selectedIds")}


def _ids(s: h.Session) -> list[str]:
    return [n["id"] for n in s.state()["nodes"]]


def _mod_right_click(s: h.Session, id_: str, mods: Q.KeyboardModifier) -> None:
    s._mouse("mouseClick", s.center(id_), button=Q.MouseButton.RightButton, mods=mods)
    s.wait(150)


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "bm_audit_fix_ptr")
    s.hold_runs()
    out: dict[str, object] = {}
    h._load(s, "evo_r")

    for name, mods in (("shift", Q.KeyboardModifier.ShiftModifier),
                       ("ctrl", Q.KeyboardModifier.ControlModifier)):
        s.click(s.center("b3"))
        s.wait(100)
        _mod_right_click(s, "b4", mods)
        out[name] = {**_sel(s), "menu": _menu(s)}
        s.close_menus()

    # Delete from that menu removes both items it names, and only them.
    s.click(s.center("b3"))
    s.wait(100)
    before = _ids(s)
    _mod_right_click(s, "b4", Q.KeyboardModifier.ShiftModifier)
    rows = s.state()["menu"]
    delete_rows = [r for r in rows if isinstance(r, str) and r.startswith("Delete")]
    out["delete-rows"] = delete_rows
    row = delete_rows[0] if delete_rows else ""
    s.click_menu_row(row.split(" (")[0])
    s.wait(150)
    after = _ids(s)
    out["deleted"] = sorted(set(before) - set(after))
    s.close_menus()
    s.key(Q.Key.Key_Z, Q.KeyboardModifier.ControlModifier)
    s.wait(150)

    # A plain right-click on an unselected item still selects just it.
    s.click(s.center("b3"))
    s.wait(100)
    s.right_click(s.center("b5"))
    out["plain"] = {**_sel(s), "menu": _menu(s)}
    s.close_menus()

    out["warnings"] = sorted({w for w in s.warnings if "RigPointerArea" in w})
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

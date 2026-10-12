# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen for the empty-space right-click
menu's plane switch (07 S113): Edit Background in Foreground mode, Exit
Background Editing in Background mode, Ctrl+B beside it, only while editing.
Prints the results as JSON; test_canvas_menu_planes.py runs it in its own
process.

    python test/unit/canvas_menu_planes_smoke.py <folder>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402


def _quick(s: h.Session) -> dict:
    """The open menu's kind, title, quick rows and header, from the model."""
    model = s.call("menuModel")
    assert isinstance(model, dict)
    return {
        "kind": model.get("kind"),
        "title": model.get("title"),
        "quick": [{"name": i.get("name", ""), "text": i.get("text"),
                   "hint": i.get("hint"), "enabled": i.get("enabled")}
                  for i in model.get("quick") or []],
        "header": [i.get("label") for i in model.get("header") or []],
        "sections": [sect.get("key") for sect in model.get("sections") or []],
    }


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "canvas_menu_planes")
    out: dict[str, object] = {}
    h._load(s, "evo_r")
    empty = s.point(0.1, 0.5)

    s.right_click(empty)
    out["fg"] = _quick(s)
    s.click_menu_row("Edit Background")
    s.wait(150)
    out["after-enter"] = s.call_prop("editPlane")
    s.close_menus()

    s.right_click(empty)
    out["bg"] = _quick(s)
    s.click_menu_row("Exit Background Editing")
    s.wait(150)
    out["after-exit"] = s.call_prop("editPlane")
    s.close_menus()

    # Not while viewing.
    s.js("setEditing", False)
    s.wait(150)
    out["viewing-interactive"] = s.call_prop("interactive")
    out["viewing"] = _quick(s)
    out["warnings"] = sorted({w for w in s.warnings if "rig_menu" in w})
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

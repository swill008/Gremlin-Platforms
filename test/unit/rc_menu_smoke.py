# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen for the right-click additions
(07 S136, S137): command tags (cmd) on the rows that are commands, Cut beside
Copy, Paste Here and Select All on empty space, Show in Layers and
Properties… on every item, Repeat first, and the Favourites list. Prints the
results as JSON; test_rc_menu.py runs it in its own process.

    python test/unit/rc_menu_smoke.py <folder>
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402


def _row(i: dict) -> dict:
    return {
        "name": i.get("name", ""),
        "text": i.get("text"),
        "hint": i.get("hint", ""),
        "enabled": i.get("enabled"),
        "cmd": i.get("cmd", ""),
        "kind": i.get("kind"),
    }


def _model(s: h.Session) -> dict:
    """The open menu's rows, from the model the menu draws."""
    model = s.call("menuModel")
    assert isinstance(model, dict)
    return {
        "kind": model.get("kind"),
        "quick": [_row(i) for i in model.get("quick") or []],
        "sections": {
            sect.get("key"): [_row(i) for i in sect.get("items") or []]
            for sect in model.get("sections") or []
        },
        "favourites": [_row(i) for i in model.get("favourites") or []],
    }


def _safe(fn: Callable[..., object], *args: object) -> object:
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001  (reported, not raised)
        return f"error: {e}"


def _edge(s: h.Session, id_: str) -> object:
    """A point on a hollow shape's left outline (its middle is empty)."""
    b = s._box(id_)
    return s.ed_point(b["x"] + 1, b["y"] + b["h"] / 2)


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "rc_menu")
    out: dict[str, object] = {}
    h._load(s, "evo_r")
    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]

    # A chip.
    s.right_click(s.center(chips[0]))
    out["chip"] = _model(s)
    s.close_menus()

    # Empty space.
    s.right_click(s.point(0.1, 0.5))
    out["canvas"] = _model(s)
    s.close_menus()

    # A rectangle: drawn, copied, pasted at a spot right-clicked.
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.10), s.point(0.15, 0.20))
    s.call("setDrawTool", "")
    rect = s.state()["selected"][0]
    out["rect"] = rect
    s.right_click(_edge(s, rect))
    out["shape"] = _model(s)
    s.close_menus()

    s.call("copySelection")
    before = {n["id"] for n in s.state()["nodes"]}
    spot = s.point(0.12, 0.70)
    s.right_click(spot)
    _safe(s.click_menu_row, "Paste Here")
    s.wait(150)
    new = [n["id"] for n in s.state()["nodes"] if n["id"] not in before]
    out["pasted"] = new
    if new:
        c = s.center(new[0])
        out["pasteCentre"] = [c.x(), c.y()]
    out["pasteSpot"] = [spot.x(), spot.y()]
    s.close_menus()

    # Repeat after a right-click command.
    s.right_click(_edge(s, rect))
    _safe(s.open_menu_section, "Rotate and Flip")
    out["flipClick"] = _safe(s.click_menu_row, "Flip Horizontally")
    s.wait(150)
    s.close_menus()
    s.right_click(_edge(s, rect))
    out["afterFlip"] = _model(s)
    s.close_menus()

    # Favourites: in the order added, only what applies, at most the count.
    out["setFav"] = _safe(
        s.set_prop, "favourites", ["group", "flipH", "edit.selectAll", "rotatePlus"]
    )
    for shown in (5, 2, 0):
        _safe(s.set_prop, "favouritesShown", shown)
        s.right_click(_edge(s, rect))
        out[f"fav{shown}"] = _model(s)["favourites"]
        s.close_menus()

    out["warnings"] = sorted({w for w in s.warnings if "rig_menu" in w})
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

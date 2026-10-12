# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen for the right-click Hide / Lock
rows (D-FIXLIST-B1 item 2): an item's Hide and Lock rows carry the hide /
lock command ids (so the menu offers the ☆), clicking the row acts on what
was right-clicked, a Hide favourite hides the whole selection, and the
hotspot and leader rows stay without a command. Prints the results as JSON;
test_b1_menu.py runs it in its own process.

    python test/unit/b1_menu_smoke.py <folder>
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path

from PySide6 import QtCore, QtQuick
from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402


def _rows(s: h.Session) -> list[dict]:
    model = s.call("menuModel")
    assert isinstance(model, dict)
    return [
        {"text": i.get("text"), "kind": i.get("kind"), "cmd": i.get("cmd", "")}
        for i in model.get("quick") or []
    ]


def _hide_lock(rows: list[dict]) -> list[dict]:
    return [r for r in rows if str(r["text"]).startswith(("Hide ", "Lock "))]


def _items(it: QtQuick.QQuickItem) -> Iterator[QtQuick.QQuickItem]:
    """Every item under it (the visual tree; QML parents differ)."""
    yield it
    for child in it.childItems():
        yield from _items(child)


def _menu_target(s: h.Session) -> QtCore.QObject | None:
    """The right-click target the map's pointer area fills in (_ctx)."""
    for item in _items(s.win.contentItem()):
        t = item.property("menuTarget")
        if isinstance(t, QtCore.QObject):
            return t
    return None


def _star(s: h.Session, cmd: str) -> bool:
    name = "ctxStar_" + cmd
    return any(o.objectName() == name for o in _items(s.win.contentItem()))


def _flag(s: h.Session, id_: str, flag: str) -> bool:
    return bool(s.call("layerFlag", id_, "", flag))


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "b1_menu")
    out: dict[str, object] = {}
    h._load(s, "evo_r")
    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]
    a, b, c = chips[0], chips[1], chips[2]

    # One chip: the rows and their ☆.
    s.right_click(s.center(a))
    out["chip"] = _hide_lock(_rows(s))
    out["starHide"] = _star(s, "hide")
    out["starLock"] = _star(s, "lock")

    # Its hotspot and a leader: the rows act on a part, no command.
    target = _menu_target(s)
    out["foundTarget"] = target is not None
    if target is not None:
        target.setProperty("kind", "hot")
        out["hotspot"] = _hide_lock(_rows(s))
        target.setProperty("kind", "spine")
        out["leader"] = _hide_lock(_rows(s))
        target.setProperty("kind", "")
    s.close_menus()

    # A drawn rectangle.
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.10), s.point(0.15, 0.20))
    s.call("setDrawTool", "")
    rect = s.state()["selected"][0]
    b_ = s._box(rect)
    s.right_click(s.ed_point(b_["x"] + 1, b_["y"] + b_["h"] / 2))
    out["shape"] = _hide_lock(_rows(s))
    s.close_menus()

    # Several selected.
    s.click(s.center(a))
    s.click(s.center(b), QtCore.Qt.KeyboardModifier.ControlModifier)
    s.right_click(s.center(a))
    out["multi"] = _hide_lock(_rows(s))
    s.close_menus()

    # Clicking the row itself: Lock Chip locks only the chip right-clicked.
    s.click(s.center(c))
    s.right_click(s.center(c))
    lock = [r["text"] for r in _hide_lock(_rows(s)) if r["text"].startswith("Lock ")]
    s.click_menu_row(lock[0])
    s.wait(100)
    s.close_menus()
    out["rowLock"] = {"c": _flag(s, c, "locked"), "a": _flag(s, a, "locked")}

    # A Hide favourite: hides the whole selection (like Ctrl+Shift+H).
    s.set_prop("favourites", ["hide"])
    s.set_prop("favouritesShown", 5)
    s.click(s.center(a))
    s.click(s.center(b), QtCore.Qt.KeyboardModifier.ControlModifier)
    s.right_click(s.center(a))
    fav = s.call("menuModel")
    out["favRows"] = [f.get("text") for f in (fav or {}).get("favourites") or []]
    if out["favRows"]:
        s.click_menu_row(out["favRows"][0])
    s.wait(100)
    s.close_menus()
    out["favHide"] = {"a": _flag(s, a, "hidden"), "b": _flag(s, b, "hidden")}

    out["warnings"] = sorted({w for w in s.warnings if "rig_menu" in w})
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

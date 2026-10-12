# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen for Reset Picture (07,
D-07-RESET-PICTURE) and Reset Shape on a turned picture (07 S42): the
right-click menu's Picture section, the Properties panel's button, one Undo
step, several pictures at once and a locked picture. Prints the results as
JSON; test_reset_picture.py runs it in its own process.

    python test/unit/reset_picture_smoke.py <picture folder>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtGui, QtQuick  # noqa: E402

_EXTRA = """
    function rpSetAspectFn(a) {
        _face.editorItem.imageAspectFn = function(rel) { return a }
    }
}
"""
h._HOST = h._HOST.rstrip()[:-1] + _EXTRA.encode()

# What Reset Picture clears and what it keeps (D-07-RESET-PICTURE 2a).
_KEYS = ("fx", "fy", "fw", "fh", "rot", "flipH", "flipV", "crop", "skew",
         "adj", "opacity", "sockets", "src", "plane", "name", "hidden",
         "locked", "look")


def _picture(folder: Path, name: str, w: int, h_: int) -> str:
    path = folder / name
    img = QtGui.QImage(w, h_, QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtGui.QColor("#3080C0"))
    assert img.save(str(path))
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def _image(id_: str, url: str, **extra: object) -> dict:
    n = {"id": id_, "kind": "draw", "shape": "image", "src": "pictures/small.png",
         "srcUrl": url, "fx": 0.30, "fy": 0.30, "fw": 0.10, "fh": 0.10,
         "rot": 0, "opacity": 1, "locked": False, "pinned": False,
         "sockets": [], "fill": "filled"}
    n.update(extra)
    return n


def _pick(n: dict) -> dict:
    return {k: n.get(k) for k in _KEYS}


def _picture_rows(s: h.Session) -> list:
    """The Picture section's rows (text, enabled), in order."""
    for sect in s.call("menuModel").get("sections") or []:
        if sect.get("key") == "image":
            return [[i.get("text"), i.get("enabled")] for i in sect["items"]]
    return []


def _shape_row(s: h.Session) -> object:
    for sect in s.call("menuModel").get("sections") or []:
        for item in sect.get("items") or []:
            if item.get("text") == "Reset Shape":
                return item.get("enabled")
    return None


def _open_section(s: h.Session, title: str) -> None:
    """Opens a menu section. A header click right after another click is
    sometimes lost off-screen, so it is tried again (up to 3)."""
    for _ in range(3):
        if ("v " + title) in s.state()["menu"]:
            return
        s.click_menu_row(title)
        s.wait(150)


def _run_row(s: h.Session, text: str) -> None:
    """Clicks an action row; the menu closes when it runs. A click lost the
    same way as above is tried again (up to 3)."""
    for _ in range(3):
        s.click_menu_row(text)
        s.wait(150)
        if not s.state()["menu"]:
            return


def _find(item: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem | None:
    for child in item.childItems():
        if child.objectName() == name and child.isVisible():
            return child
        found = _find(child, name)
        if found is not None:
            return found
    return None


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "reset_picture")
    out: dict[str, object] = {}
    url = _picture(folder, "small.png", 200, 100)
    h._load(s, "evo_r")
    s.js("rpSetAspectFn", 2)
    base = s.state()["nodes"]

    # What a fresh add of this picture gets today (the editor's add rule).
    s.js("setNodes", json.dumps(base))
    s.wait(200)
    fresh_id = s.call("addOverlay", "pictures/small.png", url, {"aspect": 2})
    fresh = s.node(fresh_id)
    out["fresh"] = {"fw": fresh["fw"], "fh": fresh["fh"]}

    shaped = _image(
        "pic", url, fx=0.20, fy=0.25, fw=0.30, fh=0.12, rot=30, flipH=True,
        flipV=True, crop={"l": 0.1, "t": 0.05, "r": 0.1, "b": 0.0},
        skew=[0.2, 0.0], opacity=0.5, name="My picture",
        look={"bright": 0.25},
        sockets=[{"id": "s1", "ux": 0.5, "uy": 0.5, "chipId": ""}])
    other = _image("pic2", url, fx=0.60, fy=0.60, fw=0.15, fh=0.15, rot=90,
                   opacity=0.4)
    locked = _image("plock", url, fx=0.05, fy=0.70, rot=45, locked=True)
    turned = _image("prot", url, fx=0.80, fy=0.20, fw=0.10, fh=0.05, rot=45)
    plain = _image("pplain", url, fx=0.70, fy=0.72,
                   fw=fresh["fw"], fh=fresh["fh"])
    s.js("setNodes", json.dumps(base + [shaped, other, locked, turned, plain]))
    s.wait(300)
    s.call("seedHist")

    before = _pick(s.node("pic"))
    out["before"] = before

    # Right-click › Picture › Reset Picture.
    s.call("setSelection", ["pic"])
    s.right_click(s.center("pic"))
    out["rows-pic"] = _picture_rows(s)
    hist0 = s.state()["histAt"]
    _open_section(s, "Picture")
    _run_row(s, "Reset Picture")
    s.wait(200)
    s.close_menus()
    out["steps"] = s.state()["histAt"] - hist0
    out["after"] = _pick(s.node("pic"))
    s.call("setSelection", ["pic"])
    s.right_click(s.center("pic"))
    out["rows-pic-after"] = _picture_rows(s)
    s.close_menus()
    s.call("undo")
    s.wait(150)
    out["undone"] = _pick(s.node("pic"))

    # Locked, and one already as a fresh add would place it: greyed out.
    for key, id_ in (("plain", "pplain"), ("lock", "plock")):
        s.call("setSelection", [id_])
        out["can-" + key] = s.call("canResetPicture", s.node(id_)["id"])
    s.call("setSelection", ["pplain"])
    s.right_click(s.center("pplain"))
    out["rows-plain"] = _picture_rows(s)
    s.close_menus()

    # Reset Shape on a picture that is only turned gives back the turn (S42).
    s.call("setSelection", ["prot"])
    s.right_click(s.center("prot"))
    out["shape-enabled"] = _shape_row(s)
    _open_section(s, "Transform")
    _run_row(s, "Reset Shape")
    s.wait(200)
    s.close_menus()
    out["prot-after"] = _pick(s.node("prot"))

    # Several pictures at once (the locked one is left), one Undo step.
    s.call("setSelection", ["pic", "pic2", "plock"])
    hist0 = s.state()["histAt"]
    s.call("resetPicture")
    s.wait(150)
    out["multi-steps"] = s.state()["histAt"] - hist0
    out["multi"] = {i: _pick(s.node(i)) for i in ("pic", "pic2", "plock")}
    s.call("undo")
    s.wait(150)

    # The menu bar's Arrange › Reset Picture (07 S134) runs the same command.
    s.call("setSelection", ["pic"])
    out["cmd-applies"] = s.call("cmdApplies", "resetPicture")
    hist0 = s.state()["histAt"]
    s.call("cmdRun", "resetPicture")
    s.wait(150)
    out["cmd-steps"] = s.state()["histAt"] - hist0
    out["cmd-after"] = _pick(s.node("pic"))
    s.call("undo")
    s.wait(150)

    # The Properties panel's button.
    s.js("showProps", True)
    s.call("setSelection", ["pic"])
    s.wait(150)
    out["props-pic"] = s.state()["props"]
    button = _find(s.win.contentItem(), "propButton_resetPicture")
    out["props-button"] = button is not None
    if button is not None:
        p = button.mapToScene(
            QtCore.QPointF(button.width() / 2, button.height() / 2))
        hist0 = s.state()["histAt"]
        s.click(QtCore.QPoint(round(p.x()), round(p.y())))
        s.wait(200)
        out["props-steps"] = s.state()["histAt"] - hist0
        out["props-after"] = _pick(s.node("pic"))
    s.js("showProps", False)

    out["warnings"] = sorted({w for w in s.warnings if "rig_" in w
                              or "RigPropsPanel" in w or "VkbRigEditor" in w})
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen for the planes' menus and
properties (07 S42, S43, S121, S124): Move to Background / Move to
Foreground in the right-click menu's Arrange section, Reset Shape on a
picture, the Properties panel's Look for pictures, and big pictures drawn
from a screen-sized copy. Prints the results as JSON;
test_planes_menus_props.py runs it in its own process.

    python test/unit/planes_menus_props_smoke.py <picture folder>
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtGui, QtQuick  # noqa: E402


def _picture(folder: Path, name: str, w: int, h_: int) -> str:
    path = folder / name
    img = QtGui.QImage(w, h_, QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtGui.QColor("#3080C0"))
    assert img.save(str(path))
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def _draw(id_: str, shape: str, fx: float, fy: float, **extra: object) -> dict:
    n = {"id": id_, "kind": "draw", "shape": shape, "fx": fx, "fy": fy,
         "fw": 0.1, "fh": 0.1, "rot": 0, "opacity": 1, "locked": False,
         "pinned": False, "sockets": [], "fill": "filled"}
    n.update(extra)
    return n


def _menu_items(s: h.Session) -> dict:
    """The open menu's items by their name (objectName), from the model."""
    model = s.call("menuModel")
    out: dict[str, dict] = {}
    for sect in model.get("sections") or []:
        for item in sect.get("items") or []:
            if item.get("name"):
                out[item["name"]] = {
                    "section": sect.get("key"), "text": item.get("text"),
                    "enabled": item.get("enabled"), "hint": item.get("hint"),
                    "tip": item.get("tip"),
                }
            if item.get("text") == "Reset Shape":
                out["Reset Shape"] = {
                    "section": sect.get("key"), "enabled": item.get("enabled")}
    return out


def _find(item: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem | None:
    for child in item.childItems():
        if child.objectName() == name and child.isVisible():
            return child
        found = _find(child, name)
        if found is not None:
            return found
    return None


def _click_slider(s: h.Session, name: str, frac: float) -> None:
    """Clicks a Properties slider at frac of its track (its padding off)."""
    slider = _find(s.win.contentItem(), name)
    assert slider is not None, f"no slider {name}"
    left = slider.property("leftPadding")
    track = slider.width() - left - slider.property("rightPadding")
    handle = slider.property("handle")
    hw = handle.width() if handle is not None else 0
    x = left + hw / 2 + (track - hw) * frac
    p = slider.mapToScene(QtCore.QPointF(x, slider.height() / 2))
    s.click(QtCore.QPoint(round(p.x()), round(p.y())))
    s.wait(150)


def _markers(item: QtQuick.QQuickItem) -> list:
    """Every "pictureMissing" item under item (Loader-made items have no
    QObject parent, so findChildren misses them)."""
    out = []
    for child in item.childItems():
        if child.objectName() == "pictureMissing":
            out.append(child)
        out += _markers(child)
    return out


def _pictures(s: h.Session) -> dict:
    """Each picture item's state (RigDrawItem.pictureInfo), by node id."""
    out = {}
    for marker in _markers(s.win.contentItem()):
        item = marker.parentItem()
        node = item.property("node")
        node = node.toVariant() if hasattr(node, "toVariant") else node
        if not isinstance(node, dict) or node.get("shape") != "image":
            continue
        info = QtCore.QMetaObject.invokeMethod(
            item, "pictureInfo", QtCore.Q_RETURN_ARG("QVariant"))
        info = info.toVariant() if hasattr(info, "toVariant") else info
        info["missingShown"] = bool(marker.property("visible"))
        out[node["id"]] = {"info": info, "item": item}
    return out


def _wait_pictures(
    s: h.Session, ids: list[str], cond: Callable[[dict], bool]
) -> dict:
    deadline = QtCore.QDeadlineTimer(8000)
    while True:
        pics = _pictures(s)
        ready = all(i in pics and cond(pics[i]["info"]) for i in ids)
        if ready or deadline.hasExpired():
            return pics
        s.wait(50)


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "planes_menus_props")
    out: dict[str, object] = {}
    small = _picture(folder, "small.png", 200, 100)
    big = _picture(folder, "big.png", 6000, 3000)
    look = _picture(folder, "look.png", 200, 100)
    h._load(s, "evo_r")
    nodes = s.state()["nodes"]
    chip = next(n for n in nodes if n["id"] == "b3")
    bg = _draw("pbg", "image", 0.02, 0.02, src="pictures/big.png", srcUrl=big,
               plane="background")
    bg.update(fw=0.3, fh=0.15)
    pic = _draw("pic", "image", 0.55, 0.70, src="pictures/small.png", srcUrl=small,
                rot=30, flipH=True)
    looked = _draw("plk", "image", 0.70, 0.70, src="pictures/small.png", srcUrl=small,
                   lookUrl=look, look={"bright": 0.5})
    gone = _draw("pgone", "image", 0.85, 0.70, src="pictures/gone.png", srcUrl="")
    rect = _draw("rect1", "rect", 0.40, 0.70)
    nodes = [bg] + nodes + [pic, looked, gone, rect]
    s.js("setNodes", json.dumps(nodes))
    s.wait(300)
    s.call("seedHist")
    out["chip"] = chip["id"]

    # Right-click › Arrange on a chip, a shape and a picture.
    for key, id_ in (("chip", chip["id"]), ("rect", "rect1"), ("pic", "pic")):
        s.call("setSelection", [id_])
        s.right_click(s.center(id_))
        out["menu-" + key] = _menu_items(s)
        s.close_menus()

    # Move to Background through the menu's own row.
    s.call("setSelection", ["rect1"])
    s.right_click(s.center("rect1"))
    s.open_menu_section("Arrange")
    hist0 = s.state()["histAt"]
    s.click_menu_row("Move to Background")
    s.wait(200)
    st = s.state()
    out["rect-after-move"] = s.node("rect1").get("plane", "")
    out["move-steps"] = st["histAt"] - hist0
    out["order-after-move"] = [n["id"] for n in st["nodes"]][:3]
    s.close_menus()

    # In Background mode the same item offers Move to Foreground.
    s.set_prop("editPlane", "background")
    s.call("setSelection", ["rect1"])
    s.right_click(s.center("rect1"))
    out["menu-rect-bg"] = _menu_items(s)
    s.open_menu_section("Arrange")
    s.click_menu_row("Move to Foreground")
    s.wait(200)
    out["rect-after-back"] = s.node("rect1").get("plane", "")
    s.close_menus()
    s.set_prop("editPlane", "foreground")

    # Reset Shape on a picture turned and flipped.
    s.call("setSelection", ["pic"])
    s.right_click(s.center("pic"))
    out["menu-pic-reset"] = _menu_items(s).get("Reset Shape")
    s.open_menu_section("Transform")
    s.click_menu_row("Reset Shape")
    s.wait(200)
    p = s.node("pic")
    out["pic-after-reset"] = {"rot": p.get("rot", 0), "flipH": bool(p.get("flipH"))}
    s.close_menus()

    # Properties: a picture's Look.
    s.js("showProps", True)
    s.call("setSelection", ["pic"])
    s.wait(150)
    out["props-pic"] = s.state()["props"]
    # A click on a slider moves it there: Brightness at 62.5 % of its
    # track (-100..100) is 25; Greyscale (0..100) at 40 % is 40.
    _click_slider(s, "propSlider_bright", 0.625)
    _click_slider(s, "propSlider_grey", 0.40)
    out["pic-look"] = s.node("pic").get("look")
    out["props-pic-after"] = s.state()["props"]
    s.call("setSelection", ["rect1"])
    s.wait(150)
    out["props-rect"] = s.state()["props"]
    s.js("showProps", False)

    # Big pictures on screen and at full size.
    pics = _wait_pictures(s, ["pbg", "pic", "plk"],
                          lambda i: i["status"] == 1 and i["natW"] > 0)
    big_item = pics["pbg"]["item"]
    pics = _wait_pictures(s, ["pbg"], lambda i: i["loadW"] < 6000)
    out["pictures"] = {k: v["info"] for k, v in pics.items()}
    big_item.setProperty("fullResolution", True)
    pics = _wait_pictures(s, ["pbg"], lambda i: i["loadW"] == 6000 and i["status"] == 1)
    out["big-full"] = pics["pbg"]["info"]
    big_item.setProperty("fullResolution", False)
    pics = _wait_pictures(s, ["pbg"], lambda i: i["loadW"] < 6000 and i["status"] == 1)
    out["big-capped-again"] = pics["pbg"]["info"]
    out["screen-side"] = big_item.property("screenSide")
    out["warnings"] = sorted({w for w in s.warnings if "RigDrawItem" in w
                              or "RigPropsPanel" in w or "rig_menu" in w
                              or "rig_props" in w})
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

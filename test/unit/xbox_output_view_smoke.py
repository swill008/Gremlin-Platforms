# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Runs the real main window off-screen and prints what the Xbox Output View
shows as one JSON line, for test_xbox_output_view.py. Pads 1 and 2 are on
(Xbox Setup); one device drives pads 1, 2 and 3 (the bindings and chips are
faked; the hardware is fake_hardware), so pad 3 (off) has no section. The
Xbox driver is reported missing, then found. Arg: optional screenshot path."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections.abc import Iterator
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

from gremlin.modules import output  # noqa: E402

output.xbox_driver_installed = lambda: False
output.xbox_driver_version = lambda: ""
output.xbox_available = lambda: False
output.xbox_error = lambda: ""

import gremlin.ui.update_model as um  # noqa: E402
from gremlin.ui import xbox_output_list, xbox_viewer  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

DEVICE = "Test Stick"
GUID = "{11111111-2222-3333-4444-555555555555}"
BOUND: dict = {
    1: {GUID: {"a", "left_stick_x"}},
    2: {GUID: {"b"}},
    3: {GUID: {"x"}},
}
output.xbox_pads_on = lambda: [1, 2]
xbox_output_list.pad_bindings = lambda: {k: dict(v) for k, v in BOUND.items()}
xbox_output_list.device_label = lambda guid: DEVICE


def _chips(pad: int) -> list[dict]:
    if pad not in BOUND:
        return []
    button = {"identifier": 1, "label": "1", "kind": "button", "xboxTarget": "a",
              "xboxLabel": "Xbox 360 1 · A", "xboxChip": "A"}
    axis = {"identifier": 1, "label": "X", "kind": "axis",
            "xboxTarget": "left_stick_x", "xboxLabel": "Xbox 360 1 · LSX",
            "xboxChip": "LX"}
    return [{"guid": GUID, "name": DEVICE, "axes": [axis] if pad == 1 else [],
             "buttons": [button]}]


xbox_viewer.pad_chips = _chips

from PySide6 import QtCore, QtGui, QtQml, QtQuick  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin.signal import signal  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window


ERRORS: list[str] = []


def run(code: str, scope: QtCore.QObject | None = None) -> object:
    target = scope if scope is not None else win
    expr = QtQml.QQmlExpression(QtQml.qmlContext(target), target, code)
    value, _ = expr.evaluate()
    if expr.hasError():
        # Recorded, not raised: on old code each check then fails by itself.
        ERRORS.append(code + ": " + expr.error().toString())
        return None
    return value


def runj(code: str) -> object:
    text = run("JSON.stringify(" + code + ")")
    return json.loads(str(text)) if text is not None else None


def pump(seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtGui.QGuiApplication.processEvents()
        time.sleep(0.01)


def walk(item: QtQuick.QQuickItem) -> Iterator[QtQuick.QQuickItem]:
    yield item
    for child in item.childItems():
        yield from walk(child)


def shown(item: QtQuick.QQuickItem | None) -> bool:
    if item is None:
        return False
    while item is not None:
        if not item.isVisible():
            return False
        item = item.parentItem()
    return True


def top(item: QtQuick.QQuickItem) -> int:
    return round(item.mapToScene(item.boundingRect().topLeft()).y())


def other_windows() -> list[str]:
    return [w.title() for w in app.topLevelWindows()
            if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow)]


def page() -> QtQuick.QQuickItem | None:
    item = run("_xboxLoader.item")
    return item if isinstance(item, QtQuick.QQuickItem) else None


def named(items: list, name: str) -> QtQuick.QQuickItem | None:
    return next((i for i in items if i.objectName() == name), None)


def pad_state(item: QtQuick.QQuickItem, items: list, content: list, pad: int) -> dict:
    section = named(items, f"xboxPadSection{pad}")
    assert section is not None
    sec_items = list(walk(section))
    heading = named(sec_items, f"xboxPadHeading{pad}")
    face = named(sec_items, f"xboxPadFace{pad}")
    tree = named(sec_items, f"xboxOutputTree{pad}")
    chips = [i for i in sec_items if i.objectName() == "xboxChip" and shown(i)]
    lines = [
        i for i in sec_items
        if i.objectName() in (f"xboxAxisLine{pad}", f"xboxButtonLine{pad}")
        and shown(i)
    ]
    texts = [
        i.property("text") for i in sec_items
        if shown(i) and isinstance(i.property("text"), str)
    ]
    return {
        "top": top(section),
        "open": run(f"isPadOpen({pad})", item),
        "headingShown": shown(heading),
        "texts": texts,
        "faceShown": shown(face),
        "facePad": face.property("padId") if face else None,
        "faceAbove": bool(face and tree and top(face) < top(tree)),
        "chips": [[c.property("hwLabel"), c.property("xbLabel")] for c in chips],
        "lines": sorted({str(i.property("deviceName")) for i in lines}),
        "treeShown": shown(tree),
        "treeInScroll": tree is not None and tree in content,
        "treeReadOnly": bool(tree and tree.property("readOnly")),
        "treeGroups": bool(tree and tree.property("showGroups")),
        # The list doesn't scroll by itself: it is as tall as its rows and
        # the page's scroll moves it with the pads (S139).
        "treeOwnScroll": bool(tree and tree.property("ownScroll")),
        "treeFull": bool(tree)
        and tree.height() + 1 >= float(tree.property("listHeight") or 0),
        "rows": run(f"padList({pad}).parentCount", item),
    }


def page_state() -> dict:
    item = page()
    if item is None:
        return {"loaded": False}
    items = list(walk(item))
    scroll = named(items, "xboxOutputScroll")
    content = list(walk(scroll)) if scroll is not None else []
    missing = named(items, "xboxDriverMissing")
    link = named(items, "xboxOpenSetupLink")
    find = named(items, "xboxOutputFindBar")
    empty = named(items, "xboxOutputEmpty")
    return {
        "loaded": True,
        "sections": int(item.property("padSectionCount") or 0),
        "missingShown": shown(missing),
        "missingText": missing.property("text") if missing else None,
        "linkShown": shown(link),
        "linkText": link.property("text") if link else None,
        "missingTop": top(missing) if missing else -1,
        "findShown": shown(find),
        "findTop": top(find) if find else -1,
        "findInScroll": find is not None and find in content,
        "emptyShown": shown(empty),
        "emptyText": empty.property("text") if empty else None,
        "pads": {
            str(pad): pad_state(item, items, content, pad)
            for pad in (1, 2, 3)
            if named(items, f"xboxPadSection{pad}") is not None
        },
    }


def bar_button(name: str) -> bool:
    """Whether the window's button with this objectName is shown."""
    item = next((i for i in walk(win.contentItem()) if i.objectName() == name), None)
    return item is not None and shown(item)


out: dict = {}
pump(0.5)
# The toolbar and the commands: no Xbox Viewer left.
out["button"] = run("typeof _xboxViewerButton")
out["captions"] = runj("_toolbarRow.children.map(function(b) { return b.caption })"
                      ".filter(function(c) { return !!c })")
out["commands"] = runj("MainCommands.commandList().map(function(c) { return c.id })")
out["helpAllowed"] = runj("HelpLinks.allowedOpen()")
out["paletteHidden"] = run("Commands.get('view.xboxOutput').palette === false")

# Help's Open link: the Xbox Output View on the main window.
run("Commands.trigger('view.xboxOutput')")
pump(1.0)
out["openRoom"] = runj("[uiState.currentRoom, uiState.currentTab]")
out["open"] = page_state()
out["openWindows"] = other_windows()
# The list's own Appearance on the page bar; the Output View's stays hidden.
out["listAppearanceButton"] = bar_button("xboxOutputAppearanceButton")
out["outputAppearanceButton"] = bar_button("outputAppearanceButton")
out["pageKey"] = run("_xboxLoader.item.appearance.pageKey")
if len(sys.argv) > 1:
    win.grabWindow().save(sys.argv[1])

# The Find bar once, for every pad's list.
first = page()
box = named(list(walk(first)), "xboxOutputFind") if first is not None else None
if box is not None and first is not None:
    box.setProperty("text", "Left Stick")
    pump(0.3)
    out["find"] = {str(p): run(f"padList({p}).parentCount", first) for p in (1, 2)}
    box.setProperty("text", "")
    pump(0.3)
    out["findCleared"] = {
        str(p): run(f"padList({p}).parentCount", first) for p in (1, 2)
    }

# Fold pad 2 only: its face, chips and list hide; pad 1 stays; remembered.
run("_xboxLoader.item.setPadOpen(2, false)")
pump(0.3)
out["folded"] = page_state()
run("closeWorkRoomNow()")
pump(0.5)
out["closedLoaded"] = page() is not None
run("openXboxOutputView()")
pump(1.0)
out["reopenedFolded"] = page_state()
run("_xboxLoader.item.setPadOpen(2, true)")
pump(0.3)
out["reopened"] = page_state()

# Pad 2 off in Xbox Setup: its section goes.
output.xbox_pads_on = lambda: [1]
signal.xboxPadsChanged.emit()
pump(0.3)
out["padsOne"] = page_state()

# No pad bound: no sections, one line, no Find bar, no Appearance button.
BOUND.clear()
signal.bindingsChanged.emit()
pump(0.5)
out["empty"] = page_state()
out["emptyAppearanceButton"] = bar_button("xboxOutputAppearanceButton")

# The red line's link asks Main for Xbox Setup.
asked = [0]
page_item = page()
if page_item is not None:
    QtCore.QObject.connect(
        page_item, "2xboxSetupRequested()",
        lambda: asked.__setitem__(0, asked[0] + 1),
    )
    link = named(list(walk(page_item)), "xboxOpenSetupLink")
    if link is not None:
        run("clicked()", link)
        pump(0.3)
out["setupAsked"] = asked[0]

# Driver found: no red line.
for w in app.topLevelWindows():
    if w is not win and w.isVisible():
        w.close()
output.xbox_available = lambda: True
run("closeWorkRoomNow()")
pump(0.5)
run("openXboxOutputView()")
pump(1.0)
out["found"] = page_state()

# The card's old viewer entry (pairingForCard) opens the same page, no window.
run("closeWorkRoomNow()")
pump(0.5)
run("pairingForCard(_moduleModel.cardMap('xbox'))")
pump(1.0)
out["pairingRoom"] = runj("[uiState.currentRoom, uiState.currentTab]")
out["pairingWindows"] = other_windows()

out["errors"] = ERRORS
print("RESULT " + json.dumps(out), flush=True)
smoke_exit(0)

# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Runs the real main window off-screen and prints what the Xbox Output View
shows as one JSON line, for test_xbox_output_view.py. One device drives the
Xbox pad (the live pads' list is faked; the hardware is fake_hardware) and
the Xbox driver is reported missing, so the result doesn't depend on this
PC. Arg: optional screenshot path."""

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
from gremlin.ui import xbox_viewer  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

DEVICE = "Test Stick"


def _one_device(self: xbox_viewer.XboxViewerDeviceModel) -> None:
    self.beginResetModel()
    self._rows = [{"guid": "{11111111-2222-3333-4444-555555555555}",
                   "name": DEVICE, "pairLabel": "Xbox 360 1"}]
    self.endResetModel()
    self.countChanged.emit()


xbox_viewer.XboxViewerDeviceModel.reload = _one_device

from PySide6 import QtGui, QtQml, QtQuick  # noqa: E402

import joystick_gremlin  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window


ERRORS: list[str] = []


def run(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
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


def page_state() -> dict:
    item = page()
    if item is None:
        return {"loaded": False}
    items = list(walk(item))
    rows = [i for i in items if i.objectName() == "xboxDriverRow" and shown(i)]
    heading = next((i for i in items if i.objectName() == "xboxPadsHeading"), None)
    scroll = next((i for i in items if i.objectName() == "xboxOutputScroll"), None)
    card = next((i for i in items if i.property("text") == DEVICE and shown(i)), None)
    control = next(
        (i for i in items if i.property("text") == "Left Stick X" and shown(i)), None
    )
    content = list(walk(scroll)) if scroll is not None else []
    return {
        "loaded": True,
        "driverRows": len(rows),
        "driverTop": top(rows[0]) if rows else -1,
        "headingTop": top(heading) if heading else -1,
        "cardShown": card is not None,
        "cardTop": top(card) if card else -1,
        "controlTop": top(control) if control else -1,
        "cardInScroll": card is not None and card in content,
        "controlInScroll": control is not None and control in content,
        "padsOpen": bool(item.property("padsOpen")),
    }


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
if len(sys.argv) > 1:
    win.grabWindow().save(sys.argv[1])

# Fold the live pads: hidden, and still folded the next time the page opens.
run("_xboxLoader.item.setPadsOpen(false)")
pump(0.3)
out["folded"] = page_state()
run("closeWorkRoomNow()")
pump(0.5)
out["closedLoaded"] = page() is not None
run("openXboxOutputView()")
pump(1.0)
out["reopenedFolded"] = page_state()
run("_xboxLoader.item.setPadsOpen(true)")
pump(0.3)
out["reopened"] = page_state()

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

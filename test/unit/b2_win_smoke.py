# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the Export / Import Device window (test_b2_win.py).

The window's title, its .gmap file choosers, openFor() on each tab, and
the As a new device / Onto an existing device choice when a file is opened
(D-FIXLIST-B2). The file's description is faked (describe_zip) so the
window is tested on its own. Prints RESULT {json}."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Iterator

from smoke_exit import smoke_exit

sys.path.insert(0, ".")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

spec = importlib.util.spec_from_file_location("fake_hardware", "test/fake_hardware.py")
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

import joystick_gremlin  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

from gremlin import device_initialization, util  # noqa: E402
from gremlin.modules import module_file, store  # noqa: E402
from gremlin.ui import device_pack  # noqa: E402

out: dict = {}


def ev(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


def walk(item: QtQuick.QQuickItem) -> Iterator[QtQuick.QQuickItem]:
    yield item
    for child in item.childItems():
        yield from walk(child)


def child(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
    for item in walk(window.contentItem()):
        if item.objectName() == name:
            return item
    return None


stick = next(
    d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
)
guid = str(stick.device_guid)
module_file.write_json(
    store.module_file_in(store.ensure_device_dir(stick.name, guid)),
    {"kind": "control.hardware", "device": stick.name, "claim": {"buttons": [1]},
     "nodes": []},
)

ev('Helpers.createComponent("DialogDevicePack.qml")')
wait_until(
    lambda: any(
        isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
        and w.title() in ("Export / Import Device", "Device Pack")
        for w in app.topLevelWindows()
    ),
    "the Device Pack window", fail=False,
)
titles = [
    w.title()
    for w in app.topLevelWindows()
    if isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
]
out["titles"] = titles
pack_win = next(
    (
        w
        for w in app.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow)
        and w.isVisible()
        and w.title() in ("Export / Import Device", "Device Pack")
    ),
    None,
)
if pack_win is None:
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


def pv(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(pack_win), pack_win, code)
    value = expr.evaluate()[0]
    if expr.hasError():
        return {"error": expr.error().toString()}
    return value


def pj(code: str) -> object:
    """A value from the window as plain JSON (lists, missing names)."""
    got = pv(f"JSON.stringify(({code}))")
    return got if isinstance(got, dict) else json.loads(str(got or "null"))


out["title"] = pack_win.title()
out["save-filters"] = pj("_save.nameFilters")
out["save-suffix"] = pj("_save.defaultSuffix")
out["open-filters"] = pj("_pick.nameFilters")
out["hint"] = pj('exportHint("pJoy Pro")')

# openFor("export", name, guid): the Export tab with that device chosen.
pv("_pages.currentIndex = 1")
pv(f'openFor("export", "pJoy Pro", "{guid}")')
QtTest.QTest.qWait(200)
out["export-tab"] = pj("_pages.currentIndex")
out["export-device"] = pj("exportDeviceName()")
out["export-guid"] = pj("exportDeviceGuid()")

# openFor("import", name, guid): the Import tab, that device as the target.
pv(f'openFor("import", "pJoy Pro", "{guid}")')
QtTest.QTest.qWait(200)
out["import-tab"] = pj("_pages.currentIndex")
out["import-target"] = pj("importTarget")
out["import-name"] = pj("_saveAs.text")
out["import-guid"] = pj("importGuid")
existing = child(pack_win, "packTargetExisting")
new = child(pack_win, "packTargetNew")
out["choice-shown"] = bool(
    existing and new and existing.isVisible() and new.isVisible()
)
out["existing-checked"] = bool(existing and existing.property("checked"))


def fake_info(device: str) -> dict:
    return {
        "ok": True,
        "exportedName": device,
        "suggestedName": device,
        "notes": {},
        "drivers": [],
        "sections": [
            {"id": "in", "title": "Input module",
             "items": [{"id": "in.checks", "title": "Checked controls"}]},
        ],
    }


described: dict = {}
device_pack.describe_zip = lambda path: described["info"]
gmap = os.path.join(util.userprofile_path(), "some.gmap")
with open(gmap, "wb") as fh:
    fh.write(b"x")
url = QtCore.QUrl.fromLocalFile(gmap).toString()

# A file whose device has a folder here, opened after openFor("import"):
# Onto an existing device, the suggested device.
described["info"] = fake_info("Unknown Stick")
pv(f'openFile("{url}")')
QtTest.QTest.qWait(100)
out["suggested-target"] = pj("importTarget")
out["suggested-name"] = pj("_saveAs.text")

# Opened from the Tools menu (no suggestion): a device with no folder here
# goes As a new device; one with a folder goes Onto an existing device.
pv("suggestedTarget = null")
pv(f'openFile("{url}")')
QtTest.QTest.qWait(100)
out["new-target"] = pj("importTarget")
out["new-name"] = pj("_saveAs.text")
out["new-checked"] = bool(new and new.property("checked"))
out["new-combo-hidden"] = not child(pack_win, "packImportDevice").isVisible()
out["new-selection"] = pj("JSON.parse(selectionJson())")
described["info"] = fake_info("pJoy Pro")
pv(f'openFile("{url}")')
QtTest.QTest.qWait(100)
out["folder-target"] = pj("importTarget")
out["folder-row"] = pj("_importDevice.currentIndex")
out["folder-selection"] = pj("JSON.parse(selectionJson())")
# The pieces' ticks show for both targets.
out["ticks-existing"] = child(pack_win, "packList").isVisible()
# Clicking As a new device switches the target.
if new is not None:
    pos = new.mapToScene(QtCore.QPointF(new.width() / 2, new.height() / 2)).toPoint()
    QtTest.QTest.mouseClick(
        pack_win, QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier, pos,
    )
    wait_until(
        lambda: pj("importTarget") == "new", "As a new device chosen", fail=False
    )
out["clicked-target"] = pj("importTarget")
out["ticks-new"] = child(pack_win, "packList").isVisible()
print("RESULT " + json.dumps(out), flush=True)
smoke_exit(0)

# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the Device Pack window (test_device_pack_window.py).

A pack is made from the open profile, then imported back over a changed
setup: the warning, Replace, Undo Import, the export choices, and the list
kept in its own area. Prints RESULT {json}."""

from __future__ import annotations

import json
import os
import sys
import uuid
from collections.abc import Iterator

sys.path.insert(0, ".")
import importlib.util

spec = importlib.util.spec_from_file_location("fake_hardware", "test/fake_hardware.py")
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

from gremlin import (  # noqa: E402
    device_initialization,
    plugin_manager,
    shared_state,
    util,
)
from gremlin.logical_device import LogicalDevice  # noqa: E402
from gremlin.modules import module_file  # noqa: E402
from gremlin.profile import DeviceInfo, Profile  # noqa: E402
from gremlin.types import InputType  # noqa: E402
from gremlin.ui import device_pack, hardware_profile  # noqa: E402

shot = sys.argv[1] if len(sys.argv) > 1 else ""
out: dict = {}


def ev(code: str, target: QtCore.QObject | None = None) -> object:
    host = target or win
    expr = QtQml.QQmlExpression(QtQml.qmlContext(host), host, code)
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


def popup_item(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
    """Items in popups aren't under the content item: find them by name."""
    return window.findChild(QtQuick.QQuickItem, name)


def add_map(
    profile: Profile, uid: uuid.UUID, button: int, mode: str, vjoy: int, target: int
) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = vjoy
    action.vjoy_input_id = target
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def add_logical(profile: Profile, uid: uuid.UUID, button: int, number: int) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to Logical Device", InputType.JoystickButton
    )
    action.logical_input_id = number
    action.logical_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


stick = next(
    d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
)
name, uid = stick.name, stick.device_guid.uuid
profile = shared_state.current_profile
profile.device_database.devices[uid] = DeviceInfo(uid, name)
profile.modes.add_mode("Combat")
profile.modes.set_parent("Combat", "Default")
add_map(profile, uid, 1, "Default", 1, 1)
add_map(profile, uid, 2, "Combat", 1, 2)
add_logical(profile, uid, 5, 9)
modules = util.modules_dir()
modules.mkdir(parents=True, exist_ok=True)
module_file.write_json(
    modules / f"{hardware_profile._slug(name)}.json",
    {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "claim": {
            "buttons": [1, 2, 5],
            "axes": [],
            "hats": [],
            "keys": [],
            "friendly": {"button:1": "Trigger"},
        },
        "catalog": {"rowHeight": 40},
        "ui": {"viewPct": 80, "printArea": {"fx": 0, "fy": 0, "fw": 1, "fh": 1}},
        "nodes": [],
    },
)

ev('Helpers.createComponent("DialogDevicePack.qml")')
QtTest.QTest.qWait(600)
pack_win = next(
    w
    for w in app.topLevelWindows()
    if isinstance(w, QtQuick.QQuickWindow)
    and w.title().startswith("Device Pack")
    and w.isVisible()
)
root = (
    pack_win.contentItem().childItems()[0]
    if pack_win.contentItem().childItems()
    else None
)
pack_win.resize(860, 780)
QtTest.QTest.qWait(200)


def pv(code: str) -> object:
    """Evaluate in the Device Pack window."""
    expr = QtQml.QQmlExpression(QtQml.qmlContext(pack_win), pack_win, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


# --- Export: the device's modes, ticked; options carry them and the notes ----
pv(f'_exportDevice.currentIndex = _exportDevice.find("{name}")')
pv("refreshExport()")
QtTest.QTest.qWait(200)
out["export-modes"] = json.loads(pv("JSON.stringify(exportModes)"))
pv(f'_exportDevice.currentIndex = _exportDevice.find("{name}")')
pv('_author.text = "Sam"; _note.text = "My setup"; exportTicks["Combat"] = false')
out["export-options"] = json.loads(pv("exportOptions()"))
out["show-folder-hidden"] = not child(pack_win, "packShowFolder").isVisible()
if shot:
    pack_win.grabWindow().save(shot + "-export.png")

# The pack (both modes), then this machine changes: Default gets another wire.
zip_path = os.path.join(util.userprofile_path(), "pack.zip")
built = device_pack.assemble(
    name, lambda stored: None, None, {"author": "Sam", "note": "My setup"}
)
with open(zip_path, "wb") as fh:
    fh.write(built[0])
add_map(profile, uid, 3, "Default", 1, 3)

# --- Import -------------------------------------------------------------------
url = QtCore.QUrl.fromLocalFile(zip_path).toString()
pv("_pages.currentIndex = 1")
pv(f'zipUrl = "{url}"')
pv("loadPack(JSON.parse(_hw.peekPackZip(zipUrl)))")
pv(f'_saveAs.text = "{name}"')
QtTest.QTest.qWait(200)
out["notes"] = child(pack_win, "packNotes").property("text")
out["sections"] = json.loads(
    pv("JSON.stringify(sections.map(function(s){return s.title}))")
)
# Every section and row open: the list must stay below Open All.
pv("setAll(true)")
QtTest.QTest.qWait(300)
lst = child(pack_win, "packList")
open_all = next(
    i for i in walk(pack_win.contentItem()) if i.property("text") == "Open All"
)
list_top = lst.mapToScene(QtCore.QPointF(0, 0)).y()
buttons_bottom = open_all.mapToScene(QtCore.QPointF(0, open_all.height())).y()
out["list-below-buttons"] = list_top >= buttons_bottom - 0.5
import_button = child(pack_win, "packImport")
out["import-below-list"] = (
    import_button.mapToScene(QtCore.QPointF(0, 0)).y()
    >= lst.mapToScene(QtCore.QPointF(0, lst.height())).y() - 0.5
)
if shot:
    pack_win.grabWindow().save(shot + "-import.png")
pv("setAll(false)")
# Tick: Default wires, Configuration Appearance, the checked controls.
pv(
    'for (var k in checks) checks[k] = false; checks["wire:Default"] = true; '
    'checks["in.catalog"] = true; checks["in.checks"] = true; tickRev = tickRev + 1'
)
pv("askImport()")
QtTest.QTest.qWait(300)
warn_text = popup_item(pack_win, "packWarningText")
out["warning"] = warn_text.property("text") if warn_text else ""
create = popup_item(pack_win, "packCreateLogical")
out["create-logical-shown"] = bool(create and create.isVisible())
if shot:
    pack_win.grabWindow().save(shot + "-warning.png")
replace = popup_item(pack_win, "packReplace")
QtTest.QTest.mouseClick(
    pack_win,
    QtCore.Qt.MouseButton.LeftButton,
    QtCore.Qt.KeyboardModifier.NoModifier,
    replace.mapToScene(
        QtCore.QPointF(replace.width() / 2, replace.height() / 2)
    ).toPoint(),
)
QtTest.QTest.qWait(400)
out["status-after"] = pv("status")
out["undo-shown"] = child(pack_win, "packUndo").isVisible()
buttons = sorted(
    item.input_id
    for item in shared_state.current_profile.inputs.get(uid, [])
    if item.mode == "Default" and item.action_sequences
)
out["default-after"] = buttons

out["logical-created"] = LogicalDevice().exists(
    LogicalDevice.Input.Identifier(InputType.JoystickButton, 9)
)
pv("undoImport()")
QtTest.QTest.qWait(300)
buttons = sorted(
    item.input_id
    for item in shared_state.current_profile.inputs.get(uid, [])
    if item.mode == "Default" and item.action_sequences
)
out["default-undone"] = buttons
out["status-undone"] = pv("status")
out["undo-hidden"] = not child(pack_win, "packUndo").isVisible()
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive

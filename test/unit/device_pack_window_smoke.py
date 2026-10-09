# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the Device Pack window (test_device_pack_window.py).

A pack is made from the open profile, then imported back over a changed
setup: the warning, Replace, Undo Import, the export choices, and the list
kept in its own area. With GREMLIN_PACK_PART=twins: two identical sticks,
one row each, Export of the second sends its id, and Import onto the
"(2)" row sends that id and changes only its module file (08 S106a). Prints
RESULT {json}."""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import uuid
from collections.abc import Iterator

sys.path.insert(0, ".")
import importlib.util

spec = importlib.util.spec_from_file_location("fake_hardware", "test/fake_hardware.py")
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()
TWINS = os.environ.get("GREMLIN_PACK_PART") == "twins"
if TWINS:
    # A second, identical stick: same name, its own id.
    twin = fake_hardware.raw_device(is_virtual=False)
    twin.device_guid.Data1 += 5
    twin.joystick_id = 2
    fake.devices.append(twin)

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
from gremlin.modules import module_file, store  # noqa: E402
from gremlin.profile import DeviceInfo, Profile  # noqa: E402
from gremlin.types import InputType  # noqa: E402
from gremlin.ui import device_pack  # noqa: E402

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
    store.own_path(name),
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


def _key(guid: object) -> str:
    return str(guid or "").strip("{}").lower()


def import_on_second(url: str, sticks: list, second: int) -> None:
    """Import the pack with "Put this pack on" set to the "(2)" row (picked
    with the keyboard): the selection carries that row's id, and only the
    second stick's module file gets the pack (08 S106a)."""
    folder = util.modules_dir()
    files = [folder / "pjoy_pro.json", folder / "pjoy_pro_2.json"]
    # Different checked controls on each: the pack's are added to the target.
    for path, button in zip(files, (8, 9)):
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["claim"]["buttons"] = [button]
        module_file.write_json(path, doc)
    first_before = files[0].read_text(encoding="utf-8")
    pv("_pages.currentIndex = 1")
    pv(f'zipUrl = "{url}"')
    pv("loadPack(JSON.parse(_hw.peekPackZip(zipUrl)))")
    # As Choose Zip... does: the suggested name picks its first row.
    pv('_saveAs.text = "pJoy Pro"; importGuid = ""; '
       '_importDevice.currentIndex = importRowOf("pJoy Pro")')
    QtTest.QTest.qWait(200)
    combo = child(pack_win, "packImportDevice")
    combo.forceActiveFocus()
    for _ in range(int(pv("_deviceModel.count"))):
        at = int(pv("_importDevice.currentIndex"))
        if at == second:
            break
        key = QtCore.Qt.Key.Key_Down if at < second else QtCore.Qt.Key.Key_Up
        QtTest.QTest.keyClick(pack_win, key)
        QtTest.QTest.qWait(50)
    out["twin-import-shown"] = str(pv("_importDevice.displayText"))
    pv('for (var k in checks) checks[k] = false; checks["in.checks"] = true; '
       "tickRev = tickRev + 1")
    out["twin-selection"] = json.loads(pv("selectionJson()"))
    pv("askImport()")
    QtTest.QTest.qWait(300)
    replace = popup_item(pack_win, "packReplace")
    if replace is not None and replace.isVisible():
        QtTest.QTest.mouseClick(
            pack_win,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            replace.mapToScene(
                QtCore.QPointF(replace.width() / 2, replace.height() / 2)
            ).toPoint(),
        )
        QtTest.QTest.qWait(400)
    out["twin-import-status"] = str(pv("status"))
    out["twin-first-unchanged"] = files[0].read_text(encoding="utf-8") == first_before
    second_doc = json.loads(files[1].read_text(encoding="utf-8"))
    out["twin-second-buttons"] = sorted(second_doc.get("claim", {}).get("buttons", []))


def run_twins() -> None:
    """Two pJoy Pro sticks, each with its own module file: two rows named as
    on Home, and Export of the second sends (and packs) its id."""
    import zipfile

    # The second one is named "pJoy Pro (2)" by the program (twin naming).
    sticks = [
        d
        for d in device_initialization.physical_devices()
        if d.name.startswith("pJoy Pro")
    ]
    out["twin-names"] = [d.name for d in sticks]
    # Both by the name Windows gives them: only the id tells them apart, and
    # the "(2)" is the row's label (as on Home), not its name.
    sticks[-1].name = sticks[0].name
    ids = [str(d.device_guid.uuid) for d in sticks]
    out["twin-ids"] = ids
    for i, guid in enumerate(ids):
        slug = "pjoy_pro" if i == 0 else "pjoy_pro_2"
        module_file.write_json(
            util.modules_dir() / f"{slug}.json",
            {
                "kind": "control.hardware",
                "device": sticks[i].name,
                "boundGuidLocal": "{" + guid.upper() + "}",
                "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
                "nodes": [],
            },
        )
    # Only the second stick has wires in "Twin": its preview lists that mode,
    # the first one's doesn't.
    twin_uid = sticks[-1].device_guid.uuid
    profile.device_database.devices[twin_uid] = DeviceInfo(twin_uid, sticks[-1].name)
    profile.modes.add_mode("Twin")
    profile.modes.set_parent("Twin", "Default")
    add_map(profile, twin_uid, 4, "Twin", 1, 4)
    pv("reloadDevices()")
    QtTest.QTest.qWait(200)
    rows = json.loads(
        pv(
            "(function(){var r=[];for(var i=0;i<_deviceModel.count;++i){"
            "var d=_deviceModel.get(i);r.push({name:d.name,label:d.label,"
            "guid:String(d.guid||'')})}return JSON.stringify(r)})()"
        )
    )
    out["all-rows"] = rows
    out["twin-rows"] = [r for r in rows if r["name"].startswith("pJoy Pro")]
    shown = []
    for i in range(int(pv("_exportDevice.count"))):
        shown.append(str(pv(f"_exportDevice.textAt({i})")))
    out["twin-shown"] = shown
    # The row named "(2)" as on Home; else (no such row) the second twin's.
    second = next(
        (
            i
            for i, r in enumerate(rows)
            if r["label"] == "pJoy Pro (2)" and r["guid"]
        ),
        next(
            (
                i
                for i, r in enumerate(rows)
                if _key(r["guid"]) == _key(ids[-1])
            ),
            -1,
        ),
    )
    out["twin-second-guid"] = rows[second]["guid"] if second >= 0 else ""
    out["twin-second-index"] = second
    if second >= 0:
        pv(f"_exportDevice.currentIndex = {second}")
        QtTest.QTest.qWait(200)
        out["twin-options"] = json.loads(pv("exportOptions()"))
        out["twin-preview-modes"] = json.loads(pv("JSON.stringify(exportModes)"))
        # The chosen row is kept when the list is read again.
        pv("reloadDevices()")
        out["twin-kept"] = int(pv("_exportDevice.currentIndex")) == second
        zip_path = os.path.join(util.userprofile_path(), "twin.zip")
        url = QtCore.QUrl.fromLocalFile(zip_path).toString()
        got = json.loads(
            pv(f'_hw.exportPack(exportDeviceName(), "{url}", exportOptions())')
        )
        out["twin-export"] = got
        if got.get("ok"):
            with zipfile.ZipFile(zip_path) as zf:
                doc = json.loads(zf.read("map.json"))
            # The pack's label names the device it was made from.
            found = re.findall(r'"exportedGuid":\s*"([^"]*)"', json.dumps(doc))
            out["twin-pack-guid"] = found[0] if found else ""
            import_on_second(url, sticks, second)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if TWINS:
    run_twins()

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
# The vJoy driver missing: the import screen and the warning say so.
from gremlin.modules import output  # noqa: E402

output.vjoy_driver_found = lambda: False
pv("_pages.currentIndex = 1")
pv(f'zipUrl = "{url}"')
pv("loadPack(JSON.parse(_hw.peekPackZip(zipUrl)))")
pv(f'_saveAs.text = "{name}"')
QtTest.QTest.qWait(200)
out["notes"] = child(pack_win, "packNotes").property("text")
drivers = child(pack_win, "packDrivers")
out["drivers-shown"] = bool(drivers and drivers.isVisible())
out["drivers"] = drivers.property("text") if drivers else ""
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


# 01 S142: what happened, on the shared message line (Undo Import link).
def message() -> dict:
    line = child(pack_win, "packMessage")
    link = child(pack_win, "messageUndo")
    return {
        "shown": bool(line and line.isVisible()),
        "text": line.property("text") if line else "",
        "failed": bool(line.property("failed")) if line else None,
        "undo": link.property("text") if link and link.isVisible() else "",
    }


out["message-after"] = message()
buttons = sorted(
    item.input_id
    for item in shared_state.current_profile.inputs.get(uid, [])
    if item.mode == "Default" and item.action_sequences
)
out["default-after"] = buttons

out["logical-created"] = LogicalDevice().exists(
    LogicalDevice.Input.Identifier(InputType.JoystickButton, 9)
)

# The same import again, but the module file can't be written: nothing is
# replaced, and Undo Import still offers the import before it.
def _cannot_write(*_args: object, **_kwargs: object) -> str:
    raise OSError("locked")


_write_module = device_pack._write_module
device_pack._write_module = _cannot_write
pv("runImport()")
QtTest.QTest.qWait(300)
device_pack._write_module = _write_module
out["status-failed"] = pv("status")
out["message-failed"] = message()
undo_button = child(pack_win, "packUndo")
out["undo-after-failed"] = bool(undo_button and undo_button.isVisible())
out["backend-undo-after-failed"] = device_pack.can_undo_import()

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
out["message-undone"] = message()

# 01 S143: the choosers open in the last folder used for Device Packs
# (the folder is remembered on accept; no native dialog is shown).
chosen = pathlib.Path(zip_path).parent / "picked"
chosen.mkdir(exist_ok=True)
pick_url = QtCore.QUrl.fromLocalFile(str(chosen / "other.zip")).toString()
pv(f'_pick._accept("{pick_url}")')
QtTest.QTest.qWait(200)
out["remembered"] = str(pv("String(_save.prepare().currentFolder)"))
out["remembered-want"] = QtCore.QUrl.fromLocalFile(str(chosen)).toString()
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive

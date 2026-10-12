# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of Export / Import Device end to end (test_b2_e2e.py,
D-FIXLIST-B2, 08 S49-S114): the real main window and the real
DialogDevicePack.qml over fake hardware. Each step records its findings
(or its error) under its own key, so one missing piece doesn't hide the
rest. Prints RESULT {json}."""

from __future__ import annotations

import json
import os
import shutil
import sys
import traceback
import uuid
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, ".")
import importlib.util

spec = importlib.util.spec_from_file_location("fake_hardware", "test/fake_hardware.py")
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

from gremlin import device_initialization, plugin_manager, shared_state  # noqa: E402
from gremlin.modules import module_file, store  # noqa: E402
from gremlin.profile import DeviceInfo, Profile  # noqa: E402
from gremlin.types import InputType  # noqa: E402

TITLE = "Export / Import Device"
# A 1x1 PNG.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cfc0f01f0005000201a5c7"
    "c2a60000000049454e44ae426082"
)
out: dict = {"errors": {}}
# Outside the program's folder (an export inside the modules folder is refused).
files = Path(os.environ["USERPROFILE"]) / "b2files"
files.mkdir(exist_ok=True)


def step(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001 - recorded for the test to show
        out["errors"][name] = traceback.format_exc()[-1500:]


def wait_until(cond: Callable[[], bool], limit_ms: int = 8000) -> bool:
    waited = 0
    while waited < limit_ms:
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        QtTest.QTest.qWait(50)
        waited += 50
    return False


def ev(host: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(host), host, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


def walk(item: QtQuick.QQuickItem) -> Iterator[QtQuick.QQuickItem]:
    yield item
    for child in item.childItems():
        yield from walk(child)


def named(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
    for item in walk(window.contentItem()):
        if item.objectName() == name:
            return item
    return window.findChild(QtQuick.QQuickItem, name)


def click(window: QtQuick.QQuickWindow, item: QtQuick.QQuickItem | None) -> None:
    assert item is not None, "control not found"
    QtTest.QTest.mouseClick(
        window,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2)).toPoint(),
    )
    QtTest.QTest.qWait(300)


def pack_windows() -> list[QtQuick.QQuickWindow]:
    return [
        w
        for w in app.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow)
        and w is not win
        and w.isVisible()
        and (w.title().startswith(TITLE) or w.title().startswith("Device Pack"))
    ]


def close_packs() -> None:
    for w in pack_windows():
        w.close()
    wait_until(lambda: not pack_windows(), 4000)


def new_pack_window() -> QtQuick.QQuickWindow:
    assert wait_until(lambda: bool(pack_windows()), 4000), "no Export / Import window"
    w = pack_windows()[-1]
    w.resize(900, 800)
    QtTest.QTest.qWait(200)
    return w


def status_changed(w: QtQuick.QQuickWindow, before: str) -> None:
    """Until the window's message line says something new (bounded)."""
    wait_until(lambda: str(ev(w, "status")) != before)


def add_map(profile: Profile, uid: uuid.UUID, button: int, mode: str) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def wired(uid: uuid.UUID, mode: str) -> list[int]:
    return sorted(
        item.input_id
        for item in shared_state.current_profile.inputs.get(uid, [])
        if item.mode == mode and item.action_sequences
    )


def folders() -> list[str]:
    root = store.folder()
    return sorted(p.name for p in Path(root).iterdir() if p.is_dir())


def url_of(path: Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(path)).toString()


# --- setup: pJoy Pro with its folder, two modes, wires to vJoy 1 -------------
stick = next(
    d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
)
name, uid = stick.name, stick.device_guid.uuid
guid = str(stick.device_guid)
profile = shared_state.current_profile
profile.device_database.devices[uid] = DeviceInfo(uid, name)
profile.modes.add_mode("Combat")
profile.modes.set_parent("Combat", "Default")
add_map(profile, uid, 1, "Default")
add_map(profile, uid, 2, "Combat")
stick_file = store.module_file_in(store.ensure_device_dir(name, guid))
module_file.write_json(
    stick_file,
    {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "keys": []},
        "nodes": [],
    },
)


def setup_output() -> None:
    """vJoy 1's own folder with a picture layer: its picture must travel."""
    match = store.match_known_device("vJoy 1")
    out["vjoy-match"] = bool(match)
    vguid = str(match["guid"]) if match and match.get("guid") else ""
    base = store.ensure_device_dir("vJoy 1", vguid)
    (base / store.PICTURES).mkdir(exist_ok=True)
    (base / store.PICTURES / "face.png").write_bytes(PNG)
    module_file.write_json(
        store.module_file_in(base),
        {
            "kind": "control.hardware",
            "device": "vJoy 1",
            "direction": "dest",
            "claim": {"buttons": [1, 2], "axes": [], "hats": [], "keys": []},
            "nodes": [{"id": "n1", "shape": "image", "src": "pictures/face.png"}],
        },
    )


step("setup-output", setup_output)
stick_before = stick_file.read_bytes()


# --- 1. Tools › Export / Import Device ---------------------------------------
def tools_route() -> None:
    texts = json.loads(
        ev(
            win,
            "JSON.stringify(MainCommands.commandList()"
            ".map(function(c){return c.text}))",
        )
    )
    out["tools-texts"] = [t for t in texts if "Device" in t]
    ev(
        win,
        "(function(){var l=MainCommands.commandList();for(var i=0;i<l.length;++i)"
        f"if(l[i].text==={json.dumps(TITLE)}){{l[i].run();return true}}"
        "return false})()",
    )
    w = new_pack_window()
    out["tools-title"] = w.title()
    out["tools-mode"] = str(ev(w, "mode"))
    out["save-filters"] = json.loads(ev(w, "JSON.stringify(_save.nameFilters)"))
    out["save-suffix"] = str(ev(w, "_save.defaultSuffix"))
    out["pick-filters"] = json.loads(ev(w, "JSON.stringify(_pick.nameFilters)"))
    out["default-url"] = str(ev(w, f"_hw.defaultExportUrl({json.dumps(name)})"))
    close_packs()


step("tools", tools_route)


# --- 2. Export: Made by, Note, chosen modes -> .gmap -----------------------------
gmap_path = files / "pjoy.gmap"


def export() -> None:
    ev(win, 'Helpers.createComponent("DialogDevicePack.qml")')
    w = new_pack_window()
    ev(w, f'openFor("export", {json.dumps(name)}, {json.dumps(guid)})')
    QtTest.QTest.qWait(300)
    out["export-device"] = str(ev(w, "exportDeviceName()"))
    out["export-modes"] = json.loads(ev(w, "JSON.stringify(exportModes)"))
    ev(
        w,
        '_author.text = "Sam"; _note.text = "My setup"; exportTicks["Combat"] = false',
    )
    ev(w, f"_save._accept({json.dumps(url_of(gmap_path))})")
    wait_until(lambda: gmap_path.is_file() and not ev(w, "_hw.packExporting"))
    out["export-written"] = gmap_path.is_file()
    out["export-status"] = str(ev(w, "status"))
    line = named(w, "packMessage")
    out["export-message"] = str(line.property("text")) if line else ""
    out["zip-written"] = sorted(p.name for p in files.iterdir() if p.suffix == ".zip")
    if gmap_path.is_file():
        with zipfile.ZipFile(gmap_path) as zf:
            names = zf.namelist()
            label = json.loads(zf.read("gmap.json"))
            wires = (
                json.loads(zf.read("bindings/wires.json"))
                if "bindings/wires.json" in names
                else {}
            )
        out["gmap-names"] = names
        out["gmap-label"] = label
        out["gmap-wires"] = wires
        out["gmap-wire-modes"] = [
            m.get("name") if isinstance(m, dict) else m for m in wires.get("modes", [])
        ]
        from gremlin.modules import device_zip

        read = device_zip.read_gmap(gmap_path)
        out["read-gmap"] = (
            read
            if isinstance(read, str)
            else {k: read.get(k) for k in ("madeBy", "note", "modes")}
            | {"outputPictures": sorted(read.get("outputPictures") or [])}
        )
    close_packs()


step("export", export)


# --- 3. Import As a new device: "(2)", Undo Import removes it -------------------
def import_new() -> None:
    ev(win, 'Helpers.createComponent("DialogDevicePack.qml")')
    w = new_pack_window()
    ev(w, f'openFor("import", {json.dumps(name)}, {json.dumps(guid)})')
    ev(w, f"_pick._accept({json.dumps(url_of(gmap_path))})")
    wait_until(lambda: str(ev(w, "fileUrl")) == url_of(gmap_path))
    new_r, old_r = named(w, "packTargetNew"), named(w, "packTargetExisting")
    out["new-radios"] = [new_r is not None, old_r is not None]
    # pJoy Pro has a folder: "Onto an existing device" is the default.
    out["new-default-existing"] = bool(old_r and old_r.property("checked"))
    click(w, new_r)
    out["new-picked"] = bool(new_r.property("checked"))
    before = folders()
    before_status = str(ev(w, "status"))
    click(w, named(w, "packImport"))
    replace = named(w, "packReplace")
    if replace is not None and replace.isVisible():
        click(w, replace)
    status_changed(w, before_status)
    after = folders()
    out["new-folders"] = [f for f in after if f not in before]
    out["new-status"] = str(ev(w, "status"))
    out["new-stick-unchanged"] = stick_file.read_bytes() == stick_before
    undo = named(w, "packUndo")
    out["new-undo-shown"] = bool(undo and undo.isVisible())
    before_status = str(ev(w, "status"))
    ev(w, "undoImport()")
    status_changed(w, before_status)
    out["new-after-undo"] = [f for f in folders() if f not in before]
    close_packs()


step("import-new", import_new)


# --- 3b. A file whose device has no folder: "As a new device" is the default ----
def import_default_new() -> None:
    """The same stick's file but another id (a twin elsewhere): its name is
    taken here, so As a new device (the default: no folder for that id)
    makes "pJoy Pro (2)", and Undo Import removes it."""
    twin = files / "twin.gmap"
    with zipfile.ZipFile(gmap_path) as src, zipfile.ZipFile(twin, "w") as dst:
        for item in src.namelist():
            data = src.read(item)
            if item == "gmap.json":
                label = json.loads(data)
                label["id"] = "ABCDEF01020311F08004444553540000"
                data = json.dumps(label).encode()
            dst.writestr(item, data)
    ev(win, 'Helpers.createComponent("DialogDevicePack.qml")')
    w = new_pack_window()
    ev(w, f"_pick._accept({json.dumps(url_of(twin))})")
    wait_until(lambda: str(ev(w, "fileUrl")) == url_of(twin))
    new_r = named(w, "packTargetNew")
    out["twin-default-new"] = bool(new_r and new_r.property("checked"))
    click(w, new_r)
    # The output's tick off: its module file here is left alone.
    out["twin-out-items"] = json.loads(
        ev(
            w,
            "(function(){var r=[];for(var s=0;s<sections.length;++s){"
            "if(String(sections[s].id||'').indexOf('out:')!==0)continue;"
            "var it=sections[s].items||[];for(var i=0;i<it.length;++i){"
            "checks[it[i].id]=false;r.push(it[i].id)}}tickRev=tickRev+1;"
            "return JSON.stringify(r)})()",
        )
    )
    vjoy_file = store.module_file_in(store.device_dir("vJoy 1", ""))
    vjoy_before = vjoy_file.read_bytes() if vjoy_file.is_file() else b""
    before = folders()
    before_status = str(ev(w, "status"))
    click(w, named(w, "packImport"))
    replace = named(w, "packReplace")
    if replace is not None and replace.isVisible():
        click(w, replace)
    status_changed(w, before_status)
    out["twin-folders"] = [f for f in folders() if f not in before]
    out["twin-status"] = str(ev(w, "status"))
    out["twin-stick-unchanged"] = stick_file.read_bytes() == stick_before
    out["twin-output-unchanged"] = (
        vjoy_file.read_bytes() if vjoy_file.is_file() else b""
    ) == vjoy_before
    undo = named(w, "packUndo")
    out["twin-undo-shown"] = bool(undo and undo.isVisible())
    before_status = str(ev(w, "status"))
    ev(w, "undoImport()")
    status_changed(w, before_status)
    out["twin-after-undo"] = [f for f in folders() if f not in before]
    close_packs()


step("import-default-new", import_default_new)


# --- 4. Import Onto an existing device: preview, Replace, Undo Import -----------
def import_existing() -> None:
    add_map(shared_state.current_profile, uid, 3, "Default")
    out["existing-before"] = wired(uid, "Default")
    ev(win, 'Helpers.createComponent("DialogDevicePack.qml")')
    w = new_pack_window()
    ev(w, f'openFor("import", {json.dumps(name)}, {json.dumps(guid)})')
    ev(w, f"_pick._accept({json.dumps(url_of(gmap_path))})")
    wait_until(lambda: str(ev(w, "fileUrl")) == url_of(gmap_path))
    click(w, named(w, "packTargetExisting"))
    out["existing-target"] = str(ev(w, "_saveAs.text"))
    ev(
        w,
        'for (var k in checks) checks[k] = false; checks["wire:Default"] = true; '
        "tickRev = tickRev + 1",
    )
    before_status = str(ev(w, "status"))
    click(w, named(w, "packImport"))
    warn = w.findChild(QtCore.QObject, "packWarning")
    out["existing-warning"] = bool(warn and warn.property("opened"))
    text = named(w, "packWarningText")
    out["existing-warning-text"] = str(text.property("text")) if text else ""
    replace = named(w, "packReplace")
    out["existing-replace"] = [
        replace is not None,
        bool(replace and replace.isVisible()),
    ]
    if replace is not None and replace.isVisible():
        click(w, replace)
    status_changed(w, before_status)
    out["existing-status"] = str(ev(w, "status"))
    out["existing-after"] = wired(uid, "Default")
    out["existing-folders-same"] = (
        store.device_dir(name, guid) / "module.json"
    ).is_file()
    undo = named(w, "packUndo")
    out["existing-undo-shown"] = bool(undo and undo.isVisible())
    before_status = str(ev(w, "status"))
    ev(w, "undoImport()")
    status_changed(w, before_status)
    out["existing-undone"] = wired(uid, "Default")
    close_packs()


step("import-existing", import_existing)


# --- 5. Home card Export Device… / Import Device… -------------------------------
def inner(item: QtCore.QObject) -> QtCore.QObject:
    for child in item.childItems():
        own = QtQml.qmlContext(child)
        if own is not None and own != QtQml.qmlContext(item):
            return child
    return item


def home_routes() -> None:
    try:
        ev(win, "_moduleModel.reload()")
    except AssertionError:
        pass
    assert wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))
    page = inner(ev(win, "_statusLoader.item"))
    find = (
        "(function(){for(var i=0;i<_liveCards.length;++i){var c=_liveCards[i];"
        f"if(c&&(c.rawName==={json.dumps(name)}||"
        f"c.cardName==={json.dumps(name)}))return c}}"
        "return null})()"
    )
    assert wait_until(lambda: ev(page, find) is not None), "no pJoy Pro card"
    for tab, signal in (("export", "exportDevice"), ("import", "importDevice")):
        ev(page, f"{find}.{signal}()")
        w = new_pack_window()
        out[f"home-{tab}-title"] = w.title()
        out[f"home-{tab}-mode"] = str(ev(w, "mode"))
        if tab == "export":
            out["home-export-device"] = str(ev(w, "exportDeviceName()"))
        else:
            out["home-import-target"] = [
                str(ev(w, "_saveAs.text")),
                str(ev(w, "_importDevice.displayText")),
            ]
        close_packs()


step("home", home_routes)

print("RESULT " + json.dumps(out, default=str), flush=True)
shutil.rmtree(files, ignore_errors=True)
smoke_exit(0)

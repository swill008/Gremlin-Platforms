# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware, a temporary user
folder) and drives the Button Map window as the user does: Edit Mapping,
Save, Cancel and its question, closing with unsaved edits, the recovery
offer, Choose / Clear Photo, the print area and guides, Copy Button Map from
Device, and the module file being changed elsewhere (History Restore,
Module Setup's photo, a Device Pack import, Delete Device) while the map is
open. Other parts drive Module Setup's Import Image then Cancel (setup), the
History window as the Button Map and a Configuration row open it (history),
and a restart with unsaved changes (quit). Prints what it saw as one
"RESULT {json}" line; a step it could not do as the user does is an "error"
(DriveError), never a result. test_stage1_button_map.py runs it in its own
process, one part at a time (also for test_stage1_modules,
test_stage1_history_pack and test_stage1_app_profile).

    python test/unit/stage1_button_map_smoke.py flows|outside|setup|history|quit

Waits poll for the result with a generous limit; none sleeps a fixed time.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Never the user's own folder: the pytest side gives a temporary one.
_HOME = Path(os.environ.get("USERPROFILE", "")).resolve()
_USERS = Path(os.environ.get("SystemDrive", "C:") + "/Users")
_REAL_HOME = (_USERS / os.environ.get("USERNAME", "")).resolve()
if not os.environ.get("USERPROFILE") or _HOME == _REAL_HOME or (
    os.environ.get("QT_QPA_PLATFORM") != "offscreen"
):
    print("RESULT " + json.dumps({"error": "not a test folder or not off-screen"}))
    sys.exit(2)

spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert spec is not None and spec.loader is not None
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
from gremlin import clock, history  # noqa: E402
from gremlin.ui import hardware_profile as hp  # noqa: E402

# A third stick, with no module file (GL-175).
third = fake_hardware.raw_device(is_virtual=False)
third.device_guid.Data1 += 11
third.name = b"Third Stick"
fake.devices.append(third)

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
THIRD_GUID = str(dill.GUID(third.device_guid).uuid)
NAME = "pJoy Pro"
CARD = {"rawName": NAME, "name": NAME, "guid": GUID}

# Generous: a busy PC is slow, never wrong.
LIMIT = 15.0


def chip(hw: int, fx: float) -> dict:
    return {
        "kind": "btn", "id": f"b{hw}", "hwId": hw, "label": f"Button {hw}",
        "chipFx": fx, "chipFy": 0.3,
    }


MAP_FILE = hp.module_json_path(NAME, GUID)
SLUG = MAP_FILE.stem
MODULES = MAP_FILE.parent
RECOVERY = MODULES / "recovery" / f"{SLUG}.json"
START_NODES = [chip(1, 0.20), chip(2, 0.30), chip(3, 0.40)]
# Another device's map: two of its chips are for buttons this stick (64
# buttons) does not have (07 Q8).
OTHER_NODES = [chip(1, 0.25), chip(2, 0.35), chip(70, 0.45), chip(80, 0.55)]


def write_json(path: Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def read_doc(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


write_json(MAP_FILE, {
    "kind": "control.hardware", "device": NAME,
    "image": f"{SLUG}/photo.png", "nodes": START_NODES,
    # The Configuration page lists claimed controls (the history part).
    **({"claim": {"buttons": [1, 2, 3], "axes": [], "hats": [], "keys": []}}
       if sys.argv[1:2] == ["history"] else {}),
})
write_json(MODULES / "other_stick.json", {
    "kind": "control.hardware", "device": "Other Stick", "nodes": OTHER_NODES,
})
# Damaged other files: not UTF-8, and JSON that is not an object (GL-021).
(MODULES / "broken_stick.json").write_bytes(b"\xff\xfe{ not json")
write_json(MODULES / "list_stick.json", [1, 2, 3])

import joystick_gremlin  # noqa: E402


def wait_for(cond: Callable[[], object], limit: float = LIMIT) -> object:
    """Runs the event loop until cond() is true (its value), up to limit."""
    end = clock.monotonic() + limit
    while True:
        value = cond()
        if value or clock.monotonic() > end:
            return value
        QtTest.QTest.qWait(25)


def expression(obj: QtCore.QObject, code: str) -> QtQml.QQmlExpression:
    """code (JavaScript) in obj's own QML scope."""
    context = QtQml.qmlContext(obj)
    assert context is not None
    return QtQml.QQmlExpression(context, obj, code)


def hw_ids(nodes: object) -> list[int]:
    """The chips' control numbers, sorted."""
    rows = nodes if isinstance(nodes, list) else []
    return sorted(int(n.get("hwId") or 0) for n in rows if isinstance(n, dict))


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def make_picture(path: Path, colour: str) -> Path:
    image = QtGui.QImage(64, 48, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(colour))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(path))
    return path


def shown(win: QtCore.QObject | None) -> bool:
    """The window is open (closed: hidden, or already gone)."""
    return (
        win is not None and shiboken6.isValid(win) and bool(win.property("visible"))
    )


def history_quiet() -> None:
    """Waits until History has written everything it was given."""
    wait_for(lambda: history._writer is None and history._queue.empty())


def history_count() -> int:
    history_quiet()
    return len([
        e for e in history.entries()
        if (e.get("subject") or {}).get("fileName") == MAP_FILE.name
    ])


# Presses the button labelled LABEL in dialog DLG, as a click does.
_PRESS = (
    "(function() { function find(it, label) { if (!it) return null;"
    " if (it.text === label && it.visible && typeof it.clicked === 'function')"
    " return it; var kids = it.children || [];"
    " for (var i = 0; i < kids.length; i++) { var f = find(kids[i], label);"
    " if (f) return f } return null }"
    " var b = find(DLG.contentItem, LABEL); if (!b) return false;"
    " b.clicked(); return true })()"
)


class Window:
    """The Button Map window, driven through its own functions."""

    def __init__(self, root: QtCore.QObject) -> None:
        self.root = root

    @property
    def win(self) -> QtCore.QObject:
        return call(self.root, "buttonMapWindow")  # type: ignore[return-value]

    def ev(self, code: str) -> object:
        win = self.win
        expr = expression(win, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(f"{code[:80]}: {expr.error().toString()}")
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def js(self, code: str) -> object:
        """A JSON-able value from a JS expression."""
        text = self.ev(f"JSON.stringify({code})")
        return json.loads(text) if isinstance(text, str) and text else None

    def press(self, dialog: str, label: str) -> bool:
        code = _PRESS.replace("DLG", dialog).replace("LABEL", json.dumps(label))
        return bool(self.ev(code))

    def opened(self, dialog: str) -> bool:
        return bool(self.ev(f"{dialog}.opened"))

    def ok_if_open(self, dialog: str) -> None:
        if self.opened(dialog):
            self.press(dialog, "OK")
            wait_for(lambda: not self.opened(dialog))

    def nodes(self) -> list[dict]:
        value = self.js("(_ed() && _ed().nodes) ? _ed().nodes : []")
        return value if isinstance(value, list) else []

    def chip_fx(self, hw: int, nodes: list[dict] | None = None) -> float | None:
        for n in self.nodes() if nodes is None else nodes:
            if n.get("hwId") == hw:
                return n.get("chipFx")
        return None

    def enter_edit(self) -> bool:
        self.ev("_buttonMap.enterEdit()")
        return bool(wait_for(
            lambda: self.ev("_buttonMap.editing && _ed() !== null && _ed().seeded"
                            " && !_buttonMap._baseWanted")
        ))

    def move(self, hw: int, by: float) -> None:
        self.ev(
            "(function() { var e = _ed(); for (var i = 0; i < e.nodes.length; i++)"
            f" if (e.nodes[i].hwId === {hw}) e.nodes[i].chipFx += {by};"
            " e.bump(); return true })()"
        )
        wait_for(lambda: self.ev("_buttonMap.isDirty()"))

    def leave_edit(self) -> None:
        """Cancel, discarding anything unsaved."""
        if not self.ev("_buttonMap.editing"):
            return
        self.ev("_buttonMap.cancelEdit()")
        if self.opened("_saveGate"):
            self.press("_saveGate", "Discard")
        wait_for(lambda: not self.ev("_buttonMap.editing"))


def file_fx(hw: int) -> float | None:
    for n in read_doc(MAP_FILE).get("nodes") or []:
        if isinstance(n, dict) and n.get("hwId") == hw:
            return n.get("chipFx")
    return None


def open_map(app: joystick_gremlin.JoystickGremlinApp) -> Window:
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    call(root, "openButtonMapForCard", CARD)
    w = Window(root)
    wait_for(lambda: w.win is not None)
    wait_for(lambda: w.ev("_buttonMap.faceLive && _ed() !== null"
                          " && _ed().nodes.length > 0"))
    return w


# +-------------------------------------------------------------------------
# | Save, Cancel, leave prompts, photo, print area, copy, recovery


def part_flows(app: joystick_gremlin.JoystickGremlinApp, out: dict) -> None:
    make_picture(MODULES / SLUG / "photo.png", "#204060")
    chosen = make_picture(_HOME / "pictures" / "new photo.jpg", "#a05020")
    w = open_map(app)

    # Save (S20, S24).
    w.enter_edit()
    out["dirty-on-entering-edit"] = w.ev("_buttonMap.isDirty()")
    w.move(1, 0.05)
    moved = w.chip_fx(1)
    w.ev("_buttonMap.saveEdit(true)")
    wait_for(lambda: w.opened("_saveGate"))
    out["save-said"] = [w.ev("_saveGate.titleText"), w.ev("_saveGate.messageText")]
    w.ok_if_open("_saveGate")
    out["save-wrote"] = file_fx(1) == moved and moved is not None
    out["dirty-after-save"] = w.ev("_buttonMap.isDirty()")
    out["editing-after-save"] = w.ev("_buttonMap.editing")
    saved_fx = file_fx(1)

    # Cancel with changes asks; Discard leaves the file and no undo (S25, S26).
    w.move(1, 0.05)
    w.ev("_buttonMap.cancelEdit()")
    asked = bool(wait_for(lambda: w.opened("_saveGate")))
    out["cancel-asks"] = [asked, w.ev("_saveGate.titleText"),
                          w.ev("_buttonMap.leaveKind")]
    w.press("_saveGate", "Discard")
    wait_for(lambda: not w.ev("_buttonMap.editing"))
    wait_for(lambda: not w.ev("_ed().canUndo"))
    out["cancel-discard"] = {
        "editing": w.ev("_buttonMap.editing"),
        "file-kept": file_fx(1) == saved_fx,
        "shown": w.chip_fx(1) == saved_fx,
        "can-undo": w.ev("_ed().canUndo"),
    }

    # Cancel, then Save in its question: saved and out of Edit (S25).
    w.enter_edit()
    w.move(2, 0.05)
    want = w.chip_fx(2)
    w.ev("_buttonMap.cancelEdit()")
    wait_for(lambda: w.opened("_saveGate"))
    w.press("_saveGate", "Save")
    wait_for(lambda: not w.ev("_buttonMap.editing"))
    out["cancel-save"] = {
        "editing": w.ev("_buttonMap.editing"),
        "written": file_fx(2) == want and want is not None,
    }
    wait_for(lambda: w.opened("_saveGate"))
    w.ok_if_open("_saveGate")

    # Cancel with nothing changed doesn't ask (S19).
    w.enter_edit()
    w.ev("_buttonMap.cancelEdit()")
    wait_for(lambda: not w.ev("_buttonMap.editing"))
    out["cancel-clean"] = [w.ev("_buttonMap.editing"), w.opened("_saveGate")]

    # Choose Photo, then Cancel: the starting photo comes back (S26, S40);
    # History and the module file (07 Q2, GL-174).
    image0 = read_doc(MAP_FILE).get("image")
    h0 = history_count()
    w.enter_edit()
    w.ev("_imageDialog.selectedFile = "
         + json.dumps(QtCore.QUrl.fromLocalFile(str(chosen)).toString())
         + "; _imageDialog.accepted(); true")
    wait_for(lambda: str(w.ev("_buttonMap.storedImage")).endswith(".jpg"))
    h1 = history_count()
    out["choose-photo"] = {
        "shown": w.ev("_buttonMap.storedImage"),
        "dirty": w.ev("_buttonMap.isDirty()"),
        "file-image-before-save": read_doc(MAP_FILE).get("image"),
        "start-image": image0,
        "history-before-save": h1 - h0,
    }
    w.leave_edit()
    h2 = history_count()
    out["choose-photo-cancel"] = {
        "file-image": read_doc(MAP_FILE).get("image"),
        "start-image": image0,
        "old-photo": (MODULES / SLUG / "photo.png").is_file(),
        "new-photo": (MODULES / SLUG / "photo.jpg").is_file(),
        "history-after-cancel": h2 - h0,
        "shown": w.ev("_buttonMap.storedImage"),
    }

    # Choose Photo, then Save: one History entry, at Save (07 Q2).
    h3 = history_count()
    w.enter_edit()
    w.ev("_imageDialog.selectedFile = "
         + json.dumps(QtCore.QUrl.fromLocalFile(str(chosen)).toString())
         + "; _imageDialog.accepted(); true")
    wait_for(lambda: str(w.ev("_buttonMap.storedImage")).endswith(".jpg"))
    h4 = history_count()
    w.ev("_buttonMap.saveEdit(false)")
    h5 = history_count()
    out["choose-photo-save"] = {
        "file-image": read_doc(MAP_FILE).get("image"),
        "before-save": h4 - h3,
        "after-save": h5 - h3,
    }
    w.leave_edit()

    # Clear Photo, then Cancel: no History entry, the photo comes back.
    def menu_item(text: str) -> str:
        return (
            "(function() { for (var i = 0; i < _photoMenu.count; i++) {"
            " var it = _photoMenu.itemAt(i);"
            f" if (it && it.text === {json.dumps(text)})"
            " { it.triggered(); return true } } return false })()"
        )

    h6 = history_count()
    w.enter_edit()
    out["clear-photo-ran"] = w.ev(menu_item("Clear Photo"))
    wait_for(lambda: w.ev("_buttonMap.storedImage === \"\""))
    h7 = history_count()
    out["clear-photo"] = {
        "photo-files-left": sorted(p.name for p in (MODULES / SLUG).glob("photo.*")),
        # Clear Photo leaves no photo (07 Q4, GL-221).
        "shown": [w.ev("_buttonMap.storedImage"), w.ev("_buttonMap.photoOverride")],
        "dirty": w.ev("_buttonMap.isDirty()"),
        "history-before-save": h7 - h6,
    }
    w.leave_edit()
    out["clear-photo-cancel"] = {
        "photo-back": (MODULES / SLUG / "photo.jpg").is_file(),
        "history": history_count() - h6,
        "file-image": read_doc(MAP_FILE).get("image"),
    }

    # Clear Photo when the file can't be removed (open elsewhere): the photo
    # stays and "Clear Photo Failed" is said (S41).
    w.enter_edit()
    held = (MODULES / SLUG / "photo.jpg").open("rb")
    try:
        w.ev(menu_item("Clear Photo"))
        wait_for(lambda: w.opened("_failNotice"))
        out["clear-photo-fails"] = {
            "said": [w.ev("_failNotice.opened"), w.ev("_failNotice.titleText")],
            "photo-kept": (MODULES / SLUG / "photo.jpg").is_file(),
            "shown": w.ev("_buttonMap.storedImage"),
        }
    finally:
        held.close()
    w.ok_if_open("_failNotice")
    w.leave_edit()
    out["clear-photo-fails"]["after-cancel"] = (MODULES / SLUG / "photo.jpg").is_file()

    # Choose Photo and Clear Photo are undo steps (07 Q3, GL-179).
    other = make_picture(_HOME / "pictures" / "other photo.png", "#20a0a0")
    saved_image = read_doc(MAP_FILE).get("image")
    w.enter_edit()
    w.ev("_imageDialog.selectedFile = "
         + json.dumps(QtCore.QUrl.fromLocalFile(str(other)).toString())
         + "; _imageDialog.accepted(); true")
    wait_for(lambda: str(w.ev("_buttonMap.storedImage")).endswith(".png"))
    w.ev("_ed().flushPendingStep()")
    w.ev(menu_item("Clear Photo"))
    wait_for(lambda: w.ev("_buttonMap.storedImage === \"\""))
    w.ev("_ed().flushPendingStep()")
    w.ev("_ed().undo()")
    after_one = {
        "shown": w.ev("_buttonMap.storedImage"),
        "file": (MODULES / SLUG / "photo.png").is_file(),
    }
    w.ev("_ed().undo()")
    out["photo-undo"] = {
        "after-one": after_one,
        "after-two": w.ev("_buttonMap.storedImage"),
        "saved": saved_image,
        "jpg-back": (MODULES / SLUG / "photo.jpg").is_file(),
        "png-gone": not (MODULES / SLUG / "photo.png").exists(),
        "dirty": w.ev("_buttonMap.isDirty()"),
    }
    w.ev("_ed().redo()")
    out["photo-redo"] = str(w.ev("_buttonMap.storedImage"))
    w.leave_edit()
    out["photo-undo"]["after-cancel"] = read_doc(MAP_FILE).get("image") == saved_image

    # A guide and the print area are undo steps too (07 Q3, GL-179).
    w.enter_edit()
    w.ev("(function() { var e = _ed(); e.rulerGuidesX = [0.25];"
         " e.rulerGuidesEdited(); return true })()")
    w.ev("(function() { var e = _ed();"
         " e.printArea = {fx: 0.1, fy: 0.1, fw: 0.3, fh: 0.3};"
         " e.printAreaEdited(false); return true })()")
    w.ev("_ed().undo()")
    undo_one = {"printArea": w.js("_buttonMap.printArea"),
                "guidesX": w.js("_buttonMap.guidesX") or []}
    w.ev("_ed().undo()")
    out["ui-undo"] = {
        "after-one": undo_one,
        "after-two": {"printArea": w.js("_buttonMap.printArea"),
                      "guidesX": w.js("_buttonMap.guidesX") or []},
        "dirty": w.ev("_buttonMap.isDirty()"),
    }
    w.leave_edit()

    # Print area and a guide changed in Edit, then Cancel (07 Q1, GL-173).
    before_ui = read_doc(MAP_FILE).get("ui") or {}
    out["ui-before"] = {"printArea": before_ui.get("printArea"),
                        "guidesX": before_ui.get("guidesX") or []}
    w.enter_edit()
    w.ev("(function() { var e = _ed();"
         " e.printArea = {fx: 0.2, fy: 0.2, fw: 0.4, fh: 0.4};"
         " e.printAreaEdited(true);"
         " e.rulerGuidesX = [0.33]; e.rulerGuidesEdited(); return true })()")
    mid = read_doc(MAP_FILE).get("ui") or {}
    out["ui-mid-edit"] = {"printArea": mid.get("printArea"),
                          "guidesX": mid.get("guidesX") or []}
    w.leave_edit()
    after = read_doc(MAP_FILE).get("ui") or {}
    out["ui-after-cancel"] = {"printArea": after.get("printArea"),
                              "guidesX": after.get("guidesX") or []}
    out["ui-shown-after-cancel"] = {
        "printArea": w.js("_buttonMap.printArea"),
        "guidesX": w.js("_buttonMap.guidesX") or [],
    }

    # Copy Button Map from Device (S75-S77; 07 Q8, GL-182; damaged other
    # files, GL-021).
    listed = w.js("_hw.savedLayouts(_buttonMap.targetName)")
    rows = listed if isinstance(listed, list) else []
    out["copy-list"] = sorted(r["name"] for r in rows)
    row = next((r for r in rows if r["name"] == "Other Stick"), None)
    w.ev("_buttonMap.openCopyLayout(" + json.dumps(row) + ")")
    wait_for(lambda: w.opened("_copyDlg"))
    out["mirror-tick-device"] = w.ev("_copyMirror.checked")
    w.ev("_copyDlg.close()")
    wait_for(lambda: not w.opened("_copyDlg"))
    w.ev("_buttonMap.openCopyLayout({name: 'Mine', template: true})")
    wait_for(lambda: w.opened("_copyDlg"))
    out["mirror-tick-template"] = w.ev("_copyDlg.opened && _copyMirror.checked")
    w.ev("_copyDlg.close()")
    wait_for(lambda: not w.opened("_copyDlg"))
    file_before = MAP_FILE.read_text(encoding="utf-8")
    old_ids = hw_ids(w.nodes())
    w.ev("_buttonMap.copyLayoutFrom(" + json.dumps(row) + ", false)")
    wait_for(lambda: 80 in [n.get("hwId") for n in w.nodes()])
    message = wait_for(lambda: w.ev("_ed().findMsg"))
    out["copy"] = {
        "editing": w.ev("_buttonMap.editing"),
        "hw-ids": hw_ids(w.nodes()),
        "file-untouched": MAP_FILE.read_text(encoding="utf-8") == file_before,
        "message": message,
        "dirty": w.ev("_buttonMap.isDirty()"),
    }
    w.ev("_ed().undo()")
    wait_for(lambda: 80 not in [n.get("hwId") for n in w.nodes()])
    out["copy-undo"] = hw_ids(w.nodes()) == old_ids
    # A mirrored copy: one Undo puts the old map back (S78, GL-184).
    old_fx = {n.get("hwId"): n.get("chipFx") for n in w.nodes()}
    w.ev("_ed().findMsg = ''")
    w.ev("_buttonMap.copyLayoutFrom(" + json.dumps(row) + ", true)")
    wait_for(lambda: w.ev("_ed().findMsg.length > 0 && _ed().seeded"))
    w.ev("_ed().flushPendingStep()")
    w.ev("_ed().undo()")
    out["mirror-copy-undo"] = {
        "ids": hw_ids(w.nodes()) == old_ids,
        "fx": {n.get("hwId"): n.get("chipFx") for n in w.nodes()} == old_fx,
    }
    w.leave_edit()

    # Recovery copies (S32-S37).
    w.ev("_opts.set('autosave-seconds', 1)")
    wait_for(lambda: w.ev("_autosaveTimer.interval") == 10000)
    out["autosave-interval-at-1s"] = w.ev("_autosaveTimer.interval")
    w.ev("_opts.set('autosave-seconds', 60)")
    w.enter_edit()
    w.move(3, 0.05)
    w.ev("_buttonMap.autosaveNow()")
    out["copy-written"] = RECOVERY.is_file()
    w.ev("_ed().undo()")
    wait_for(lambda: not w.ev("_buttonMap.isDirty()"))
    w.ev("_buttonMap.autosaveNow()")
    out["copy-gone-when-undone"] = not RECOVERY.is_file()
    w.move(3, 0.05)
    crash_fx = w.chip_fx(3)
    w.ev("_buttonMap.autosaveNow()")
    left = RECOVERY.read_text(encoding="utf-8")
    w.leave_edit()
    out["copy-gone-after-cancel"] = not RECOVERY.is_file()
    # As if the program had closed mid-edit: the copy is still there.
    RECOVERY.write_text(left, encoding="utf-8")
    w.ev("_buttonMap.enterEdit()")
    wait_for(lambda: w.opened("_recoverGate"))
    out["offer"] = [w.opened("_recoverGate"), w.ev("_recoverGate.titleText"),
                    w.ev("_buttonMap.editing")]
    w.press("_recoverGate", "Not now")
    wait_for(lambda: not w.opened("_recoverGate"))
    out["not-now"] = [w.ev("_buttonMap.editing"), RECOVERY.is_file()]
    w.ev("_buttonMap.enterEdit()")
    out["offered-again"] = bool(wait_for(lambda: w.opened("_recoverGate")))
    w.press("_recoverGate", "Restore")
    wait_for(lambda: w.ev("_buttonMap.editing") and w.chip_fx(3) == crash_fx)
    out["restore"] = {
        "editing": w.ev("_buttonMap.editing"),
        "edits-back": w.chip_fx(3) == crash_fx and crash_fx is not None,
        "dirty": w.ev("_buttonMap.isDirty()"),
        "file-untouched": file_fx(3) != crash_fx,
    }
    w.leave_edit()
    out["copy-gone-after-restore-cancel"] = not RECOVERY.is_file()
    RECOVERY.write_text(left, encoding="utf-8")
    w.ev("_buttonMap.enterEdit()")
    wait_for(lambda: w.opened("_recoverGate"))
    w.press("_recoverGate", "Discard")
    wait_for(lambda: not RECOVERY.is_file())
    out["discard"] = [w.ev("_buttonMap.editing"), RECOVERY.is_file(),
                      file_fx(3) != crash_fx]
    # A copy the same as the saved map goes without asking (S37).
    w.ev("_hw.saveRecovery(_buttonMap.targetName, JSON.stringify({image:"
         " _buttonMap.liveImage,"
         " photo: _buttonMap.livePhoto || _buttonMap.photoFromDoc(null),"
         " nodes: _buttonMap.liveNodes}))")
    out["same-copy-written"] = RECOVERY.is_file()
    out["same-copy-offered"] = w.ev("_buttonMap.offerRecovery()")
    out["same-copy-removed"] = not RECOVERY.is_file()
    # An open offer is put off when another device shows (S35).
    RECOVERY.write_text(left, encoding="utf-8")
    w.ev("_buttonMap.offerRecovery()")
    wait_for(lambda: w.opened("_recoverGate"))
    w.ev("_buttonMap.openForDevice('Third Stick', '', " + json.dumps(THIRD_GUID) + ")")
    wait_for(lambda: w.ev("_buttonMap.targetName") == "Third Stick")
    wait_for(lambda: not w.opened("_recoverGate"))
    out["switch-puts-off"] = {
        "offer-open": w.opened("_recoverGate"),
        "copy-kept": RECOVERY.is_file(),
        "editing": w.ev("_buttonMap.editing"),
    }

    # A guide changed in Edit on a device with no module file (GL-175).
    third_file = hp.module_json_path("Third Stick", THIRD_GUID)
    out["third-file-at-start"] = third_file.is_file()
    w.enter_edit()
    w.ev("(function() { var e = _ed(); e.rulerGuidesX = [0.5];"
         " e.rulerGuidesEdited(); return true })()")
    out["third-file-mid-edit"] = third_file.is_file()
    w.leave_edit()
    out["third-file-after-cancel"] = third_file.is_file()

    # Back to the stick; closing with unsaved edits asks once (S28).
    call(w.root, "openButtonMapForCard", CARD)
    wait_for(lambda: w.ev("_buttonMap.targetName") == NAME)
    RECOVERY.unlink(missing_ok=True)
    w.enter_edit()
    w.move(1, 0.05)
    kept = MAP_FILE.read_text(encoding="utf-8")
    w.ev("_buttonMap.close()")
    asked = bool(wait_for(lambda: w.opened("_saveGate")))
    out["close-asks"] = [asked, w.ev("_buttonMap.leaveKind"),
                         w.ev("_buttonMap.visible")]
    w.press("_saveGate", "Discard")
    win = w.win
    wait_for(lambda: not shown(win))
    out["close-discard"] = {
        "closed": not shown(win),
        "file-kept": MAP_FILE.read_text(encoding="utf-8") == kept,
    }


# +-------------------------------------------------------------------------
# | The module file changed elsewhere while the map is open; Delete Device


def part_outside(app: joystick_gremlin.JoystickGremlinApp, out: dict) -> None:
    from gremlin.ui import history_model

    make_picture(MODULES / SLUG / "photo.png", "#204060")
    setup_photo = make_picture(_HOME / "pictures" / "setup photo.jpg", "#30a030")
    w = open_map(app)

    # A saved edit, then History Restore of the version before it, outside
    # Edit: the map shows the file as it is now (07 Q6, GL-071).
    w.enter_edit()
    w.move(1, 0.1)
    w.ev("_buttonMap.saveEdit(false)")
    w.leave_edit()
    history_quiet()
    entry = next(
        e for e in history.entries()
        if (e.get("subject") or {}).get("fileName") == MAP_FILE.name
    )
    done = history_model.restore(entry["id"], "before")
    restored_fx = file_fx(1)
    follows = wait_for(lambda: w.chip_fx(1) == restored_fx, 5.0)
    out["history-restore"] = {
        "ok": done.get("ok"),
        "file-restored": restored_fx == START_NODES[0]["chipFx"],
        "shown-follows": bool(follows),
        "shown": w.chip_fx(1),
        "file": restored_fx,
    }

    # Module Setup's photo while editing, then Save (07 Q6, GL-071).
    w.enter_edit()
    w.move(2, 0.05)
    setup = hp.HardwareProfile()
    setup.setDeviceGuid(GUID)
    setup_ref = setup.keepPhoto(
        NAME, QtCore.QUrl.fromLocalFile(str(setup_photo)).toString())
    # Module Setup's photo reaches the file with its Save (03 Q2, 07 Q5),
    # as ModuleListModel's save names it.
    from gremlin.modules import store

    store.update(
        NAME, GUID, lambda doc: doc.__setitem__("image", setup_ref), "Module Setup")
    out["setup-photo-written"] = read_doc(MAP_FILE).get("image") == setup_ref
    w.ev("_buttonMap.saveEdit(true)")
    wait_for(lambda: w.opened("_saveGate"))
    out["setup-photo-save"] = {
        "file-image": read_doc(MAP_FILE).get("image"),
        "setup-image": setup_ref,
        "said": w.ev("_saveGate.messageText"),
    }
    w.ok_if_open("_saveGate")
    w.leave_edit()

    # A Device Pack import onto this stick while editing, then Save.
    w.enter_edit()
    w.move(3, 0.05)
    packer = hp.HardwareProfile()
    pack = _HOME / "packs" / "other.zip"
    pack.parent.mkdir(parents=True, exist_ok=True)
    made = json.loads(packer.exportPack(
        "Other Stick", QtCore.QUrl.fromLocalFile(str(pack)).toString(), ""))
    imported = json.loads(packer.importPack(
        QtCore.QUrl.fromLocalFile(str(pack)).toString(), NAME, ""))
    pack_ids = hw_ids(read_doc(MAP_FILE).get("nodes"))
    out["pack-import"] = {
        "made": made.get("ok"), "imported": imported.get("ok"),
        "error": imported.get("error") or made.get("error"),
        "file-ids": pack_ids,
    }
    w.ev("_buttonMap.saveEdit(true)")
    wait_for(lambda: w.opened("_saveGate"))
    out["pack-save"] = {
        "file-ids": hw_ids(read_doc(MAP_FILE).get("nodes")),
        "pack-ids": pack_ids,
        "said": w.ev("_saveGate.messageText"),
    }
    w.ok_if_open("_saveGate")
    w.leave_edit()

    # Delete Device while its map is being edited (S13, 07 Q7, GL-176).
    w.enter_edit()
    w.move(1, 0.05)
    win = w.win
    result = expression(
        w.root,
        "_moduleModel.deleteDevice(" + json.dumps(NAME) + ", "
        + json.dumps(GUID) + ", false)",
    ).evaluate()
    deleted = json.loads(result[0] if isinstance(result, tuple) else result)
    out["delete-ok"] = [deleted.get("ok"), MAP_FILE.is_file()]
    call(w.root, "closeDeletedDevice", CARD)
    wait_for(lambda: not shown(win) or w.opened("_saveGate"))
    out["delete-mid-edit"] = {
        "closed": not shown(win),
        "asked": shown(win) and w.opened("_saveGate"),
        "file": MAP_FILE.is_file(),
    }


# +-------------------------------------------------------------------------
# | Other windows: Module Setup's photo, History filters, quit and restart


class DriveError(RuntimeError):
    """The smoke could not do a step as the user does: not a program result."""


def ev_in(obj: QtCore.QObject, code: str) -> object:
    """code (JavaScript) in obj's own QML scope, as its handlers run it."""
    expr = expression(obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise DriveError(f"{code[:80]}: {expr.error().toString()}")
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def press_in(obj: QtCore.QObject, dialog: str, label: str) -> None:
    """Clicks the button labelled label in dialog (in obj's scope)."""
    code = _PRESS.replace("DLG", dialog).replace("LABEL", json.dumps(label))
    if not ev_in(obj, code):
        raise DriveError(f"no {label!r} button in {dialog}")


def main_root(app: joystick_gremlin.JoystickGremlinApp) -> QtCore.QObject:
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    if not isinstance(root, QtCore.QObject):
        raise DriveError("the main window did not open")
    return root


def top_window(title: str) -> QtGui.QWindow | None:
    """The visible top-level window whose title starts with title."""
    for w in QtGui.QGuiApplication.topLevelWindows():
        if w.isVisible() and w.title().startswith(title):
            return w
    return None


def walk(item: QtCore.QObject) -> list[QtCore.QObject]:
    """item and every Quick item under it."""
    found = [item]
    for child in getattr(item, "childItems", lambda: [])():
        found += walk(child)
    return found


CARD_JS = f"_moduleModel.cardMap({json.dumps(SLUG)})"


def part_setup(app: joystick_gremlin.JoystickGremlinApp, out: dict) -> None:
    """Module Setup: Import Image, then Cancel and Discard (03 Q2, GL-078)."""
    make_picture(MODULES / SLUG / "photo.png", "#204060")
    chosen = make_picture(_HOME / "pictures" / "setup photo.jpg", "#30a030")
    image0 = read_doc(MAP_FILE).get("image")
    root = main_root(app)
    ev_in(root, f"openConfigureModule('source', {CARD_JS})")
    win = wait_for(lambda: top_window("Input Module Setup"))
    if not isinstance(win, QtCore.QObject):
        raise DriveError("Module Setup did not open")
    # Import Image... and a picture picked in the file dialog.
    ev_in(win, "_imageDialog.selectedFile = "
          + json.dumps(QtCore.QUrl.fromLocalFile(str(chosen)).toString())
          + "; _imageDialog.accepted(); true")
    if not wait_for(lambda: "photo.jpg" in str(ev_in(win, "_win.photoUrl"))
                    and ev_in(win, "claimDirty")):
        raise DriveError("Import Image did not show the picture")
    out["setup-imported"] = {
        "file-image": read_doc(MAP_FILE).get("image"),
        "start-image": image0,
    }
    # The window's Cancel button, then Discard in its question.
    content = cast(QtCore.QObject, win.property("contentItem"))
    cancel = next(
        (it for it in walk(content)
         if it.property("text") == "Cancel" and it.property("visible")),
        None,
    )
    if cancel is None:
        raise DriveError("no Cancel button in Module Setup")
    ev_in(cancel, "clicked()")
    if not wait_for(lambda: ev_in(win, "_saveGate.opened")):
        raise DriveError("Cancel with an imported picture did not ask")
    press_in(win, "_saveGate", "Discard")
    if not wait_for(lambda: not shown(win)):
        raise DriveError("Discard did not close Module Setup")
    out["setup-cancel"] = {
        "file-image": read_doc(MAP_FILE).get("image"),
        "start-image": image0,
        "old-photo": (MODULES / SLUG / "photo.png").is_file(),
        "new-photo": (MODULES / SLUG / "photo.jpg").is_file(),
    }
    # Opened again: the picture it shows.
    wait_for(lambda: not ev_in(root, "configureWin"))
    ev_in(root, f"openConfigureModule('source', {CARD_JS})")
    again = wait_for(lambda: top_window("Input Module Setup"))
    if not isinstance(again, QtCore.QObject):
        raise DriveError("Module Setup did not open again")
    url = str(ev_in(again, "_win.photoUrl")).split("?")[0]
    out["setup-reopened-photo"] = url.rsplit("/", 1)[-1]


def history_filter(open_it: Callable[[], object]) -> dict:
    """The filter of the History window open_it opens (closed again after)."""
    old = top_window("History")
    if old is not None:
        old.close()
        wait_for(lambda: top_window("History") is None)
    open_it()
    win = wait_for(lambda: top_window("History"))
    if not isinstance(win, QtGui.QWindow):
        raise DriveError("History did not open")
    text = str(win.property("filter") or "")
    win.close()
    wait_for(lambda: top_window("History") is None)
    return json.loads(text) if text else {}


def part_history(app: joystick_gremlin.JoystickGremlinApp, out: dict) -> None:
    """History as the Button Map's File menu and a Configuration row open it
    (08 Q15, Q16; GL-188, GL-194)."""
    root = main_root(app)
    out["map-file"] = MAP_FILE.name

    # Button Map: File > History.
    w = open_map(app)
    def file_history() -> None:
        if not w.ev(
            "(function() { for (var i = 0; i < _fileMenu.count; i++) {"
            " var it = _fileMenu.itemAt(i);"
            " if (it && it.text === 'History' && it.enabled)"
            " { it.triggered(); return true } } return false })()"
        ):
            raise DriveError("no History item in the Button Map's File menu")

    out["button-map-filter"] = history_filter(file_history)

    # A Configuration row's History, with a saved profile open (stick
    # button 1 has an action, so the page lists it).
    from gremlin.plugin_manager import PluginManager
    from gremlin.types import InputType
    from gremlin.ui.binding_catalog import BindingCatalogModel

    backend = app.backend
    saved = _HOME / "profiles" / "open profile.xml"
    saved.parent.mkdir(parents=True, exist_ok=True)
    # Made in the open profile (actions live in its library), saved, opened.
    item = backend.profile.get_input_item(
        dill.GUID(fake.devices[0].device_guid).uuid, InputType.JoystickButton, 1,
        "Default", create_if_missing=True,
    )
    if item is None:
        raise DriveError("no input item for stick button 1")
    note = PluginManager().create_instance("Description", InputType.JoystickButton)
    root_action = item.add_item_binding().root_action
    if root_action is None:
        raise DriveError("the new binding has no root action")
    root_action.insert_action(note, "children")
    if not backend.saveProfile(QtCore.QUrl.fromLocalFile(str(saved)).toString()):
        raise DriveError("the profile was not saved")
    backend.loadProfile(str(saved))
    if not wait_for(lambda: backend.profilePath()
                    and Path(backend.profilePath()).resolve() == saved.resolve()):
        raise DriveError(
            f"the saved profile did not open: {backend._load_problem}"
        )
    out["open-profile"] = backend.profilePath()
    ev_in(root, f"openConfigurationForCard(_moduleModel.cardMap({json.dumps(SLUG)}))")

    def row_button() -> QtCore.QObject | None:
        page = ev_in(root, "catalogPane()")
        if not isinstance(page, QtCore.QObject):
            return None
        catalog = page.findChild(BindingCatalogModel)
        if catalog is None or catalog.rowCount() == 0:
            return None
        content = cast(QtCore.QObject, root.property("contentItem"))
        for it in walk(content):
            if it.objectName() == "catalogHistory" and ev_in(
                it, "(rowKind === 'group' || rowKind === 'unmapped')"
                " && _root.device !== null && deviceIndex >= 0"
            ):
                return it
        return None

    button = wait_for(row_button)
    if not isinstance(button, QtCore.QObject):
        raise DriveError("no Configuration row with a History button")
    out["row-filter"] = history_filter(lambda: ev_in(button, "clicked()"))


def part_quit(app: joystick_gremlin.JoystickGremlinApp, out: dict) -> None:
    """Restart with unsaved changes: Cancel calls it off; Discard quits the
    usual way with the restart still set (01 S81)."""
    root = main_root(app)
    backend = app.backend
    quits: list[bool] = []
    # Qt.quit() ends here: the program's own quit (Qt's) is left out.
    app.engine.quit.disconnect()
    app.engine.quit.connect(lambda: quits.append(bool(backend.restart_on_exit)))
    backend.profile.modes.add_mode("Unsaved")
    if not backend.profileContainsUnsavedChanges:
        raise DriveError("the profile has no unsaved change")
    gate = "_saveBeforeContinueDialog"

    backend.requestRestart()
    if not wait_for(lambda: ev_in(root, f"{gate}.opened")):
        raise DriveError("a restart with unsaved changes did not ask")
    out["restart-asks"] = {
        "title": ev_in(root, f"{gate}.titleText"),
        "restart-set": backend.restart_on_exit,
    }
    press_in(root, gate, "Cancel")
    # Cancel closes the question; its cancelled() handler runs at the close.
    wait_for(lambda: not ev_in(root, f"{gate}.opened")
             and not backend.restart_on_exit)
    out["restart-cancel"] = {
        "restart-set": backend.restart_on_exit,
        "quit": len(quits),
    }

    backend.requestRestart()
    if not wait_for(lambda: ev_in(root, f"{gate}.opened")):
        raise DriveError("the second restart did not ask")
    press_in(root, gate, "Discard")
    wait_for(lambda: quits)
    out["restart-discard"] = {"quit": quits, "restart-set": backend.restart_on_exit}


def main() -> None:
    part = sys.argv[1] if len(sys.argv) > 1 else "flows"
    out: dict = {"part": part}
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    if not joystick_gremlin.running_offscreen():
        out["error"] = "not off-screen"
    else:
        try:
            {
                "flows": part_flows, "outside": part_outside, "setup": part_setup,
                "history": part_history, "quit": part_quit,
            }[part](app, out)
        except Exception as exc:  # noqa: BLE001
            out["error"] = repr(exc)
            out["traceback"] = traceback.format_exc()
    print("RESULT " + json.dumps(out), flush=True)
    # os._exit skips Qt's teardown, which can hang off-screen.
    os._exit(0)


if __name__ == "__main__":
    main()

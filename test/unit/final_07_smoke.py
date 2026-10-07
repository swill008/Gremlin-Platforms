# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final test plan, Button Map (07): starts the program off-screen (stand-in
hardware, a temporary user folder) and drives the Button Map window through
its own functions for the spec statements no other test checks: one window
(S1), the blank page (S2, S96), File → Device (S4), no other device's photo
(S11), Photo menu (S39), pool and filter (S45), Chip only (S47), free leader
ends (S50), Undo steps (S56), Mirror pictures (S59), Fit to Photo Frame
(S60), Reset Layout (S61), drop outside Edit (S63), Follow the Program
(S71), Labels Mode forgotten (S74), export cap (S84), zoom range (S94) and
the Command Palette (S100). Prints one "RESULT {json}" line; a step that
raised is {"error": ...} under its own key. test_final_07.py runs it.

    python test/unit/final_07_smoke.py

Waits poll for what is checked with a generous limit; none sleeps a fixed
time.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

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
from gremlin import clock  # noqa: E402
from gremlin.ui import hardware_profile as hp  # noqa: E402
from vigem import own_pads  # noqa: E402

# A stick with no module file, and one of the program's own Xbox pads (an
# output: never in File → Device, S4).
third = fake_hardware.raw_device(is_virtual=False)
third.device_guid.Data1 += 11
third.name = b"Third Stick"
fake.devices.append(third)
pad = fake_hardware.raw_device(is_virtual=False)
pad.device_guid.Data1 += 23
pad.name = b"Controller (XBOX 360 For Windows)"
fake.devices.append(pad)
_is_own = own_pads.is_own_pad
_PAD_NAME = "Controller (XBOX 360 For Windows)"


def _name_of(dev: object) -> str:
    name = getattr(dev, "name", "") or ""
    return name.decode("utf-8", "replace") if isinstance(name, bytes) else str(name)


own_pads.is_own_pad = lambda dev: (  # type: ignore[assignment]
    _name_of(dev) == _PAD_NAME or _is_own(dev)
)

STICK = next(d for d in fake.devices if bytes(d.name) == b"pJoy Pro")
GUID = str(dill.GUID(STICK.device_guid).uuid)
THIRD_GUID = str(dill.GUID(third.device_guid).uuid)
NAME = "pJoy Pro"
CARD = {"rawName": NAME, "name": NAME, "guid": GUID}
THIRD_CARD = {"rawName": "Third Stick", "name": "Third Stick", "guid": THIRD_GUID}

LIMIT = 15.0
NOT_S = 1.5

MAP_FILE = hp.module_json_path(NAME, GUID)
SLUG = MAP_FILE.stem
MODULES = MAP_FILE.parent


def chip(hw: int, fx: float) -> dict:
    return {
        "kind": "btn", "id": f"b{hw}", "hwId": hw, "label": f"Button {hw}",
        "chipFx": fx, "chipFy": 0.3, "hotFx": fx, "hotFy": 0.5,
    }


START_NODES = [chip(1, 0.20), chip(2, 0.30), chip(3, 0.40)]

# A large photo: 800% of it is past the 16384 pixel cap (S84).
_photo = QtGui.QImage(2400, 2400, QtGui.QImage.Format.Format_RGB32)
_photo.fill(QtGui.QColor("#305070"))
(MODULES / SLUG).mkdir(parents=True, exist_ok=True)
_photo.save(str(MODULES / SLUG / "photo.png"))
MAP_FILE.write_text(json.dumps({
    "kind": "control.hardware", "device": NAME,
    "image": f"{SLUG}/photo.png", "nodes": START_NODES,
}), encoding="utf-8")

PICTURE = _HOME / "pictures" / "drop me.png"
PICTURE.parent.mkdir(parents=True, exist_ok=True)
_small = QtGui.QImage(40, 20, QtGui.QImage.Format.Format_RGB32)
_small.fill(QtGui.QColor("#a05020"))
_small.save(str(PICTURE))

import joystick_gremlin  # noqa: E402


def wait_for(cond: Callable[[], object], limit: float = LIMIT) -> object:
    """Runs the event loop until cond() is true (its value), up to limit."""
    end = clock.monotonic() + limit
    while True:
        value = cond()
        if value or clock.monotonic() > end:
            return value
        QtTest.QTest.qWait(25)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def same(a: object, b: object) -> bool:
    return (
        a is not None and b is not None
        and shiboken6.isValid(a) and shiboken6.isValid(b)
        and shiboken6.getCppPointer(a)[0] == shiboken6.getCppPointer(b)[0]
    )


def files_under(folder: Path) -> list[str]:
    return sorted(
        str(p.relative_to(folder)).replace("\\", "/")
        for p in folder.rglob("*") if p.is_file()
    )


# Finds a menu row by its text (submenus too) and returns it.
_ROW = (
    "(function(menu, text) { function find(m) { if (!m) return null;"
    " for (var i = 0; i < m.count; i++) { var it = m.itemAt(i);"
    " if (!it) continue; if (it.subMenu) { var f = find(it.subMenu);"
    " if (f) return f; continue }"
    " if (String(it.text) === text) return it } return null }"
    " return find(menu) })"
)


class Window:
    def __init__(self, root: QtCore.QObject) -> None:
        self.root = root

    @property
    def win(self) -> QtCore.QObject:
        return call(self.root, "buttonMapWindow")  # type: ignore[return-value]

    def ev(self, code: str) -> object:
        win = self.win
        context = QtQml.qmlContext(win)
        assert context is not None
        expr = QtQml.QQmlExpression(context, win, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(f"{code[:80]}: {expr.error().toString()}")
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def js(self, code: str) -> object:
        text = self.ev(f"JSON.stringify({code})")
        return json.loads(text) if isinstance(text, str) and text else None

    def node(self, hw: int) -> dict | None:
        nodes = self.js("_ed() ? _ed().nodes : []") or []
        return next((n for n in nodes if n.get("hwId") == hw), None)

    def loaded(self, name: str) -> bool:
        return bool(wait_for(lambda: self.ev(
            f"_buttonMap.targetName === {json.dumps(name)} && _buttonMap.faceLive"
            " && _ed() !== null && _ed().nodes.length > 0")))

    def enter_edit(self) -> bool:
        self.ev("_buttonMap.enterEdit()")
        return bool(wait_for(lambda: self.ev(
            "_buttonMap.editing && _ed() !== null && _ed().seeded"
            " && !_buttonMap._baseWanted")))

    def discard(self) -> None:
        if self.ev("_buttonMap.editing"):
            self.ev("_buttonMap.discardEdit()")
            wait_for(lambda: not self.ev("_buttonMap.editing"))


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    w = Window(root)
    out: dict = {}

    def step(name: str, fn: Callable[[], object]) -> None:
        try:
            out[name] = fn()
        except Exception as error:
            out[name] = {"error": repr(error), "traceback": traceback.format_exc()}

    # --- S2, S1: the blank page, then devices in the same window ------------
    def blank() -> dict:
        call(root, "openBlankButtonMap")
        wait_for(lambda: w.win is not None)
        win = w.win
        wait_for(lambda: bool(win.property("visible")))
        before = files_under(MODULES)
        hint = next((
            o for o in win.findChildren(QtCore.QObject)
            if o.property("text") == "Choose a device from the File menu."
        ), None)
        shown = bool(hint is not None and hint.property("visible"))
        w.ev("_buttonMap.setGridPref('gridOn', false)")
        w.ev("_buttonMap.setGridPref('gridSize', 16)")
        w.ev("_buttonMap.resetViewNow()")
        wait_for(lambda: files_under(MODULES) != before, NOT_S)
        return {"hint": shown, "files-same": files_under(MODULES) == before}

    step("blank", blank)

    def one_window() -> dict:
        first = w.win
        call(root, "openButtonMapForCard", CARD)
        w.loaded(NAME)
        after_card = w.win
        call(root, "openButtonMapForCard", THIRD_CARD)
        wait_for(lambda: w.ev("_buttonMap.targetName") == "Third Stick")
        after_other = w.win
        call(root, "openBlankButtonMap")
        wait_for(lambda: w.ev("_buttonMap.targetName") == "")
        after_blank = w.win
        return {
            "card": same(first, after_card),
            "other": same(first, after_other),
            "blank": same(first, after_blank),
        }

    step("one-window", one_window)

    # --- S11, S96: a stick with no module file -------------------------------
    def no_file() -> dict:
        call(root, "openButtonMapForCard", CARD)
        w.loaded(NAME)
        wait_for(lambda: str(w.ev("_buttonMap.storedImage")).endswith("photo.png"))
        had = str(w.ev("_buttonMap.storedImage"))
        call(root, "openButtonMapForCard", THIRD_CARD)
        wait_for(lambda: w.ev("_buttonMap.targetName") == "Third Stick"
                 and w.ev("_buttonMap.faceLive"))
        wait_for(lambda: w.ev("_buttonMap.storedImage") == "", NOT_S)
        before = files_under(MODULES)
        w.ev("_buttonMap.setGridPref('gridOn', true)")
        w.ev("_buttonMap.setGridPref('gridSize', 32)")
        w.ev("(function() { var f = _ed() ? _ed().face : null;"
             " if (f && f.zoomAt) f.zoomAt(NaN, NaN, 1.5); _buttonMap.captureView();"
             " _buttonMap.persistUi(); return true })()")
        wait_for(lambda: files_under(MODULES) != before, NOT_S)
        return {
            "first-photo": had.endswith("photo.png"),
            "third-photo": w.ev("_buttonMap.storedImage"),
            "photo-override": w.ev("_buttonMap.photoOverride"),
            "files-same": files_under(MODULES) == before,
        }

    step("no-file", no_file)

    # Back on the stick with a map for the rest.
    call(root, "openButtonMapForCard", CARD)
    w.loaded(NAME)

    # --- S4: File → Device --------------------------------------------------
    def device_menu() -> list:
        return w.js("(function() { var r = []; for (var i = 0; i < _deviceMenu.count;"
                    " i++) { var it = _deviceMenu.itemAt(i);"
                    " if (it && it.text) r.push(String(it.text)) } return r })()") or []

    step("device-menu", device_menu)

    # --- S39, S56: outside Edit ----------------------------------------------
    step("outside-edit", lambda: {
        "photo-menu": w.ev("_photoMenu.enabled"),
        "undo": w.ev(f"{_ROW}(_editMenu, 'Undo').enabled"),
        "redo": w.ev(f"{_ROW}(_editMenu, 'Redo').enabled"),
        "hist-cap": w.ev("_ed().histCap"),
    })

    w.enter_edit()
    step("inside-edit", lambda: {"photo-menu": w.ev("_photoMenu.enabled")})

    # --- S45: the pool -------------------------------------------------------
    def pool() -> dict:
        w.ev("_buttonMap.poolFilter = ''; _buttonMap.refreshReservoir()")
        rows = w.js("(_buttonMap.resItems || []).map(function(r) {"
                    " return r.kind + ':' + r.hwId })") or []
        w.ev("_buttonMap.poolFilter = '17'; _buttonMap.refreshReservoir()")
        filtered = w.js("(_buttonMap.resItems || []).map(function(r) {"
                        " return r.kind + ':' + r.hwId })") or []
        w.ev("_buttonMap.poolFilter = ''; _buttonMap.refreshReservoir()")
        return {
            "placed-left-out": not any(k in rows for k in ("btn:1", "btn:2", "btn:3")),
            "has-17": "btn:17" in rows,
            "filtered": filtered,
        }

    step("pool", pool)

    # --- S47: Chip only ------------------------------------------------------
    def chip_only() -> dict:
        def drop(hw: int) -> dict | None:
            w.ev(f"_buttonMap.poolKind = 'btn'; _buttonMap.poolHw = {hw};"
                 " _buttonMap.dropPool(_mapHost.width * 0.5, _mapHost.height * 0.45)")
            wait_for(lambda: w.node(hw) is not None)
            return w.node(hw)

        w.ev("_opts.set('chip-only', true)")
        on = drop(10) or {}
        w.ev("_opts.set('chip-only', false)")
        off = drop(11) or {}
        return {
            "on": [on.get("leaders"), on.get("hotHidden")],
            "off": [off.get("leaders"), bool(off.get("hotHidden"))],
        }

    step("chip-only", chip_only)

    # --- S50: a leader end aimed at a removed chip ---------------------------
    def free_end() -> dict:
        w.ev("(function() { var e = _ed(); e.addDrawFree('line', e.fxToX(0.6),"
             " e.fyToY(0.6), e.fxToX(0.8), e.fyToY(0.8)); return true })()")
        line_id = w.ev("_ed().selectedId")
        w.ev(f"(function() {{ var e = _ed(); var n = e.nodeAt({json.dumps(line_id)});"
             " n.from = {type: 'chip', id: 'b2', pin: 'right'}; e.bump();"
             " return true })()")
        at = w.js(f"(function() {{ var e = _ed();"
                  f" var n = e.nodeAt({json.dumps(line_id)});"
                  " var p = e.endPt(n.from); return [e.xToFx(p.x), e.yToFy(p.y)] })()")
        w.ev("_ed().setSelection(['b2']); _buttonMap.deleteOrBreak()")
        end = w.js(f"_ed().nodeAt({json.dumps(line_id)}).from") or {}
        return {
            "type": end.get("type"),
            "kept-place": bool(at) and abs(end.get("fx", -1) - at[0]) < 1e-6
            and abs(end.get("fy", -1) - at[1]) < 1e-6,
            "chip-gone": w.node(2) is None,
        }

    step("free-end", free_end)

    # --- S59: Mirror Layout and Mirror pictures -------------------------------
    def mirror() -> dict:
        url = QtCore.QUrl.fromLocalFile(str(PICTURE)).toString()
        w.ev(f"_ed().addOverlay('pictures/drop me.png', {json.dumps(url)})")
        pic = w.ev("_ed().selectedId")
        fx0 = w.node(1)["chipFx"]  # type: ignore[index]

        def flip() -> object:
            return w.ev(f"!!_ed().nodeAt({json.dumps(pic)}).flipH")

        w.ev("_opts.set('mirror-pictures', false); _buttonMap.mirrorNow()")
        plain = [flip(), w.node(1)["chipFx"] != fx0]  # type: ignore[index]
        w.ev("_ed().undo()")
        back = abs(w.node(1)["chipFx"] - fx0) < 1e-9  # type: ignore[index]
        w.ev("_opts.set('mirror-pictures', true); _buttonMap.mirrorNow()")
        with_pictures = flip()
        w.ev("_ed().undo(); _opts.set('mirror-pictures', false)")
        return {"plain": plain, "undo": back, "pictures": with_pictures,
                "undo-pictures": flip()}

    step("mirror", mirror)

    # --- S60: Fit to Photo Frame --------------------------------------------
    def fit() -> dict:
        n0 = w.node(1) or {}
        w.ev("_buttonMap.fitToPhotoFrame()")
        n1 = w.node(1) or {}
        w.ev("_buttonMap.fitToPhotoFrame()")
        n2 = w.node(1) or {}
        w.ev("_ed().undo()")
        wait_for(lambda: not w.ev("_buttonMap.fittedThisEdit"), NOT_S)
        n3 = w.node(1) or {}
        return {
            "chip": [n0.get("chipFx"), n1.get("chipFx")],
            "hot": [n0.get("hotFx"), n1.get("hotFx")],
            "once": n2.get("chipFx") == n1.get("chipFx"),
            "undo": n3.get("chipFx") == n0.get("chipFx"),
            "again": not w.ev("_buttonMap.fittedThisEdit"),
        }

    step("fit", fit)

    # --- S61: Reset Layout ---------------------------------------------------
    def reset() -> dict:
        count = w.ev("_ed().nodes.length")
        w.ev(f"{_ROW}(_fileMenu, 'Reset Layout').triggered()")
        asked = bool(wait_for(lambda: w.ev("_resetDlg.opened")))
        unchanged = w.ev("_ed().nodes.length") == count
        w.ev("_resetDlg.close()")
        wait_for(lambda: not w.ev("_resetDlg.opened"))
        w.ev("_buttonMap.resetLayout()")
        cleared = w.ev("_ed().nodes.length")
        w.ev("_ed().undo()")
        return {"asked": asked, "unchanged": unchanged, "cleared": cleared,
                "undo": w.ev("_ed().nodes.length") == count}

    step("reset", reset)

    # --- S56: Undo steps ----------------------------------------------------
    def undo_steps() -> dict:
        w.ev("_opts.set('undo-steps', 3)")
        cap = w.ev("_ed().histCap")
        for i in range(6):
            w.ev(f"(function() {{ var e = _ed(); e.nodes[0].chipFx = {0.1 + 0.01 * i};"
                 " e.bump(); return true })()")
        undos = 0
        while w.ev("_ed().canUndo") and undos < 20:
            w.ev("_ed().undo()")
            undos += 1
        w.ev("_opts.set('undo-steps', 80)")
        return {"cap": cap, "undos": undos, "cap-back": w.ev("_ed().histCap")}

    step("undo-steps", undo_steps)

    # --- S100: Command Palette -----------------------------------------------
    def palette() -> list:
        w.ev("_palette.open()")
        wait_for(lambda: w.ev("_palette.opened"))
        texts = w.js("Commands.search('', ['buttonmap']).map(function(c) {"
                     " return c.text })") or []
        w.ev("_palette.close()")
        wait_for(lambda: not w.ev("_palette.opened"))
        return texts

    step("palette", palette)

    # --- S84: export cap; S94: zoom range ------------------------------------
    def export_cap() -> dict:
        wait_for(lambda: w.ev("_ed().photoNatural().w > 0"))
        w.ev("_buttonMap.setPrint('scale', 100)")
        at_100 = w.js("_buttonMap.exportPixels()") or {}
        w.ev("_buttonMap.setPrint('scale', 800)")
        at_800 = w.js("_buttonMap.exportPixels()") or {}
        w.ev("_buttonMap.setPrint('scale', 100)")
        return {"100": at_100, "800": at_800}

    step("export-cap", export_cap)

    def zoom() -> dict:
        w.ev("_ed().face.zoomAt(NaN, NaN, 1000)")
        most = w.ev("_ed().face.viewPct")
        w.ev("_ed().face.zoomAt(NaN, NaN, 0.00001)")
        least = w.ev("_ed().face.viewPct")
        w.ev("_ed().face.resetView()")
        hints = w.js(
            f"[{_ROW}(_viewMenu, 'Zoom to Fit Page').hint,"
            f" {_ROW}(_viewMenu, 'Zoom to Selection').hint,"
            f" {_ROW}(_viewMenu, 'Reset View (View 100%)').hint]"
        )
        return {"most": round(float(most), 4), "least": round(float(least), 4),
                "hints": hints}

    step("zoom", zoom)

    w.discard()

    # --- S63: a picture dropped outside Edit ---------------------------------
    def drop_outside() -> dict:
        before = files_under(MODULES)
        url = QtCore.QUrl.fromLocalFile(str(PICTURE)).toString()
        took = w.ev(f"_buttonMap.dropPictures([{json.dumps(url)}], 20, 20, _mapHost)")
        return {
            "took": took,
            "said": w.ev("_ed().findMsg"),
            "files-same": files_under(MODULES) == before,
        }

    step("drop-outside", drop_outside)

    # --- S71: Follow the Program; S74: forgotten when the window closes ------
    def follow() -> dict:
        w.ev("_buttonMap.labelMode = ''")
        w.ev("uiState.setCurrentMode('Combat')")
        followed = w.ev("_buttonMap.labelModeNow")
        w.ev("uiState.setCurrentMode('Default')")
        back = w.ev("_buttonMap.labelModeNow")
        w.ev("_buttonMap.labelMode = 'Chosen'")
        chosen = w.ev("_buttonMap.labelModeNow")
        w.ev("uiState.setCurrentMode('Combat')")
        kept = w.ev("_buttonMap.labelModeNow")
        w.ev("uiState.setCurrentMode('Default')")
        return {"follows": [followed, back], "chosen": [chosen, kept]}

    step("follow", follow)

    def forgotten() -> dict:
        w.ev("_buttonMap.labelMode = 'Default'")
        old = w.win
        w.ev("_buttonMap.close()")
        wait_for(lambda: not shiboken6.isValid(old) or not old.property("visible"))
        call(root, "openButtonMapForCard", CARD)
        w.loaded(NAME)
        return {"label-mode": w.ev("_buttonMap.labelMode")}

    step("forgotten", forgotten)

    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("RESULT " + json.dumps(
            {"error": repr(error), "traceback": traceback.format_exc()}), flush=True)
        os._exit(1)

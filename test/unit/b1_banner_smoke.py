# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's view-only banner (D-FIXLIST-B1 item 1) in the real
window: starts the program off-screen (stand-in hardware, a temporary user
folder), opens a stick's Device Mapping Editor and clicks the banner's Edit Mapping
link, then Cancel, Save and a window with no device. Prints one
"RESULT {json}" line. test_b1_banner.py runs it.

    python test/unit/b1_banner_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Never the user's own folder: the pytest side gives a temporary one.
_HOME = Path(os.environ.get("USERPROFILE", "")).resolve()
_USERS = Path(os.environ.get("SystemDrive", "C:") + "/Users")
_REAL_HOME = (_USERS / os.environ.get("USERNAME", "")).resolve()
if (
    not os.environ.get("USERPROFILE")
    or _HOME == _REAL_HOME
    or (os.environ.get("QT_QPA_PLATFORM") != "offscreen")
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

from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
from gremlin import clock  # noqa: E402
from gremlin.modules import store  # noqa: E402

STICK = next(d for d in fake.devices if bytes(d.name) == b"pJoy Pro")
GUID = str(dill.GUID(STICK.device_guid).uuid)
NAME = "pJoy Pro"
CARD = {"rawName": NAME, "name": NAME, "guid": GUID}
LIMIT = 15.0

DEVICE = store.ensure_device_dir(NAME, GUID)
store.module_file_in(DEVICE).write_text(
    json.dumps(
        {
            "kind": "control.hardware",
            "device": NAME,
            "nodes": [
                {
                    "kind": "btn",
                    "id": "b1",
                    "hwId": 1,
                    "label": "Button 1",
                    "chipFx": 0.2,
                    "chipFy": 0.3,
                    "hotFx": 0.2,
                    "hotFy": 0.5,
                }
            ],
        }
    ),
    encoding="utf-8",
)

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
        obj,
        name,
        QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


# The banner's state: shown, its words, its place under the menu bar, its
# height beside the Background banner's, and any button in it.
_STATE = (
    "(function() { var b = _viewOnlyBanner, l = _viewOnlyEdit;"
    " var words = []; var buttons = [];"
    " function walk(it) { for (var i = 0; i < it.children.length; i++) {"
    "  var c = it.children[i]; if (c.text !== undefined && c.visible)"
    "   words.push(String(c.text));"
    "  if (c.clicked !== undefined && c.text !== undefined)"
    "   buttons.push(String(c.text));"
    "  walk(c) } }"
    " walk(b);"
    " var mb = _menuBar.mapToItem(null, 0, 0);"
    " var bp = b.mapToItem(null, 0, 0);"
    " return { visible: b.visible, text: words.join(''), linkText: String(l.text),"
    "  linkEnabled: l.enabled, gap: bp.y - (mb.y + _menuBar.height),"
    "  height: b.height, bgHeight: _bgBanner.height, buttons: buttons,"
    "  editing: _editorWin.editing } })()"
)


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_for(lambda: (app.engine.rootObjects() or [None])[0])
    assert isinstance(root, QtCore.QObject)
    out: dict = {}

    def win() -> QtGui.QWindow:
        return call(root, "deviceMappingEditorWindow")  # type: ignore[return-value]

    def ev(code: str) -> object:
        w = win()
        context = QtQml.qmlContext(w)
        assert context is not None
        expr = QtQml.QQmlExpression(context, w, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(f"{code[:80]}: {expr.error().toString()}")
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def state() -> dict:
        return json.loads(str(ev(f"JSON.stringify({_STATE})")))

    def click_link() -> None:
        # A real mouse click on the link's middle, once the window has laid
        # out again (the banner just came back and pushed the map down).
        QtTest.QTest.qWait(300)
        p = ev(
            "(function() { var p = _viewOnlyEdit.mapToItem(null,"
            " _viewOnlyEdit.width / 2, _viewOnlyEdit.height / 2);"
            " return [p.x, p.y] })()"
        )
        x, y = (int(v) for v in p)  # type: ignore[union-attr]
        QtTest.QTest.mouseClick(
            win(),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            QtCore.QPoint(x, y),
        )
        QtTest.QTest.qWait(150)

    def ready() -> bool:
        return bool(
            wait_for(
                lambda: ev(
                    "_editorWin.editing && _ed() !== null && _ed().seeded"
                    " && !_editorWin._baseWanted"
                )
            )
        )

    def step(name: str, fn: Callable[[], object]) -> None:
        try:
            out[name] = fn()
        except Exception as error:
            out[name] = {"error": repr(error), "traceback": traceback.format_exc()}

    call(root, "openDeviceMappingEditorForCard", CARD)
    wait_for(lambda: win() is not None)
    win().setProperty("width", 1200)
    win().setProperty("height", 800)
    wait_for(
        lambda: ev(
            f"_editorWin.targetName === {json.dumps(NAME)} && _editorWin.faceLive"
            " && _ed() !== null"
        )
    )
    QtTest.QTest.qWait(300)

    step("live", state)

    def via_link() -> dict:
        click_link()
        res = {"started": ready()}
        res.update(state())
        return res

    step("clicked", via_link)

    def after_cancel() -> dict:
        ev("_editorWin.cancelEdit()")
        wait_for(lambda: not ev("_editorWin.editing"))
        return state()

    step("cancelled", after_cancel)

    def after_save() -> dict:
        # Save keeps the edit open (the banner stays hidden); leaving it
        # brings the banner back.
        click_link()
        res = {"started": ready()}
        ev("_editorWin.saveEdit()")
        QtTest.QTest.qWait(200)
        res["saved"] = bool(ev("_editorWin.saveOk"))
        res["whileEditing"] = state()
        ev("_editorWin.cancelEdit()")
        wait_for(lambda: not ev("_editorWin.editing"))
        res.update(state())
        return res

    step("saved", after_save)

    def reopened() -> dict:
        # The window closed mid-edit (nothing changed) and opened again:
        # the banner shows.
        click_link()
        res = {"started": ready()}
        win().close()
        wait_for(lambda: win() is None)
        res["closed"] = win() is None
        call(root, "openDeviceMappingEditorForCard", CARD)
        wait_for(
            lambda: (
                win() is not None
                and ev(
                    f"_editorWin.targetName === {json.dumps(NAME)} && _ed() !== null"
                )
            )
        )
        QtTest.QTest.qWait(300)
        res.update(state())
        return res

    step("reopened", reopened)

    def no_device() -> dict:
        # No device: the link is greyed and a click (or the call) is
        # refused, as File › Edit Mapping is.
        ev('_editorWin.targetName = ""')
        QtTest.QTest.qWait(100)
        click_link()
        ev("_editorWin.enterEdit()")
        QtTest.QTest.qWait(100)
        res = state()
        res["canEnterEdit"] = bool(ev("_editorWin.canEnterEdit"))
        return res

    step("nodevice", no_device)

    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()

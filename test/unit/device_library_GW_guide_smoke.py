# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Device
Library through Tools, then uses its Help menu and F1 and prints as JSON what
the guide window showed. test_device_library_GW_guide.py runs it in its own
process with a fresh user folder.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

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

import joystick_gremlin  # noqa: E402
from gremlin import clock  # noqa: E402

messages: list[str] = []


def _capture(mode, context, text: str) -> None:  # noqa: ANN001
    messages.append(text)


QtCore.qInstallMessageHandler(_capture)


def wait_until(cond, limit_ms: int = 10000) -> bool:  # noqa: ANN001
    end = clock.monotonic() + limit_ms / 1000.0
    qapp = QtCore.QCoreApplication.instance()
    while True:
        if cond():
            return True
        if clock.monotonic() > end:
            return False
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        clock.sleep(0.005)


def ev(obj: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(expr.error().toString() + " :: " + code[:200])
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def windows(title: str) -> list:
    return [
        w for w in QtGui.QGuiApplication.topLevelWindows()
        if w.isVisible() and w.title() == title
    ]


_TITLES = (
    "(function(){var o=[];for(var i=0;i<_topics.length;++i)"
    "o.push(_topics[i].title);return o})()"
)
_HELP_ITEMS = (
    "(function(){var ms=_menuBar.menus;for(var i=0;i<ms.length;++i){"
    "if(ms[i].title==='Help'){var o=[];for(var j=0;j<ms[i].count;++j){"
    "var it=ms[i].itemAt(j);"
    "o.push({text:String(it.text||''),hint:String(it.hint||'')})}"
    "return o}}return null})()"
)
_TRIGGER_HELP = (
    "(function(){var ms=_menuBar.menus;for(var i=0;i<ms.length;++i){"
    "if(ms[i].title==='Help'){ms[i].itemAt(0).triggered();return true}}return false})()"
)


def guide_state() -> dict:
    found = windows("Device Library Guide")
    state: dict = {"count": len(found), "titles": []}
    if found:
        state["titles"] = list(ev(found[0], _TITLES) or [])
    return state


def close_guides() -> None:
    for w in windows("Device Library Guide"):
        w.close()
    wait_until(lambda: not windows("Device Library Guide"), 3000)


out: dict = {"errors": []}
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))
ev(win, "Commands.trigger('tools.deviceLibrary')")
out["library_opened"] = wait_until(lambda: bool(windows("Device Library")), 8000)
lib = windows("Device Library")[0]

try:
    out["help_items"] = ev(lib, _HELP_ITEMS)
except RuntimeError as exc:
    out["errors"].append(str(exc))
    out["help_items"] = None

# Help > Device Library Guide.
try:
    out["menu_triggered"] = bool(ev(lib, _TRIGGER_HELP))
except RuntimeError as exc:
    out["errors"].append(str(exc))
    out["menu_triggered"] = False
wait_until(lambda: bool(windows("Device Library Guide")), 4000)
out["menu"] = guide_state()
# Again: the same window comes forward, no second one.
if out["menu_triggered"]:
    ev(lib, _TRIGGER_HELP)
    wait_until(lambda: False, 500)
out["menu_again"] = guide_state()

# F1 in the Device Library window.
close_guides()
lib.requestActivate()
wait_until(lambda: lib.isActive(), 3000)
QtTest.QTest.keyClick(lib, QtCore.Qt.Key.Key_F1)
wait_until(lambda: bool(windows("Device Library Guide")), 4000)
out["f1"] = guide_state()
lib.requestActivate()
wait_until(lambda: lib.isActive(), 3000)
QtTest.QTest.keyClick(lib, QtCore.Qt.Key.Key_F1)
wait_until(lambda: False, 500)
out["f1_again"] = guide_state()

shot = os.environ.get("GW_SHOT")
if shot and windows("Device Library Guide"):
    guide = windows("Device Library Guide")[0]
    wait_until(lambda: False, 800)
    image = guide.grabWindow()
    Path(shot).parent.mkdir(parents=True, exist_ok=True)
    out["shot"] = bool(image.save(shot))

# The program's User Guide still has every topic.
ev(win, "Commands.trigger('help.guide')")
wait_until(lambda: bool(windows("User Guide")), 4000)
user = windows("User Guide")
out["user_guide"] = {
    "count": len(user),
    "titles": list(ev(user[0], _TITLES) or []) if user else [],
}
out["full_count"] = int(ev(user[0], "HelpTopics.topics().length")) if user else 0
out["dl_count"] = (
    int(ev(user[0], "typeof HelpTopics.deviceLibraryTopics === 'function'"
                     " ? HelpTopics.deviceLibraryTopics().length : -1"))
    if user else -1
)
out["qml_errors"] = [
    m for m in messages if "Error" in m or "is not a function" in m
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)

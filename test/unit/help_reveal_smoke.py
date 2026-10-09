# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and drives Help's links
to the program through Style.helpLinks (01 S139, D-01-HELP-LINKS): menus
drop down with the item pulsing and nothing chosen, toolbar and mode-bar
buttons pulse, open: runs only allowed commands. Prints the findings as
JSON. test_help_reveal.py runs it in its own process with a fresh user
folder.
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

from PySide6 import QtCore, QtGui, QtQml  # noqa: E402

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


def titles() -> list[str]:
    return sorted(
        w.title() for w in QtGui.QGuiApplication.topLevelWindows() if w.isVisible()
    )


def call(win: QtCore.QObject, fn: str, link: str) -> object:
    return ev(win, (
        f"Style.helpLinks ? Style.helpLinks.{fn}({json.dumps(link)})"
        " : 'no helpLinks'"
    ))


# JS: whether an item has a pulse on it now.
_PULSING = (
    "function(it){if(!it)return false;var c=it.children;"
    "for(var i=0;i<c.length;++i)if(c[i].objectName==='helpPulse'"
    "&&c[i].visible)return true;return false}"
)

# JS: the menu bar's menu titled t (null if none).
_MENU = (
    "function(t){var b=_root.menuBar;for(var i=0;i<b.count;++i)"
    "if(b.menuAt(i).title===t)return b.menuAt(i);return null}"
)

# JS: the row of menu m whose text is t.
_ROW = (
    "function(m,t){for(var i=0;i<m.count;++i){var r=m.itemAt(i);"
    "if(r&&r.text===t)return r}return null}"
)


def menu_state(win: QtCore.QObject) -> dict:
    return ev(win, (
        f"(function(){{var pulsing={_PULSING};var menu={_MENU};var row={_ROW};"
        "var tools=menu('Tools');var setup=row(tools,'Device Setup');"
        "var cal=row(setup.subMenu,'Calibration');"
        "return {toolsOpen:tools.opened,setupOpen:setup.subMenu.opened,"
        "pulsing:pulsing(cal),current:setup.subMenu.currentIndex>=0"
        "&&setup.subMenu.itemAt(setup.subMenu.currentIndex)===cal}})()"
    ))


def pulsing(win: QtCore.QObject, item_id: str) -> bool:
    return bool(ev(win, f"({_PULSING})({item_id})"))


out: dict = {"errors": []}
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))

try:
    out["bridge"] = bool(ev(win, "!!Style.helpLinks"))
    out["start_titles"] = titles()

    # check(): real paths are fine, unknown ones say why.
    out["check_menu"] = call(win, "check", "show:menu/Tools/Device Setup/Calibration")
    out["check_menu_dots"] = call(
        win, "check", "show:menu/tools/device setup/device library"
    )
    out["check_unknown"] = call(win, "check", "show:menu/File/No Such Thing")
    out["check_toolbar"] = call(win, "check", "show:toolbar/Run")
    out["check_toolbar_tip"] = call(
        win, "check", "show:toolbar/Show or hide the vJoy Viewer"
    )
    out["check_toolbar_bad"] = call(win, "check", "show:toolbar/Nope")
    out["check_modebar"] = call(win, "check", "show:modebar")
    out["check_modebar_btn"] = call(win, "check", "show:modebar/Manage Modes")
    out["check_option_bad"] = call(win, "check", "show:option/No such setting at all")
    out["check_open_allowed"] = call(win, "check", "open:tools.vjoyViewer")
    out["check_open_denied"] = call(win, "check", "open:help.diagnostics")

    # A menu path: Tools and Device Setup drop down, Calibration pulses,
    # nothing is chosen.
    out["reveal_menu"] = call(win, "reveal", "show:menu/Tools/Device Setup/Calibration")
    wait_until(lambda: False, 400)
    out["menu_now"] = menu_state(win)
    out["menu_titles"] = titles()
    wait_until(lambda: False, 2500)
    out["menu_later"] = menu_state(win)
    ev(win, f"({_MENU})('Tools').close()")
    wait_until(lambda: False, 300)

    # Toolbar and mode bar buttons pulse; nothing opens.
    out["reveal_toolbar"] = call(win, "reveal", "show:toolbar/Options")
    out["reveal_modebar"] = call(win, "reveal", "show:modebar/Manage Modes")
    wait_until(lambda: False, 300)
    out["toolbar_pulsing"] = pulsing(win, "_optionsButton")
    out["modebar_pulsing"] = pulsing(win, "_manageModesButton")
    out["after_pulse_titles"] = titles()
    wait_until(lambda: False, 2500)
    out["toolbar_pulse_gone"] = not pulsing(win, "_optionsButton")

    # open: an allowed id opens it; a disallowed one does nothing.
    out["reveal_denied"] = call(win, "reveal", "open:help.diagnostics")
    wait_until(lambda: False, 800)
    out["denied_titles"] = titles()
    out["reveal_allowed"] = call(win, "reveal", "open:tools.vjoyViewer")
    wait_until(lambda: "vJoy Viewer" in titles(), 5000)
    out["allowed_titles"] = titles()

    # An Options setting: found by label without opening Options; reveal
    # opens Options on it.
    labels = ev(win, (
        "typeof _helpOptionLabels === 'undefined' ? []"
        " : _helpOptionLabels.settingLabels()"
    )) or []
    out["option_label"] = labels[0] if labels else ""
    label = "show:option/" + out["option_label"].upper()
    out["check_option"] = call(win, "check", label)
    out["option_titles_before"] = titles()
    out["reveal_option"] = call(win, "reveal", "show:option/" + out["option_label"])
    wait_until(lambda: "Options" in titles(), 5000)
    out["option_titles"] = titles()
except Exception as exc:  # noqa: BLE001
    out["errors"].append(repr(exc))

out["qml_errors"] = [
    m for m in messages
    if any(
        k in m
        for k in ("Error", "is not a function", "is not defined", "TypeError")
    )
    and ("Main.qml" in m or "Pulse.qml" in m)
][:5]
print("RESULT " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)

# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen with a made-up user, runs Help → Save
Diagnostics… from the command list and the Debug tab's button, saves a zip
with the open profile ticked and prints what it found, as JSON.
test_diagnostics_ui.py runs it in its own process and user folder.

    python test/unit/handson_D11_diagnostics_smoke.py <zip path>
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(fake_hardware)  # type: ignore[union-attr]
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtQuick  # noqa: E402

# Registers the Diagnostics QML type (the program imports it at start too).
import gremlin.ui.diagnostics  # noqa: E402, F401
import joystick_gremlin  # noqa: E402

LIMIT_S = 20.0


def wait_until(check, limit: float = LIMIT_S) -> bool:  # noqa: ANN001
    """Runs Qt events until check() is true; False after limit seconds."""
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50
        )
        try:
            if check():
                return True
        except Exception:
            pass
    return False


def window(title: str) -> QtQuick.QQuickWindow | None:
    for w in QtGui.QGuiApplication.topLevelWindows():
        if isinstance(w, QtQuick.QQuickWindow) and w.isVisible() \
                and w.title().startswith(title):
            return w
    return None


def ev(win: QtQuick.QQuickWindow, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    if expr.hasError():
        return "error: " + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def main() -> None:
    dest = Path(sys.argv[1])
    out: dict = {}
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    main_win = app.main_window
    assert wait_until(lambda: main_win.isVisible() or True)

    # Help → Save Diagnostics… is one command in the command list.
    out["command"] = ev(main_win, (
        "(function() { var c = MainCommands.commandList().filter("
        "function(x) { return x.id === 'help.diagnostics' })[0];"
        " if (!c) return null; c.run(); return c.group + ' › ' + c.text })()"
    ))
    out["fromMenu"] = wait_until(lambda: window("Save Diagnostics") is not None)
    win = window("Save Diagnostics")
    if win is not None:
        out["startFolder"] = ev(win, "String(_saveDialog.startFolder())")
        out["desktop"] = ev(win, "_diag.desktopUrl")
        out["box"] = ev(win, "_includeProfile.text")
        out["boxStarts"] = ev(win, "_includeProfile.checked")
        win.close()
        wait_until(lambda: window("Save Diagnostics") is None)

    # The Debug tab's button opens the same window.
    ev(main_win, 'Helpers.createComponent("DialogLiveLog.qml")')
    wait_until(lambda: window("Live Log Reader") is not None)
    log = window("Live Log Reader")
    out["button"] = ev(log, "_saveDiagnostics.text") if log else None
    if log is not None:
        ev(log, "_tabs.currentIndex = 1")
        ev(log, "_saveDiagnostics.clicked()")
    out["fromDebugTab"] = wait_until(lambda: window("Save Diagnostics") is not None)
    win = window("Save Diagnostics")
    if win is not None:
        ev(win, "_includeProfile.checked = true")
        url = QtCore.QUrl.fromLocalFile(str(dest)).toString()
        out["started"] = ev(win, f"_win.saveTo({json.dumps(url)})")
        out["finished"] = wait_until(
            lambda: ev(win, "_diag.busy") is False and bool(ev(win, "_diag.message"))
        )
        out["shown"] = ev(win, "_result.text")
        if dest.is_file():
            with zipfile.ZipFile(dest) as zf:
                out["files"] = sorted(zf.namelist())
        # A failure: a folder that is not there.
        gone = dest.parent / "gone" / "x.zip"
        gone_url = QtCore.QUrl.fromLocalFile(str(gone)).toString()
        ev(win, f"_win.saveTo({json.dumps(gone_url)})")
        wait_until(lambda: "not saved" in str(ev(win, "_result.text")))
        out["failure"] = ev(win, "_result.text")
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

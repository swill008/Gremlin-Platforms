# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run for test_b2_card.py: the real program; Tools › Device
Setup › Export / Import Device and the Home card's Export Device… / Import
Device… routes. Prints RESULT {json}."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator

from smoke_exit import smoke_exit

sys.path.insert(0, ".")
sys.path.insert(0, "test")
import importlib.util

spec = importlib.util.spec_from_file_location("fake_hardware", "test/fake_hardware.py")
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick  # noqa: E402

import joystick_gremlin  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

from gremlin import device_initialization  # noqa: E402
from gremlin.modules import module_file, store  # noqa: E402

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


def pack_window() -> QtQuick.QQuickWindow | None:
    for w in app.topLevelWindows():
        if (
            isinstance(w, QtQuick.QQuickWindow)
            and w.isVisible()
            and (
                w.title().startswith("Device Pack")
                or w.title().startswith("Export / Import Device")
            )
        ):
            return w
    return None


def old_box() -> bool:
    return any(
        d.property("opened")
        for d in win.findChildren(QtCore.QObject, "deviceExportDialog")
    )


stick = next(
    d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
)
guid = str(stick.device_guid)
out["guid"] = guid
module_file.write_json(
    store.module_file_in(store.ensure_device_dir(stick.name, guid)),
    {
        "kind": "control.hardware",
        "device": stick.name,
        "direction": "source",
        "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
        "nodes": [],
    },
)

try:
    out["tools-text"] = ev('Commands.textOf("tools.devicePack")')
    ev('Commands.trigger("tools.devicePack")')
    pw = wait_until(pack_window, "the Export / Import Device window", fail=False)
    out["tools-open"] = pw is not None
    out["tools-mode"] = str(ev("mode", pw)) if pw else ""
    out["has-openFor"] = bool(pw) and bool(ev('typeof openFor === "function"', pw))
    if pw:
        pw.close()
        wait_until(lambda: pack_window() is None, "the window closed", fail=False)

    page = next(
        (i for i in walk(win.contentItem()) if i.objectName() == "homePage"), None
    )
    out["page"] = page is not None
    card = (
        '({rawName: "pJoy Pro", cardName: "pJoy Pro", name: "pJoy Pro",'
        f' guid: "{guid}"}})'
    )
    for tab in ("export", "import"):
        if page is not None:
            ev(f"{tab}Device({card})", page)
        pw = wait_until(pack_window, f"the {tab} window", 5000, fail=False)
        out[f"{tab}-open"] = pw is not None
        out[f"{tab}-mode"] = str(ev("mode", pw)) if pw else ""
        out[f"{tab}-old-box"] = old_box()
        if pw and tab == "export":
            out["export-guid"] = str(ev("exportDeviceGuid()", pw))
        if pw:
            pw.close()
            wait_until(lambda: pack_window() is None, "the window closed", fail=False)
except Exception as e:  # noqa: BLE001
    out["error"] = f"{type(e).__name__}: {e}"

print("RESULT " + json.dumps(out), flush=True)
smoke_exit(0)

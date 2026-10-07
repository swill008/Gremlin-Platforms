# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of the Device Pack window for test_handson_G3_pack_window.py
(08 S106 D-08-PACK-START, 08 S107 D-08-PACK-BG).

"Alpha Stick" (listed first) has a damaged module file; "pJoy Pro" has a good
one with a photo. The window should open on pJoy Pro with Alpha Stick listed
as "(file damaged)"; choosing a device from code shows that device at once;
Export runs in the background (busy note, Export disabled, the window's
timers keep firing) and reports when done. Prints RESULT {json}."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import uuid
from collections.abc import Callable, Iterator

sys.path.insert(0, ".")

spec = importlib.util.spec_from_file_location("fake_hardware", "test/fake_hardware.py")
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

from gremlin import clock, device_initialization, shared_state, util  # noqa: E402
from gremlin.modules import module_file, store  # noqa: E402
from gremlin.profile import DeviceInfo  # noqa: E402
from gremlin.ui import device_pack  # noqa: E402

WAIT_MS = 10000
out: dict = {}


def ev(code: str, target: QtCore.QObject | None = None) -> object:
    host = target or win
    expr = QtQml.QQmlExpression(QtQml.qmlContext(host), host, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


def walk(item: QtQuick.QQuickItem) -> Iterator[QtQuick.QQuickItem]:
    yield item
    for kid in item.childItems():
        yield from walk(kid)


def child(window: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
    for item in walk(window.contentItem()):
        if item.objectName() == name:
            return item
    return None


def wait_for(check: Callable[[], object], ms: int = WAIT_MS) -> bool:
    """Runs the event loop until check() is true, up to ms (bounded)."""
    end = clock.monotonic() + ms / 1000
    while True:
        if check():
            return True
        if clock.monotonic() > end:
            return False
        QtTest.QTest.qWait(20)


stick = next(
    d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
)
name, uid = stick.name, stick.device_guid.uuid
profile = shared_state.current_profile
profile.device_database.devices[uid] = DeviceInfo(uid, name)
alpha = uuid.uuid4()
profile.device_database.devices[alpha] = DeviceInfo(alpha, "Alpha Stick")
modules = util.modules_dir()
modules.mkdir(parents=True, exist_ok=True)
# pJoy Pro: a good module file with a large photo.
photo_dir = store.own_path(name).with_suffix("")
photo_dir.mkdir(parents=True, exist_ok=True)
photo = QtGui.QImage(3000, 2000, QtGui.QImage.Format.Format_RGB32)
photo.fill(QtGui.QColor("#336699"))
photo.save(str(photo_dir / "photo.png"))
module_file.write_json(
    store.own_path(name),
    {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "image": store.picture_ref(photo_dir.name, "photo.png"),
        "claim": {"buttons": [1], "axes": [], "hats": [], "keys": []},
        "nodes": [],
    },
)
# Alpha Stick: its module file can't be read.
row = store.match_known_device("Alpha Stick")
damaged = store.path_for("Alpha Stick", str((row or {}).get("guid") or ""))
damaged.write_text("{ not json", encoding="utf-8")

ev('Helpers.createComponent("DialogDevicePack.qml")')
assert wait_for(
    lambda: any(
        isinstance(w, QtQuick.QQuickWindow)
        and w.title().startswith("Device Pack")
        and w.isVisible()
        for w in app.topLevelWindows()
    )
)
pack_win = next(
    w
    for w in app.topLevelWindows()
    if isinstance(w, QtQuick.QQuickWindow)
    and w.title().startswith("Device Pack")
    and w.isVisible()
)


def enabled(name: str) -> object:
    item = child(pack_win, name)
    return None if item is None else bool(item.isEnabled())


def pv(code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(pack_win), pack_win, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value


wait_for(lambda: pv("exportSize").startswith("about"))

# --- S106: opens on the first device that can be exported ---------------------
out["labels"] = json.loads(
    pv(
        "(function(){var a=[];for(var i=0;i<_deviceModel.count;i++)"
        "a.push(_deviceModel.get(i).label);return JSON.stringify(a)})()"
    )
)
out["open-on"] = pv("exportName")
out["open-shown"] = pv("_exportDevice.currentText")
out["open-status"] = pv("status")
alpha_index = int(pv('_exportDevice.find("Alpha Stick (file damaged)")'))
out["alpha-index"] = alpha_index
# The list's choice set from code: the window shows that device at once.
pv(f"_exportDevice.currentIndex = {alpha_index}")
out["picked-name"] = pv("exportName")
out["picked-status"] = pv("status")
out["picked-export-enabled"] = enabled("packExportButton")
pv(f'_exportDevice.currentIndex = _exportDevice.find("{name}")')
out["back-name"] = pv("exportName")
wait_for(lambda: pv("exportSize").startswith("about"))

# --- S107: the photo loads in the background at preview size -----------------
try:
    image = child(pack_win, "packExportPhoto")
    out["photo-async"] = bool(image.property("asynchronous"))
    size = image.property("sourceSize")
    out["photo-source-size"] = [size.width(), size.height()]
    def ready() -> bool:
        return bool(ev("status === Image.Ready", image))

    out["photo-ready"] = wait_for(ready)
    out["photo-loaded-width"] = image.property("implicitWidth")

    # --- S107: Export in the background --------------------------------------------
    entered = threading.Event()
    release = threading.Event()
    where: list[str] = []
    real_write = device_pack.write_pack


    def slow_write(*args: object, **kwargs: object) -> object:
        where.append(threading.current_thread().name)
        entered.set()
        release.wait(WAIT_MS / 1000)  # bounded
        return real_write(*args, **kwargs)  # type: ignore[arg-type]


    device_pack.write_pack = slow_write
    zip_path = os.path.join(util.userprofile_path(), "g3 pack.zip")
    url = QtCore.QUrl.fromLocalFile(zip_path).toString()
    pv(f'startExport("{url}")')
    out["entered"] = entered.wait(WAIT_MS / 1000)
    ticks: list[int] = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    out["timer-fired"] = wait_for(lambda: len(ticks) >= 3)
    timer.stop()
    busy = child(pack_win, "packExportBusy")
    out["busy-shown"] = bool(busy and busy.isVisible())
    out["busy-text"] = busy.property("text") if busy else ""
    out["export-enabled-while-busy"] = enabled("packExportButton")
    out["status-while-busy"] = pv("status")
    # A second export while it runs is not started.
    pv(f'startExport("{QtCore.QUrl.fromLocalFile(zip_path + "2.zip").toString()}")')
    out["file-before-release"] = os.path.exists(zip_path)
    release.set()
    out["finished"] = wait_for(lambda: str(pv("status")).startswith("Wrote"))
    out["status-after"] = pv("status")
    out["busy-after"] = bool(busy.isVisible())
    out["export-enabled-after"] = enabled("packExportButton")
    out["show-folder-after"] = bool(child(pack_win, "packShowFolder").isVisible())
    out["file-after"] = os.path.exists(zip_path)
    out["second-file"] = os.path.exists(zip_path + "2.zip")
    out["writes"] = len(where)
    out["worker-thread"] = where[0] if where else ""
    device_pack.write_pack = real_write

    # A failure is reported when done, naming the file, folder and reason.
    # A folder already has the pack's name.
    bad = os.path.join(util.userprofile_path(), "taken.zip")
    os.makedirs(bad, exist_ok=True)
    pv(f'startExport("{QtCore.QUrl.fromLocalFile(bad).toString()}")')
    wait_for(lambda: str(pv("status")).startswith("Export failed"))
    out["status-failed"] = pv("status")
    out["export-enabled-after-fail"] = enabled("packExportButton")
except Exception as exc:  # noqa: BLE001 - reported, the checks fail
    out["error"] = repr(exc)
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive

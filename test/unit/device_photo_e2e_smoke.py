# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device's background picture on the real path (07 S157, S127),
off-screen with stand-in hardware. test_device_photo_e2e.py runs it in its
own process with a fresh user folder.

The device's map starts with only a chip. Then, through HardwareProfile's
Save (the Device Mapping Editor's save slot), it gets a background of
- a plain red picture, 800 x 400 pixels, top left of the page;
- a blue filled rectangle, bottom right;
- a green picture, bottom left, hidden (left out, as in an export);
and the chip in the empty top right (foreground: never in the picture).
The program's own maker (context property devicePhotoMaker) and the main
window's DevicePhotoHost make pictures/device-photo.png. Then a Save that
moves only the chip makes nothing new, and a Save with no background left
removes the file. Prints what it found as JSON on a "RESULT " line.

    python test/unit/device_photo_e2e_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtGui, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.modules import store  # noqa: E402
from gremlin.ui import hardware_profile  # noqa: E402

NAME = "pJoy Pro"
GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
FOLDER = store.ensure_device_dir(NAME, GUID)
PICS = FOLDER / "pictures"
PICS.mkdir(exist_ok=True)


def _picture(name: str, w: int, h: int, color: QtGui.QColor) -> None:
    img = QtGui.QImage(w, h, QtGui.QImage.Format.Format_RGB32)
    img.fill(color)
    img.save(str(PICS / name))


_picture("red.png", 800, 400, QtGui.QColor(255, 0, 0))
_picture("green.png", 400, 400, QtGui.QColor(0, 255, 0))

# Page fractions (the page is 16:9). Visible background extent:
# x 0.1 .. 0.8, y 0.1 .. 0.8.
RED = {"kind": "draw", "id": "red", "shape": "image", "plane": "background",
       "src": "pictures/red.png", "fx": 0.1, "fy": 0.1, "fw": 0.4,
       "fh": 0.4 * 16 / 9 / 2, "rot": 0, "opacity": 1, "locked": False,
       "pinned": False, "sockets": [], "fill": "filled"}
BLUE = {"kind": "draw", "id": "blue", "shape": "rect", "plane": "background",
        "fx": 0.6, "fy": 0.6, "fw": 0.2, "fh": 0.2, "rot": 0, "opacity": 1,
        "color": "#0000FF", "border": "#0000FF", "fill": "filled",
        "locked": False, "pinned": False, "sockets": []}
GREEN = {"kind": "draw", "id": "green", "shape": "image", "plane": "background",
         "src": "pictures/green.png", "fx": 0.1, "fy": 0.6, "fw": 0.2,
         "fh": 0.2, "rot": 0, "opacity": 1, "hidden": True, "locked": False,
         "pinned": False, "sockets": [], "fill": "filled"}


def chip(fx: float, fy: float) -> dict:
    return {"kind": "btn", "id": "b1", "label": "Button 1",
            "chipFx": fx, "chipFy": fy}


AREA = (0.1, 0.1, 0.7, 0.7)  # x, y, w, h of the visible background


def _write_start_map() -> None:
    store.module_file_in(FOLDER).write_text(json.dumps({
        "kind": "control.hardware", "device": NAME,
        "nodes": [chip(0.75, 0.15)],
    }), encoding="utf-8")


_write_start_map()
PHOTO = PICS / "device-photo.png"


def wait_for(test: Callable[[], bool], seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if test():
            return True
        QtTest.QTest.qWait(100)
    return test()


def sample(img: QtGui.QImage, fx: float, fy: float) -> list[int]:
    """RGBA at a page point, mapped into the picture's area."""
    ax, ay, aw, ah = AREA
    x = int((fx - ax) / aw * (img.width() - 1))
    y = int((fy - ay) / ah * (img.height() - 1))
    c = img.pixelColor(max(0, min(img.width() - 1, x)),
                       max(0, min(img.height() - 1, y)))
    return [c.red(), c.green(), c.blue(), c.alpha()]


def key_text(path: Path) -> str:
    reader = QtGui.QImageReader(str(path))
    return reader.text(getattr(store, "DEVICE_PHOTO_KEY", "GremlinBackgroundKey"))


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    wait_until(lambda: app.engine.rootObjects(), "the main window")
    out: dict = {"errors": []}
    maker = app.engine.rootContext().contextProperty("devicePhotoMaker")
    out["maker"] = maker is not None and type(maker).__name__
    out["host-ready"] = maker is not None and bool(maker.property("hostReady"))
    wanted: list = []
    if maker is not None and hasattr(maker, "renderWanted"):
        maker.renderWanted.connect(lambda *a: wanted.append(list(a)))
    # The start-up check (2 s after start): no background, nothing made.
    QtTest.QTest.qWait(2600)
    out["start-file"] = PHOTO.exists()

    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(GUID)

    def save(nodes: list) -> bool:
        return bool(hw.save(NAME, json.dumps({"nodes": nodes})))

    # 1. Save a map with a background.
    out["save-bg"] = save([RED, BLUE, GREEN, chip(0.75, 0.15)])
    made = wait_for(PHOTO.is_file, 20)
    out["made"] = made
    out["renders-1"] = len(wanted)
    if made:
        # Until the written file reads as a picture.
        wait_until(lambda: not QtGui.QImage(str(PHOTO)).isNull(), "the photo file",
                   5000, fail=False)
        img = QtGui.QImage(str(PHOTO)).convertToFormat(
            QtGui.QImage.Format.Format_ARGB32)
        out["size"] = [img.width(), img.height()]
        out["has-alpha"] = img.hasAlphaChannel()
        out["red"] = sample(img, 0.3, 0.1 + 0.4 * 16 / 9 / 4)
        out["blue"] = sample(img, 0.7, 0.7)
        out["hidden-green"] = sample(img, 0.2, 0.7)
        out["chip-corner"] = sample(img, 0.75, 0.15)
        out["file-key"] = key_text(PHOTO)
        doc = store.read_path(store.module_file_in(FOLDER))
        try:
            out["store-key"] = store.background_key(doc, FOLDER)
            out["store-file-key"] = store.device_photo_key(FOLDER)
            out["current"] = store.device_photo_current(FOLDER)
        except AttributeError as exc:
            out["errors"].append(f"store: {exc}")
        out["photo-url"] = hw.profilePhotoUrl(NAME, GUID)
        out["mtime-1"] = PHOTO.stat().st_mtime_ns

    # 2. Only the chip moves: nothing is made again.
    before = len(wanted)
    out["save-fg"] = save([RED, BLUE, GREEN, chip(0.2, 0.15)])
    QtTest.QTest.qWait(3500)
    out["renders-fg"] = len(wanted) - before
    out["mtime-2"] = PHOTO.stat().st_mtime_ns if PHOTO.exists() else None

    # 3. No background left: the file goes, no photo is shown.
    out["save-none"] = save([chip(0.2, 0.15)])
    out["removed"] = wait_for(lambda: not PHOTO.exists(), 10)
    out["photo-url-none"] = hw.profilePhotoUrl(NAME, GUID)

    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:  # noqa: BLE001 - always report and end
        import traceback

        traceback.print_exc()
        print("RESULT " + json.dumps({"crash": repr(exc)}), flush=True)
        smoke_exit(1)

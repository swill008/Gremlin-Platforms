# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and checks the hidden
renderer's two new jobs (07 S157, S83). Prints what it found as JSON.
test_device_photo_render.py runs it in its own process with a fresh user
folder.

1. The device's background picture: a DevicePhotoHost of its own, driven by
   a stand-in devicePhotoMaker, draws a background of a red picture
   (1600 x 800), a hidden blue picture, a half-strength green box and a
   flipped picture (yellow left, black right), with a chip in the
   foreground, and saves the PNG. A second job, one 300 x 150 picture, is
   not enlarged past its own pixels.
2. 100% export scale: a device map with a bottom picture (800 x 400) and a
   denser picture above it (1600 x 400 in a smaller box); the renderer's
   exportFactor in the Device Mapping Editor, with picture sizes known,
   without them, and with the denser picture hidden.

With SMOKE_QML_DIR set, the program's QML is loaded from that folder (the
test runs it once against the QML before this change).

    python test/unit/device_photo_render_smoke.py <folder>
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import gremlin.util  # noqa: E402

_QML = os.environ.get("SMOKE_QML_DIR", "")
if _QML:
    _plain = gremlin.util.resource_path

    def _resource(relative: str) -> str:
        rel = relative.replace("\\", "/")
        if rel == "qml" or rel.startswith("qml/"):
            return str(Path(_QML) / rel[len("qml") :].lstrip("/"))
        return _plain(relative)

    gremlin.util.resource_path = _resource

from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.modules import store  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
SIZES: dict[str, list[int]] = {}


def size_table() -> str:
    """A sizeOf function (HardwareProfile.pictureSize's job) for the
    pictures made here, by file name."""
    return (
        "function(u) { var t = " + json.dumps(SIZES) + ";"
        " var k = String(u).split('/').pop();"
        " return t[k] ? { w: t[k][0], h: t[k][1] } : null }"
    )


def picture(
    folder: Path, name: str, w: int, h: int, color: str, right: str | None = None
) -> None:
    img = QtGui.QImage(w, h, QtGui.QImage.Format.Format_RGB32)
    img.fill(QtGui.QColor(color))
    if right:
        p = QtGui.QPainter(img)
        p.fillRect(w // 2, 0, w - w // 2, h, QtGui.QColor(right))
        p.end()
    img.save(str(folder / name))
    SIZES[name] = [w, h]


def image_node(
    nid: str, name: str, fx: float, fy: float, fw: float, aspect: float, **extra: object
) -> dict:
    """A background picture in a box of its own proportions on the 16:9
    page (the picture fills its box, 07 S140)."""
    node = {
        "kind": "draw",
        "id": nid,
        "shape": "image",
        "plane": "background",
        "src": "pictures/" + name,
        "fx": fx,
        "fy": fy,
        "fw": fw,
        "fh": fw * (16 / 9) / aspect,
        "rot": 0,
        "opacity": 1,
        "locked": False,
        "pinned": False,
        "sockets": [],
        "fill": "filled",
    }
    node.update(extra)
    return node


class Maker(QtCore.QObject):
    """Stands in for gremlin/ui/device_photo.py's DevicePhotoMaker."""

    renderWanted = QtCore.Signal(str, str, str, int, str)

    def __init__(self) -> None:
        super().__init__()
        self._ready = False
        self.done: list = []

    def _get_ready(self) -> bool:
        return self._ready

    def _set_ready(self, value: bool) -> None:
        self._ready = bool(value)

    hostReady = QtCore.Property(bool, _get_ready, _set_ready)

    @QtCore.Slot(str, bool)
    def rendered(self, token: str, ok: bool) -> None:
        self.done.append([token, ok])


def matte(on_black: QtGui.QImage, on_white: QtGui.QImage) -> QtGui.QImage:
    """The transparent picture from the host's two grabs (what the maker
    does with them): on black is each pixel's colour times its strength;
    on white less on black is 1 - strength."""
    black = on_black.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    diff = on_white.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    p = QtGui.QPainter(diff)
    p.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Difference)
    p.drawImage(0, 0, black)
    p.end()
    diff.invertPixels()
    out = bytearray(black.constBits().tobytes())
    # Little-endian B, G, R, A: the strength from the green of the difference.
    alpha = diff.constBits().tobytes()[1::4]
    out[3::4] = alpha
    img = QtGui.QImage(
        bytes(out),
        black.width(),
        black.height(),
        black.bytesPerLine(),
        QtGui.QImage.Format.Format_ARGB32_Premultiplied,
    )
    return img.convertToFormat(QtGui.QImage.Format.Format_ARGB32)


def look(path: Path) -> dict:
    img = QtGui.QImage(str(path))
    if img.isNull():
        return {"missing": True}
    img = img.convertToFormat(QtGui.QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()

    def at(fx: float, fy: float) -> list[int]:
        c = img.pixelColor(min(w - 1, int(fx * w)), min(h - 1, int(fy * h)))
        return [c.red(), c.green(), c.blue(), c.alpha()]

    blue = 0
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            c = img.pixelColor(x, y)
            if c.blue() > 150 and c.red() < 80 and c.green() < 80 and c.alpha() > 100:
                blue += 1
    return {"size": [w, h], "has-alpha": img.hasAlphaChannel(), "blue": blue, "at": at}


def main() -> None:
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    pics = folder / "pictures"
    pics.mkdir(exist_ok=True)
    picture(pics, "red.png", 1600, 800, "#ff0000")
    picture(pics, "blue.png", 400, 400, "#0000ff")
    picture(pics, "flip.png", 200, 200, "#ffff00", right="#000000")
    picture(pics, "small.png", 300, 150, "#ff0000")

    # The map for the 100% check, in the device's own folder.
    dev = store.ensure_device_dir("pJoy Pro", GUID)
    mp = store.module_file_in(dev)
    (dev / "pictures").mkdir(exist_ok=True)
    picture(dev / "pictures", "bottom.png", 800, 400, "#ff0000")
    picture(dev / "pictures", "dense.png", 1600, 400, "#00ff00")
    mp.write_text(
        json.dumps(
            {
                "kind": "control.hardware",
                "device": "pJoy Pro",
                "nodes": [
                    image_node("p1", "bottom.png", 0.1, 0.1, 0.6, 2.0),
                    image_node("p2", "dense.png", 0.2, 0.6, 0.3, 4.0),
                    {
                        "kind": "btn",
                        "id": "b1",
                        "label": "Button 1",
                        "chipFx": 0.05,
                        "chipFy": 0.05,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    out: dict = {}
    engine = app.engine
    root = engine.rootObjects()[0]

    # --- 1. the device's background picture ------------------------------
    maker = Maker()
    ctx = QtQml.QQmlContext(engine.rootContext())
    ctx.setContextProperty("devicePhotoMaker", maker)
    qml_dir = Path(_QML) if _QML else ROOT / "qml"
    comp = QtQml.QQmlComponent(
        engine, QtCore.QUrl.fromLocalFile(str(qml_dir / "DevicePhotoHost.qml"))
    )
    ready = comp.status() == QtQml.QQmlComponent.Status.Ready
    host = comp.create(ctx) if ready else None
    out["host-errors"] = [e.toString() for e in comp.errors()][:3]
    if host is not None:
        # Parented to the window so it is drawn (a grab needs a window).
        host.setParentItem(root.contentItem() if hasattr(root, "contentItem") else root)
        host.setParent(root)
        out["host-ready"] = maker.hostReady

        def ev(code: str) -> object:
            expr = QtQml.QQmlExpression(QtQml.qmlContext(host), host, code)
            value = expr.evaluate()
            if expr.hasError():
                return "error: " + expr.error().toString()
            value = value[0] if isinstance(value, tuple) else value
            return value.toVariant() if hasattr(value, "toVariant") else value

        # Picture sizes from the files made above (HardwareProfile
        # .pictureSize's job; the renderer reads them through sizeOf).
        ev("renderer.sizeOf = " + size_table())
        pics_url = QtCore.QUrl.fromLocalFile(str(pics)).toString() + "/"
        nodes = [
            image_node("bg1", "red.png", 0.1, 0.1, 0.5, 2.0),
            image_node("bg2", "blue.png", 0.75, 0.6, 0.2, 1.0, hidden=True),
            {
                "kind": "draw",
                "id": "bg3",
                "shape": "rect",
                "plane": "background",
                "fx": 0.55,
                "fy": 0.5,
                "fw": 0.1,
                "fh": 0.1,
                "rot": 0,
                "opacity": 0.5,
                "color": "#00ff00",
                "border": "#00ff00",
                "stroke": 1,
                "fill": "filled",
            },
            image_node("bg4", "flip.png", 0.2, 0.6, 0.1, 1.0, flipH=True),
            {
                "kind": "btn",
                "id": "b1",
                "label": "Button 1",
                "chipFx": 0.9,
                "chipFy": 0.9,
            },
        ]
        out["area"] = ev(
            "JSON.stringify(renderer.jobNodes("
            + json.dumps(json.dumps(nodes))
            + ", true, true).map(function(n) { return n.id }))"
        )

        def job(token: str, node_list: list, side: int) -> dict:
            target = folder / (token + ".png")
            count = len(maker.done) + 1
            maker.renderWanted.emit(
                token, json.dumps(node_list), pics_url, side, str(target)
            )
            for _ in range(600):
                QtTest.QTest.qWait(25)
                if len(maker.done) >= count:
                    break
            white = folder / (token + ".white.png")
            done = maker.done[-1] if len(maker.done) >= count else None
            if not (target.is_file() and white.is_file()):
                return {"missing": True, "done": done}
            final = folder / (token + "-final.png")
            black_img = QtGui.QImage(str(target))
            white_img = QtGui.QImage(str(white))
            matte(black_img, white_img).save(str(final))
            got = look(final)
            got["white-size"] = [white_img.width(), white_img.height()]
            got["done"] = done
            return got

        whole = job("whole", nodes, 1024)
        at = whole.pop("at", None)
        if at:
            # The cut: x 0.1 to 0.65 of the page (red picture to green box),
            # y 0.1 to the flipped picture's foot.
            fh = 0.6 + 0.1 * 16 / 9 - 0.1
            # Corners of the cut: nothing drawn there (transparent ground).
            whole["corner-top-right"] = at(0.99, 0.01)
            whole["corner-bottom-right"] = at(0.99, 0.99)
            # The red picture's middle; the green box at half strength
            # (x 0.62, y 0.57 of the page: off the red picture).
            whole["red-middle"] = at((0.35 - 0.1) / 0.55, (0.32 - 0.1) / fh)
            whole["green"] = at((0.62 - 0.1) / 0.55, (0.57 - 0.1) / fh)
            # The flipped picture: black on its left now, yellow on its right.
            fy = (0.6 + 0.1 * 16 / 9 / 2 - 0.1) / fh
            whole["flip-left"] = at((0.22 - 0.1) / 0.55, fy)
            whole["flip-right"] = at((0.28 - 0.1) / 0.55, fy)
        out["whole"] = whole
        small = job("small", [image_node("s1", "small.png", 0.1, 0.1, 0.5, 2.0)], 1024)
        small.pop("at", None)
        out["small"] = small
        empty = job(
            "empty",
            [
                {
                    "kind": "btn",
                    "id": "b1",
                    "label": "Button 1",
                    "chipFx": 0.5,
                    "chipFy": 0.5,
                }
            ],
            1024,
        )
        empty.pop("at", None)
        out["empty"] = empty

    # --- 2. 100% export scale -------------------------------------------
    def call(obj: QtCore.QObject, name: str, *args: object) -> object:
        return QtCore.QMetaObject.invokeMethod(
            obj,
            name,
            QtCore.Q_RETURN_ARG("QVariant"),
            *[QtCore.Q_ARG("QVariant", a) for a in args],
        )

    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openDeviceMappingEditorForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "deviceMappingEditorWindow")
    win.setProperty("width", 1200)
    win.setProperty("height", 800)
    QtTest.QTest.qWait(600)

    def wev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    geo = (
        "var e = _editorWin._ed(); var a = e.nodes[0], b = e.nodes[1];"
        " JSON.stringify({bottom: 800 / e.drawGeom(a).w,"
        " dense: 1600 / e.drawGeom(b).w,"
        " ids: [a.id, b.id], natural: e.photoNatural()})"
    )
    for _ in range(80):
        QtTest.QTest.qWait(50)
        g = wev(geo)
        if isinstance(g, str) and not g.startswith("error") and '"w":800' in g:
            break
    good = isinstance(g, str) and not g.startswith("error")
    out["geom"] = json.loads(g) if good else g
    # The dialog's own sizeOf (HardwareProfile.pictureSize), when wired.
    out["wired-100"] = wev("_renderer.exportFactor(_editorWin._ed(), 100)")
    # Without sizeOf: only the bottom picture's size is known.
    wev("_renderer.sizeOf = null")
    out["fallback-100"] = wev("_renderer.exportFactor(_editorWin._ed(), 100)")
    wev("_renderer.sizeOf = " + size_table())
    out["sized-100"] = wev("_renderer.exportFactor(_editorWin._ed(), 100)")
    out["sized-50"] = wev("_renderer.exportFactor(_editorWin._ed(), 50)")
    wev("var e = _editorWin._ed(); e.nodes[1].hidden = true; e.bump()")
    QtTest.QTest.qWait(100)
    out["dense-hidden-100"] = wev("_renderer.exportFactor(_editorWin._ed(), 100)")
    win.close()
    QtTest.QTest.qWait(300)
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        smoke_exit(1)

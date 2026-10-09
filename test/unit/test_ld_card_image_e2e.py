# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device card's picture end to end (03 S88, D-03-LD-IMAGE): the
real Home page (qml/StatusPage.qml) off-screen over the real ModuleListModel
and a temp modules folder. A real right-click opens the Logical Device
card's own menu; Add Image… opens the page's FilePicker, which is handed a
PNG as its file dialog would; the card then shows the photo and the module
file has "image". The menu then reads Change Image… and Remove Image, and
Remove Image clears both.

The off-screen part runs in its own process (this file run as a script):

    python test/unit/test_ld_card_image_e2e.py <out_dir>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]

# A 1x1 PNG.
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cfc0f01f0005000201a5c7"
    "c2a60000000049454e44ae426082"
)

_WRAPPER = """
import QtQuick
import QtQuick.Controls

import "{qml}"

ApplicationWindow {{
    id: _win
    width: 1200
    height: 800
    visible: true

    StatusPage {{
        id: _page
        objectName: "homePage"
        anchors.fill: parent
        model: cards
    }}

    function logicalCard() {{
        var list = _page._liveCards
        for (var i = 0; i < list.length; ++i)
            if (list[i] && list[i].slug === "logical")
                return list[i]
        return null
    }}
}}
"""


def _child() -> None:
    """The off-screen run: prints "RESULT name json", "ERROR ...", "done"."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
    os.environ["QT_FILE_SELECTORS"] = "Universal"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    sys.path.insert(0, str(_ROOT))
    sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(dir=out))

    import unittest.mock

    import gremlin.util

    gremlin.util.userprofile_path = unittest.mock.Mock(return_value=str(profile))

    import shiboken6
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest

    import gremlin.ui.device  # noqa: F401  (Gremlin.Device)
    import gremlin.ui.folder_memory  # noqa: F401  (FilePicker)
    from gremlin import logical_device_file as ldf
    from gremlin.ui import module_model

    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    class FakeBackend(QtCore.QObject):
        changed = QtCore.Signal()
        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)
        gremlinActive = QtCore.Property(bool, fget=lambda self: False, notify=changed)

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )

    path = ldf.path()
    result("modules", str(path.parent))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": "Logical Device"}), encoding="utf-8")
    pick = out / "pick" / "card.png"
    pick.parent.mkdir(exist_ok=True)
    pick.write_bytes(_PNG)

    cards = module_model.ModuleListModel()
    cards.reload()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("cards", cards)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    wrapper = out / "LdImageHarness.qml"
    wrapper.write_text(
        _WRAPPER.format(qml=(_ROOT / "qml").as_uri()), encoding="utf-8"
    )
    engine.load(QtCore.QUrl.fromLocalFile(str(wrapper)))
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)
        return
    win = roots[0]
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    QtTest.QTest.qWait(500)

    def ev(name: str, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {name}: {expr.error().toString()}", flush=True)
            return None
        return value[0] if isinstance(value, tuple) else value

    def card() -> QtCore.QObject | None:
        found = ev("card", "logicalCard()")
        return found if isinstance(found, QtCore.QObject) else None

    def menu_of(c: QtCore.QObject) -> QtCore.QObject | None:
        # The card's own ContextMenu (a Popup with describe/activate).
        for child in c.findChildren(QtCore.QObject):
            meta = child.metaObject()
            if meta.indexOfMethod("activate(QVariant,QVariant)") >= 0 and (
                meta.indexOfMethod("describe()") >= 0
            ):
                return child
        return None

    def picker() -> QtCore.QObject | None:
        page = win.findChild(QtCore.QObject, "homePage")
        for dialog in page.findChildren(QtCore.QObject, "filePickerFileDialog"):
            owner = dialog.parent()
            if owner is not None and owner.property("title") == "Choose Image":
                return owner
        return None

    def right_click(c: QtCore.QObject) -> None:
        item = shiboken6.wrapInstance(shiboken6.getCppPointer(c)[0], QtQuick.QQuickItem)
        pos = item.mapToScene(QtCore.QPointF(30, 30)).toPoint()
        QtTest.QTest.mouseClick(
            quick,
            QtCore.Qt.MouseButton.RightButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            pos,
        )
        QtTest.QTest.qWait(250)

    def on(obj: QtCore.QObject, code: str) -> object:
        # JavaScript with obj as its scope (the menu's own functions).
        expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {code}: {expr.error().toString()}", flush=True)
            return None
        return value[0] if isinstance(value, tuple) else value

    def open_device(menu: QtCore.QObject) -> list[str]:
        # The menu remembers an open section: open Device only when shut.
        rows = str(on(menu, "describe().join('|')") or "").split("|")
        if "> Device" in rows:
            on(menu, "activate('Device')")
            rows = str(on(menu, "describe().join('|')") or "").split("|")
        return rows

    def activate(menu: QtCore.QObject, text: str) -> object:
        return on(menu, f"activate({json.dumps(text)})")

    def doc() -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    c = card()
    if c is None:
        print("ERROR no Logical Device card on the Home page", flush=True)
    else:
        menu = menu_of(c)
        if menu is None:
            print("ERROR the card has no context menu", flush=True)
        else:
            # Add Image… from a real right-click.
            right_click(c)
            result("opened", bool(menu.property("opened")))
            result("bare", open_device(menu))
            result("add-ran", activate(menu, "Add Image…"))
            QtTest.QTest.qWait(200)
            pk = picker()
            if pk is None:
                print("ERROR no Choose Image FilePicker on the page", flush=True)
            else:
                dialog = pk.findChild(QtCore.QObject, "filePickerFileDialog")
                result("dialog-shown", bool(dialog.property("visible")))
                on(dialog, "close()")
                QtTest.QTest.qWait(100)
                # What the file dialog's Accept hands the picker.
                on(pk, f"_accept({json.dumps(pick.as_uri())})")
                QtTest.QTest.qWait(300)
                c = card()
                result("photo-after-add", str(c.property("photo")) if c else "")
                result("image-after-add", doc().get("image", None))
                files = sorted(p.name for p in path.parent.rglob("photo*.*"))
                result("files-after-add", files)

                # The menu now offers Change Image… and Remove Image.
                if c is not None:
                    menu = menu_of(c) or menu
                    on(menu, "close()")
                    QtTest.QTest.qWait(100)
                    right_click(c)
                    result("with-photo", open_device(menu))
                    result("remove-ran", activate(menu, "Remove Image"))
                    QtTest.QTest.qWait(300)
                    c = card()
                    result("photo-after-remove", str(c.property("photo")) if c else "?")
                    result("image-after-remove", doc().get("image", None))
                    files = sorted(p.name for p in path.parent.rglob("photo*.*"))
                    result("files-after-remove", files)
                    on(menu, "close()")
                    QtTest.QTest.qWait(100)
                    right_click(c)
                    result("after-remove", open_device(menu))
    quick.grabWindow().save(str(out / "home.png"))
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    del app


def _run(tmp_path: Path) -> dict[str, object]:
    profile = tmp_path / "profile"
    profile.mkdir()
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(tmp_path / "out")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8",
            "USERPROFILE": str(profile),
        },
    )
    lines = proc.stdout.splitlines()
    assert "done" in lines, (proc.stdout[-2000:], proc.stderr[-3000:])
    errors = [line for line in lines if line.startswith("ERROR")]
    assert errors == [], (errors, proc.stderr[-2000:])
    found: dict[str, object] = {}
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            found[name] = json.loads(value)
    return found


def test_logical_card_add_change_remove_image_end_to_end(tmp_path: Path) -> None:
    r = _run(tmp_path)
    modules = Path(str(r["modules"]))
    assert str(tmp_path) in str(modules)  # never the real folder

    assert r["opened"] is True
    bare = r["bare"]
    assert isinstance(bare, list)
    assert "  Add Image…" in bare and "  Remove Image" not in bare
    assert r["add-ran"] is True
    assert r["dialog-shown"] is True

    # The card shows the picture; the module file names it.
    assert r["photo-after-add"], r
    assert "logical_device/photo.png" in str(r["photo-after-add"])
    assert r["image-after-add"] == "logical_device/photo.png"
    assert r["files-after-add"] == ["photo.png"]

    with_photo = r["with-photo"]
    assert isinstance(with_photo, list)
    assert "  Change Image…" in with_photo and "  Remove Image" in with_photo
    assert "  Add Image…" not in with_photo

    assert r["remove-ran"] is True
    assert r["photo-after-remove"] == ""
    assert r["image-after-remove"] in ("", None)
    assert r["files-after-remove"] == []
    after = r["after-remove"]
    assert isinstance(after, list)
    assert "  Add Image…" in after and "  Remove Image" not in after


if __name__ == "__main__":
    _child()

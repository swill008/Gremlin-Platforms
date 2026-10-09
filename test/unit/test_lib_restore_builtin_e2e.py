# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Restore of the Logical Device from the Device Library end to end (10 S6,
S6a, S48, D-04-LD-FILE): the real Device Library window
(qml/WindowDeviceLibrary.qml) off-screen over its real model, the real
Library, store and History, in a temp modules folder. The Logical Device's
module file has a picture and two controls; Save to Device Library keeps
them. Then a control is removed and the picture changed, and the device's
Restore… button (real clicks, its question's Restore button too) puts the
saved setup back: no "isn't plugged in", the layout and picture are back in
the module file, the Logical Device has both controls, the Home card's
photo is back, and History has one new entry.

The off-screen part runs in its own process (this file run as a script):

    python test/unit/test_lib_restore_builtin_e2e.py <out_dir>
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]

# Two different 1x1 PNGs: the saved picture and the one it is changed to.
_PNG_SAVED = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cfc0f01f0005000201a5c7"
    "c2a60000000049454e44ae426082"
)
_PNG_LATER = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)


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

    import gremlin.ui.folder_memory  # noqa: F401  (FilePicker)
    from gremlin import clock, history, logical_device_file
    from gremlin.logical_device import LogicalDevice
    from gremlin.modules import ids, module_file, store

    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    class FakeBackend(QtCore.QObject):
        changed = QtCore.Signal()
        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)
        gremlinActive = QtCore.Property(bool, fget=lambda self: False, notify=changed)

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style",
        1,
        0,
        "Style",
    )
    import gremlin.ui.window_placement  # noqa: F401  (Gremlin.UI WindowPlacement)
    import joystick_gremlin
    from gremlin.ui import module_model
    from gremlin.ui.device_library_model import DeviceLibraryModel

    joystick_gremlin.register_config_options()

    # The Logical Device's module file: two controls and a picture.
    ld_guid = "{" + str(ids.LOGICAL_DEVICE).upper() + "}"
    slug = logical_device_file.SLUG
    path = logical_device_file.path()
    result("modules", str(path.parent))
    path.parent.mkdir(parents=True, exist_ok=True)

    def control(n: int, label: str) -> dict:
        return {
            "uid": f"{n:032x}",
            "type": "button",
            "id": n,
            "label": label,
            "user-label": "",
            "group": "",
            "hide-system": False,
        }

    layout = {"controls": [control(1, "Fire"), control(2, "Jump")], "groups": []}
    module_file.write_bytes(
        path,
        json.dumps(
            {
                "kind": "control.hardware",
                "device": "Logical Device",
                "boundGuidLocal": ld_guid,
                "nodes": [],
                "claim": {},
                logical_device_file.KEY: layout,
            }
        ).encode(),
    )
    logical_device_file.load()

    def set_photo(data: bytes) -> None:
        # As the card's Add / Change Image does: photo.png through the store
        # and the module file's "image".
        store.remove_picture_files(store.photo_files(slug))
        store.put_picture_at(store.pictures_dir_of(slug) / "photo.png", data)
        ref = store.picture_ref(slug, "photo.png")

        def change(doc: dict) -> None:
            doc["image"] = ref

        if not store.update_path(path, change, "Home"):
            print("ERROR the picture wasn't set", flush=True)

    set_photo(_PNG_SAVED)

    def doc() -> dict:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def file_labels() -> list[str]:
        rows = (doc().get(logical_device_file.KEY) or {}).get("controls") or []
        return [str(c.get("label")) for c in rows]

    def ld_labels() -> list[str]:
        return [str(c.get("label")) for c in LogicalDevice().to_dict()["controls"]]

    def photo_bytes() -> str:
        found = store.photo_files(slug)
        if not found:
            return ""
        return "saved" if found[0].read_bytes() == _PNG_SAVED else "other"

    def card_photo() -> str:
        # The picture the Home card shows (the Home page's model, read
        # afresh): "saved", "other" or "" for none.
        url = str(module_model.ModuleListModel().cardMap("logical").get("photo") or "")
        if not url:
            return ""
        shown = Path(QtCore.QUrl(url).toLocalFile())
        if not shown.is_file():
            return "missing"
        return "saved" if shown.read_bytes() == _PNG_SAVED else "other"

    result("ld-start", ld_labels())
    result("card-start", card_photo())

    model = DeviceLibraryModel(watch_devices=False)
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("deviceLibrary", model)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.load(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "WindowDeviceLibrary.qml"))
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)
        os._exit(0)
    win = roots[0]
    win.setProperty("width", 1180)
    win.setProperty("height", 720)
    win.setProperty("visible", True)
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {code}: {expr.error().toString()}", flush=True)
            return None
        return value[0] if isinstance(value, tuple) else value

    def pump(cond: str = "", timeout: float = 15.0) -> bool:
        deadline = clock.monotonic() + timeout
        while True:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
            if not cond or bool(ev(cond)):
                return True
            if clock.monotonic() > deadline:
                print(f"ERROR timed out waiting for {cond}", flush=True)
                return False

    def walk(item: QtQuick.QQuickItem):  # noqa: ANN202
        yield item
        for kid in item.childItems():
            yield from walk(kid)

    def find_item(name: str) -> QtQuick.QQuickItem | None:
        roots_ = [quick.contentItem()]
        overlay = win.property("overlay")
        if overlay is not None:
            roots_.append(
                shiboken6.wrapInstance(
                    shiboken6.getCppPointer(overlay)[0], QtQuick.QQuickItem
                )
            )
        for root in roots_:
            for item in walk(root):
                if item.objectName() == name:
                    return item
        found = win.findChild(QtQuick.QQuickItem, name)
        return found

    def click(name: str) -> bool:
        item = find_item(name)
        if item is None or not item.isVisible():
            print(f"ERROR {name} isn't on show", flush=True)
            return False
        at = item.mapToScene(
            QtCore.QPointF(item.width() / 2, item.height() / 2)
        ).toPoint()
        QtTest.QTest.mouseClick(
            quick,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            at,
        )
        pump()
        return True

    def history_count() -> int:
        return len(history.entries())

    pump("deviceLibrary.rows.length > 0")
    ld_key = str(
        ev(
            "(deviceLibrary.rows.filter(r => r.name === 'Logical Device')[0]"
            " || {key: ''}).key"
        )
        or ""
    )
    result("ld-row", ld_key)
    if not ld_key:
        print("ERROR no Logical Device row in the Device Library", flush=True)
    else:
        # Save to Device Library… (its dialog's Save).
        ev(f"deviceLibrary.select({json.dumps(ld_key)}); _lib.openSave()")
        pump("_saveDlg.opened")
        pump()
        result("save-enabled", ev("_saveDlg.hasModule"))
        ev("_saveDlg.accept()")
        pump("!deviceLibrary.busy && _lib.message.length > 0")
        result("save-message", ev("_lib.message"))
        pump("deviceLibrary.details.count > 0")
        result("saved-count", ev("deviceLibrary.details.count"))

        # Change it: one control removed (as the Logical Device's editor
        # saves) and another picture.
        LogicalDevice().load_dict({"controls": [control(1, "Fire")], "groups": []})
        logical_device_file.save(who="Home")
        set_photo(_PNG_LATER)
        result("file-changed", file_labels())
        result("ld-changed", ld_labels())
        result("photo-changed", photo_bytes())
        result("card-changed", card_photo())

        history.entries()
        before = history_count()

        # Restore… on the device's details, then the question's Restore.
        ev(f"deviceLibrary.select({json.dumps(ld_key)}); _lib.showMessage('', false)")
        pump()
        result("restore-shown", bool(find_item("libraryRestoreButton")))
        button = find_item("libraryRestoreButton")
        result("restore-enabled", bool(button is not None and button.isEnabled()))
        if click("libraryRestoreButton") and pump("_restoreDlg.opened"):
            result("question", ev("_restoreDlg.title"))
            # Its opening transition ends before the click.
            QtTest.QTest.qWait(400)
            click("libraryRestoreDialogGo")
            pump("!_restoreDlg.opened")
            pump("!deviceLibrary.busy && _lib.message.length > 0")
        result("restore-message", ev("_lib.message"))
        result("restore-bad", ev("_lib.messageBad"))
        pump()
        result("file-after", file_labels())
        result("image-after", str(doc().get("image") or ""))
        result("photo-after", photo_bytes())
        result("ld-after", ld_labels())
        result("card-after", card_photo())
        after = history_count()
        result("history-new", after - before)
        result(
            "history-titles",
            [str(e.get("title") or e.get("summary") or "") for e in history.entries()][
                : max(after - before, 0)
            ],
        )
    quick.grabWindow().save(str(out / "library.png"))
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    os._exit(0)


def _run(tmp_path: Path) -> dict[str, object]:
    profile = tmp_path / "profile"
    profile.mkdir()
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(tmp_path / "out")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8",
            "USERPROFILE": str(profile),
        },
    )
    lines = proc.stdout.splitlines()
    assert "done" in lines, (proc.stdout[-3000:], proc.stderr[-3000:])
    errors = [line for line in lines if line.startswith("ERROR")]
    found: dict[str, object] = {}
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            found[name] = json.loads(value)
    assert errors == [], (errors, found, proc.stderr[-2000:])
    return found


def test_restore_of_the_logical_device_from_the_library_end_to_end(
    tmp_path: Path,
) -> None:
    r = _run(tmp_path)
    assert str(tmp_path) in str(r["modules"])  # never the real folder
    assert r["ld-start"] == ["Fire", "Jump"]
    assert r["card-start"] == "saved"

    # Saved to the Device Library.
    assert r["ld-row"]
    assert r["save-message"] == "Saved to the Device Library.", r
    assert int(r["saved-count"]) >= 1  # type: ignore[arg-type]

    # Changed: one control, another picture.
    assert r["file-changed"] == ["Fire"]
    assert r["ld-changed"] == ["Fire"]
    assert r["photo-changed"] == "other"
    assert r["card-changed"] == "other"

    # Restore: offered, not refused as unplugged, and everything is back.
    assert r["restore-shown"] is True and r["restore-enabled"] is True
    message = str(r["restore-message"])
    assert "plugged in" not in message, r
    assert r["restore-bad"] is False, r
    assert message.startswith("Restored."), r
    assert r["file-after"] == ["Fire", "Jump"], r
    assert "photo.png" in str(r["image-after"]), r
    assert r["photo-after"] == "saved", r
    assert r["ld-after"] == ["Fire", "Jump"], r
    assert r["card-after"] == "saved", r
    # One History entry for the whole Restore.
    assert r["history-new"] == 1, r


if __name__ == "__main__":
    _child()

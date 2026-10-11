# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Export Device… and Import Device… open their box from the real Home page
(08 S111, D-03-DEVICE-FOLDERS): qml/StatusPage.qml off-screen over the real
ModuleListModel. The box (DialogDeviceExport.qml, a Popup) must open inside
the window; made as a separate window it failed with "Cannot assign to
non-existent property transientParent" and never showed.

The off-screen part runs in its own process (this file run as a script):

    python test/unit/test_device_export_dialog_e2e.py <out_dir>
"""

from __future__ import annotations

import json
import os
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

    from PySide6 import QtCore, QtGui, QtQml, QtTest

    import gremlin.ui.device  # noqa: F401  (Gremlin.Device)
    import gremlin.ui.device_export  # noqa: F401  (DeviceExport)
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
        "Gremlin.Style",
        1,
        0,
        "Style",
    )

    from gremlin.modules import ids, store

    store.ensure_device_dir("Logical Device", str(ids.LOGICAL_DEVICE))
    path = ldf.path()
    result("modules", str(path.parent))
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
    wrapper = out / "DeviceExportHarness.qml"
    wrapper.write_text(_WRAPPER.format(qml=(_ROOT / "qml").as_uri()), encoding="utf-8")
    engine.load(QtCore.QUrl.fromLocalFile(str(wrapper)))
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)
        return
    win = roots[0]
    QtTest.QTest.qWait(500)

    def ev(name: str, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {name}: {expr.error().toString()}", flush=True)
            return None
        return value[0] if isinstance(value, tuple) else value

    def dialog() -> QtCore.QObject | None:
        found = [
            d
            for d in win.findChildren(QtCore.QObject, "deviceExportDialog")
            if d.property("opened")
        ]
        return found[-1] if found else None

    for mode in ("export", "import"):
        ran = ev(mode, f"_page.{mode}Device(logicalCard()); 'ok'")
        QtTest.QTest.qWait(300)
        box = dialog()
        result(f"{mode}-ran", ran)
        result(f"{mode}-open", box is not None)
        result(f"{mode}-mode", str(box.property("mode")) if box else "")
        if box is not None:
            on = QtQml.QQmlExpression(QtQml.qmlContext(box), box, "close()")
            on.evaluate()
            QtTest.QTest.qWait(300)
            result(f"{mode}-gone", dialog() is None)
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    del app


def _run(tmp_path: Path) -> dict[str, object]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    profile = tmp_path / "profile"
    profile.mkdir()
    proc = proc_tree.run(
        [sys.executable, str(Path(__file__).resolve()), str(tmp_path / "out")],
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


def test_export_and_import_device_open_their_box_on_the_home_page(
    tmp_path: Path,
) -> None:
    r = _run(tmp_path)
    assert str(tmp_path) in str(r["modules"])  # never the real folder
    for mode in ("export", "import"):
        assert r[f"{mode}-ran"] == "ok"
        assert r[f"{mode}-open"] is True, r
        assert r[f"{mode}-mode"] == mode
        assert r[f"{mode}-gone"] is True


if __name__ == "__main__":
    _child()

# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""07 S104 (D-07-EDITOR-LOADFAIL, AD8): when the Device Mapping Editor
(VkbRigEditor.qml) can't load, VkbRigFace shows the plain error "The Button
Map editor could not load." and the reason goes to the log; no built-in
device layout (the old EVO R tag column and its leader lines) is shown.

Real QML off-screen: the real VkbRigFace.qml is copied next to a broken
VkbRigEditor.qml in a temp folder. Needs a QGuiApplication, so the checks
run in a child process (this file run as a script).
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
MESSAGE = "The Device Mapping Editor could not load."

_HOST = r"""
import QtQuick

Window {
    width: 900; height: 700
    visible: true
    VkbRigFace { objectName: "face"; anchors.fill: parent }
}
"""


def _child() -> None:
    from PySide6 import QtCore, QtGui, QtQml, QtQuick

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    folder = pathlib.Path(sys.argv[2])
    shutil.copy(_ROOT / "qml" / "VkbRigFace.qml", folder / "VkbRigFace.qml")
    (folder / "VkbRigEditor.qml").write_text("Item { this is not QML", encoding="utf-8")
    (folder / "host.qml").write_text(_HOST, encoding="utf-8")

    engine = QtQml.QQmlApplicationEngine(app)
    engine.addImportPath(str(_ROOT / "theme"))
    engine.load(QtCore.QUrl.fromLocalFile(str(folder / "host.qml")))
    roots = engine.rootObjects()
    assert roots, "host.qml failed to load"
    win = roots[0]
    deadline = QtCore.QDeadlineTimer(300)
    while not deadline.hasExpired():
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)

    face = win.findChild(QtQuick.QQuickItem, "face")
    error = win.findChild(QtQuick.QQuickItem, "editorLoadError")
    print("RESULT error_found", error is not None)
    if error is not None:
        print("RESULT error_visible", error.isVisible())
        print("RESULT error_text", error.property("text"))
    # Any visible text other than the error (the EVO tags read "3 → —").
    others = [
        str(item.property("text"))
        for item in face.findChildren(QtQuick.QQuickItem)
        if item.metaObject().className().startswith("QQuickText")
        and item.isVisible()
        and item is not error
        and str(item.property("text") or "")
    ]
    print("RESULT other_texts", ascii(others))
    sys.stdout.flush()
    print("done")
    sys.stdout.flush()
    os._exit(0)


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
    tmp_path = tmp_path_factory.mktemp("editor_load_error")
    import child_env  # pyright: ignore[reportMissingImports]  (test/)

    run = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__)), "child", str(tmp_path)],
        text=True,
        timeout=120,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            # As the program (gremlin/qt_log.py): Qt writes to the error stream.
            "QT_FORCE_STDERR_LOGGING": "1",
            "QT_QUICK_CONTROLS_STYLE": "Basic",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
            # Kept, not replaced: it carries test/hang_trace (the child's
            # dill/vJoy guards and its stack dump if it stalls).
            "PYTHONPATH": child_env.python_path(_ROOT),
        },
    )
    lines = run.stdout.splitlines()
    assert "done" in lines, smoke_report.explain(run)
    found = dict(
        tuple(line.split(" ", 2)[1:]) for line in lines if line.startswith("RESULT ")
    )
    found["stderr"] = run.stderr
    return found


def test_failed_load_shows_the_plain_error(found: dict[str, str]) -> None:
    assert found["error_found"] == "True"
    assert found["error_visible"] == "True"
    assert found["error_text"] == MESSAGE


def test_failed_load_shows_no_device_layout(found: dict[str, str]) -> None:
    assert found["other_texts"] == "[]"


def test_the_reason_goes_to_the_log(found: dict[str, str]) -> None:
    # console.warn goes to the error stream, which qt_log copies to qt.log.
    assert "The Device Mapping Editor could not load:" in found["stderr"]
    assert "VkbRigEditor.qml" in found["stderr"]


def test_no_evo_layout_left_in_the_face() -> None:
    text = (_ROOT / "qml" / "VkbRigFace.qml").read_text(encoding="utf-8")
    for word in ("HatPlus", "component Tag", "photoPt", "face_map", "_leftPane"):
        assert word not in text, word
    assert not (_ROOT / "qml" / "vkb_evo_l_face_map.md").exists()
    assert not (_ROOT / "qml" / "vkb_evo_r_face_map.md").exists()


if __name__ == "__main__" and sys.argv[1:2] == ["child"]:
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "test"))
    import fake_hardware  # pyright: ignore[reportMissingImports]

    fake_hardware.install()  # never the PC's own devices or vJoy
    _child()

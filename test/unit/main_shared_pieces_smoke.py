# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and drives the main
window's pages on the shared pieces (01 S140, S143): Save As / Open profile
choosers remember the profile folder, Home's Delete Device, the Scripts
page's Remove and the OSC page's Clear ask the shared question (Enter and
Esc cancel), the Output View's Screen Background picks a picture. Prints the
findings as JSON. test_main_shared_pieces.py runs it in its own process with
a fresh user folder.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
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

from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

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


def inner(item: QtCore.QObject) -> QtCore.QObject:
    """A child made by the item's own .qml file: its ids are in scope there."""
    for child in item.childItems():
        own = QtQml.qmlContext(child)
        if own is not None and own != QtQml.qmlContext(item):
            return child
    return item


def question(win: QtCore.QObject) -> QtCore.QObject | None:
    for obj in win.findChildren(QtCore.QObject, "confirmDialog"):
        if obj.property("opened"):
            return obj
    return None


def describe(dlg: QtCore.QObject | None) -> dict:
    if dlg is None:
        return {}
    return {
        "title": dlg.property("titleText"),
        "text": dlg.property("bodyText"),
        "last": dlg.property("lastLine"),
        "action": dlg.property("actionText"),
    }


def key(win: QtGui.QWindow, k: QtCore.Qt.Key) -> None:
    QtTest.QTest.keyClick(win, k)
    wait_until(lambda: False, 200)


def section(name: str, fn) -> None:  # noqa: ANN001
    print("SECTION " + name, file=sys.stderr, flush=True)
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        import traceback
        out["errors"].append(f"{name}: {exc!r} " + traceback.format_exc()[-600:])


out: dict = {"errors": []}
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))
win.requestActivate()
wait_until(lambda: False, 300)
work = Path(tempfile.mkdtemp(prefix="bmain_"))
folder_url = QtCore.QUrl.fromLocalFile(str(work)).toString()


def profiles() -> None:
    # Save As saves into a chosen folder; Open then starts there.
    out["save_kind"] = ev(win, "_saveProfileFileDialog.kind")
    out["open_kind"] = ev(win, "_loadProfileFileDialog.kind")
    target = QtCore.QUrl.fromLocalFile(str(work / "chosen.xml")).toString()
    ev(win, (
        "(function(){var d=_saveProfileFileDialog.prepare();"
        f"d.selectedFile={json.dumps(target)};d.accepted();return true}})()"
    ))
    wait_until(lambda: (work / "chosen.xml").exists(), 5000)
    out["saved"] = (work / "chosen.xml").exists()
    out["open_start"] = str(
        ev(win, "String(_loadProfileFileDialog.prepare().currentFolder)")
    )
    out["folder_url"] = folder_url
    # Closing Save As without saving calls off a waiting quit.
    ev(win, (
        "_saveProfileFileDialog.afterSave = function(){};"
        "_saveProfileFileDialog.afterSaveQuitting = false;"
        "_saveProfileFileDialog.prepare().rejected(); true"
    ))
    out["cancel_clears"] = bool(ev(win, "_saveProfileFileDialog.afterSave === null"))


def delete_device() -> None:
    page = ev(win, "_statusLoader.item")
    assert page is not None, "no Home"
    page = inner(page)
    slug = ev(page, (
        "(function(){for(var i=0;i<_liveCards.length;++i){var c=_liveCards[i];"
        "if(c&&c.slug&&c.direction!=='dest')return c.slug}return ''})()"
    ))
    out["delete_slug"] = slug
    ev(page, f"askDelete(model.cardMap({json.dumps(slug)}))")
    wait_until(lambda: bool(ev(page, "_explainDialog.opened")), 3000)
    ev(page, "_explainAdvance = true; _explainDialog.close(); true")
    wait_until(lambda: question(win) is not None, 3000)
    dlg = question(win)
    out["delete_question"] = describe(dlg)
    key(win, QtCore.Qt.Key.Key_Return)
    out["delete_enter_closed"] = question(win) is None
    out["delete_done_after_enter"] = bool(ev(page, "_doneDialog.opened"))
    # Asked again, a click on the red button deletes (step 3: the result).
    ev(page, f"askDelete(model.cardMap({json.dumps(slug)}))")
    wait_until(lambda: bool(ev(page, "_explainDialog.opened")), 3000)
    ev(page, "_explainAdvance = true; _explainDialog.close(); true")
    wait_until(lambda: question(win) is not None, 3000)
    ev(question(win), "_go.clicked(); true")
    wait_until(lambda: bool(ev(page, "_doneDialog.opened")), 5000)
    out["delete_done_title"] = ev(page, "_doneTitle")
    ev(page, "_doneDialog.close(); true")


def quick_item() -> type:
    from PySide6 import QtQuick

    return QtQuick.QQuickItem


def scripts() -> None:
    script = work / "demo_script.py"
    script.write_text("import gremlin\n", encoding="utf-8")
    ev(win, "uiState.setCurrentRoom('scripts'); true")
    wait_until(lambda: bool(ev(win, "_scriptLoader.item !== null")), 5000)
    outer = ev(win, "_scriptLoader.item")
    assert outer is not None, "no Scripts page"
    page = inner(outer)
    out["script_kind"] = ev(page, "_selectScript.kind")
    url = QtCore.QUrl.fromLocalFile(str(script)).toString()
    ev(page, (
        "(function(){var d=_selectScript.prepare();"
        f"d.selectedFile={json.dumps(url)};d.accepted();return true}})()"
    ))
    wait_until(lambda: ev(page, "scriptListModel.rowCount()") == 1, 3000)
    out["script_rows_added"] = ev(page, "scriptListModel.rowCount()")
    out["script_start"] = str(ev(page, "String(_selectScript.prepare().currentFolder)"))
    # The row's trash button, clicked as a click would (its own handler).
    click_js = (
        "(function(){var t=bsi.icons.trash;"
        "function find(it){if(!it)return null;"
        "if(it.text===t&&typeof it.clicked==='function')return it;"
        "var c=it.children||[];"
        "for(var i=0;i<c.length;++i){var f=find(c[i]);if(f)return f}"
        "return null}"
        "_view.forceLayout();var b=find(_view.itemAtIndex(0));if(!b)return false;"
        "b.clicked();return true})()"
    )
    wait_until(lambda: False, 300)

    def click_trash() -> None:
        assert ev(page, click_js), "no trash button"

    click_trash()
    wait_until(lambda: question(win) is not None, 3000)
    out["script_question"] = describe(question(win))
    key(win, QtCore.Qt.Key.Key_Return)
    out["script_enter_closed"] = question(win) is None
    out["script_rows_after_enter"] = ev(page, "scriptListModel.rowCount()")
    click_trash()
    wait_until(lambda: question(win) is not None, 3000)
    dlg = question(win)
    assert dlg is not None, "no question the second time"
    # A click on the red button (its own handler).
    ev(dlg, "_go.clicked(); true")
    wait_until(lambda: ev(page, "scriptListModel.rowCount()") == 0, 3000)
    out["script_rows_after_remove"] = ev(page, "scriptListModel.rowCount()")
    ev(win, "uiState.setCurrentRoom('status'); true")
    wait_until(lambda: False, 300)


def osc() -> None:
    ev(win, "uiState.setCurrentRoom('configuration');"
            " uiState.setCurrentTab('osc'); true")
    split = "_configSplitLoader.item"
    wait_until(lambda: bool(ev(win, f"!!({split} && {split}.oscList)")), 5000)
    page = ev(win, "_configSplitLoader.item.oscList")
    assert page is not None, "no OSC page"
    clear = [
        o for o in page.findChildren(quick_item()) if o.objectName() == "oscClear"
    ]
    assert clear, "no Clear button"
    out["osc_clear_class"] = clear[0].metaObject().className()
    out["osc_clear_text"] = clear[0].property("text")
    QtCore.QMetaObject.invokeMethod(clear[0], "clicked")
    wait_until(lambda: question(win) is not None, 3000)
    out["osc_question"] = describe(question(win))
    key(win, QtCore.Qt.Key.Key_Escape)
    out["osc_esc_closed"] = question(win) is None


def output_view() -> None:
    ev(win, "uiState.setCurrentRoom('status'); true")
    wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")), 5000)
    wait_until(lambda: False, 300)
    home = ev(win, "_statusLoader.item")
    assert home is not None, "no Home"
    home = inner(home)
    ev(home, (
        "(function(){for(var i=0;i<_liveCards.length;++i){var c=_liveCards[i];"
        "if(c&&c.direction==='dest'){openOutputView(pack(c));return true}}"
        "return false})()"
    ))
    wait_until(lambda: bool(ev(win, "_outputLoader.item !== null")), 5000)
    view = ev(win, "_outputLoader.item")
    assert view is not None, "no Output View"
    view = inner(view)
    out["picture_kind"] = ev(view, "_screenImageDlg.kind")
    pic = work / "back.png"
    pic.write_bytes(b"\x89PNG\r\n\x1a\n")
    url = QtCore.QUrl.fromLocalFile(str(pic)).toString()
    ev(view, (
        "(function(){var d=_screenImageDlg.prepare();"
        f"d.selectedFile={json.dumps(url)};d.accepted();return true}})()"
    ))
    out["picture_set"] = ev(view, "screenImage") == url
    out["picture_start"] = str(
        ev(view, "String(_screenImageDlg.prepare().currentFolder)")
    )


for name, fn in (("profiles", profiles), ("delete", delete_device),
                 ("scripts", scripts), ("osc", osc), ("output", output_view)):
    section(name, fn)

out["qml_errors"] = [
    m for m in messages
    if any(
        k in m
        for k in ("Error", "is not a function", "is not defined", "TypeError")
    )
    and any(f in m for f in ("Main.qml", "StatusPage.qml", "ScriptManager.qml",
                             "OscDevice.qml", "OutputModuleView.qml", "confirm"))
][:8]
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)

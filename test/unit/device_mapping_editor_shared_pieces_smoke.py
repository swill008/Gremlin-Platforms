# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor on the shared pieces (01 S140-S143): its message line, its
Undo / Redo through the Edit menu and Ctrl+Z (no bar), the shared delete
question (Reset Layout, Delete Template, the Options Library), the Layers
search box and its file choosers. Loads the window off-screen with
stand-ins, drives it with real key and mouse events and prints
"RESULT name value" lines, then "done".
test_device_mapping_editor_shared_pieces.py runs it in its own process.

    python test/unit/device_mapping_editor_shared_pieces_smoke.py <out_dir>
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest.mock
from pathlib import Path

from smoke_exit import smoke_exit

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))

import gremlin.util  # noqa: E402

# Settings and module files in a folder of their own, never the user's.
gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402
from qt_wait import wait_until  # noqa: E402  # pyright: ignore[reportMissingImports]

Qt = QtCore.Qt

# A QML function finding an item by objectName under another.
_FIND = (
    "function _find(it, name) { if (!it) return null;"
    " if (it.objectName === name) return it;"
    " var kids = it.children || [];"
    " for (var i = 0; i < kids.length; i++) {"
    "   var h = _find(kids[i], name); if (h) return h }"
    " return null }"
)


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    propertyChanged = QtCore.Signal()
    activityChanged = QtCore.Signal()

    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)
    gremlinActive = QtCore.Property(
        bool, fget=lambda self: False, notify=activityChanged
    )
    currentMode = QtCore.Property(
        str, fget=lambda self: "Default", notify=propertyChanged
    )

    @QtCore.Slot(str)
    def noteSave(self, text: str) -> None:
        pass


class FakeUiState(QtCore.QObject):
    modeChanged = QtCore.Signal()
    currentMode = QtCore.Property(str, fget=lambda self: "Default", notify=modeChanged)


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])
    font = QtGui.QFont("Segoe UI")
    font.setPixelSize(15)
    app.setFont(font)
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.device_map_options  # noqa: F401
    import gremlin.ui.device_names  # noqa: F401
    import gremlin.ui.folder_memory  # noqa: F401
    import joystick_gremlin

    joystick_gremlin.register_config_options()

    backend = FakeBackend()
    ui_state = FakeUiState()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.load(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogDeviceMappingEditor.qml"))
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        print("done", flush=True)
        smoke_exit(0)
    win = roots[0]
    win.setProperty("width", 1400)
    win.setProperty("height", 900)
    win.setProperty("visible", True)
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)
    quick.requestActivate()
    wait_until(lambda: quick.isActive(),
               "the window active", 5000, fail=False)

    def js(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, _FIND + "; " + code)
        value = expr.evaluate()
        if expr.hasError():
            return "ERROR " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def click_at(code: str) -> bool:
        """Clicks the middle of the item code gives (window pixels)."""
        where = js(f"(function() {{ var it = {code}; if (!it) return '';"
                   " var p = it.mapToItem(null, it.width / 2, it.height / 2);"
                   " return Math.round(p.x) + ',' + Math.round(p.y) })()")
        if not isinstance(where, str) or "," not in where:
            return False
        x, y = (int(v) for v in where.split(","))
        QtTest.QTest.mouseClick(quick, Qt.MouseButton.LeftButton,
                                Qt.KeyboardModifier.NoModifier, QtCore.QPoint(x, y))
        QtTest.QTest.qWait(250)
        return True

    no_mods = Qt.KeyboardModifier.NoModifier

    def key(k: Qt.Key, mods: Qt.KeyboardModifier = no_mods) -> None:
        QtTest.QTest.keyClick(quick, k, mods)
        QtTest.QTest.qWait(250)

    def question() -> QtCore.QObject | None:
        # An open one: a closed one may be on its way out.
        # Made on the window's root item (Confirm.ask), not the window.
        for q in quick.contentItem().findChildren(QtCore.QObject, "confirmDialog"):
            if shiboken6.isValid(q) and q.property("opened"):
                return q
        return None

    def question_words() -> list | None:
        q = question()
        if q is None or not q.property("opened"):
            return None
        words = []
        for name in ("confirmTitle", "confirmText", "confirmLastLine", "confirmAction"):
            it = q.findChild(QtCore.QObject, name)
            words.append(it.property("text") if it is not None else None)
        return words

    def click_question(name: str) -> None:
        q = question()
        it = q.findChild(QtQuick.QQuickItem, name) if q is not None else None
        if it is None:
            return
        p = it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2))
        QtTest.QTest.mouseClick(quick, Qt.MouseButton.LeftButton,
                                Qt.KeyboardModifier.NoModifier,
                                QtCore.QPoint(round(p.x()), round(p.y())))
        QtTest.QTest.qWait(300)

    # A device, in Edit, with a drawing.
    js("_editorWin.targetGuid = '12345678-1234-1234-1234-123456789abc';"
       " _editorWin.targetName = 'Smoke Stick'; 1")
    wait_until(lambda: js("_editorWin.canEnterEdit"), "the device shown", 5000,
               fail=False)
    js("_editorWin.enterEdit(); 1")
    wait_until(
        lambda: js("_editorWin.editing && _ed() !== null && _ed().seeded"
                   " && !_editorWin._baseWanted"),
        "the edit", 5000, fail=False,
    )
    js("var e = _ed(); e.nodes.push({id: 'b1', kind: 'draw', shape: 'rect',"
       " fx: 0.1, fy: 0.1, fw: 0.1, fh: 0.1}); e.bump(); 1")
    QtTest.QTest.qWait(400)

    # Save says so on the shared message line, no box (07 S20, 01 S142).
    js("_editorWin.saveEdit(true); 1")
    QtTest.QTest.qWait(300)
    result("save-message", js(
        "var m = _messageLine; [m.objectName, m.text, m.failed, m.visible,"
        " _saveGate.opened].join('|')"))

    # Undo / Redo through the Edit menu and Ctrl+Z / Ctrl+Y; the window has
    # no Undo / Redo bar (01 S143, 07 S113).
    js("var e = _ed(); e.nodes.push({id: 'b2', kind: 'draw', shape: 'rect',"
       " fx: 0.4, fy: 0.4, fw: 0.1, fh: 0.1}); e.bump(); 1")
    QtTest.QTest.qWait(600)

    def b2() -> object:
        return js("_ed().nodes.filter(function(n) { return n.id === 'b2' }).length")

    def edit_item(text: str) -> str:
        return ("(function() { for (var i = 0; i < _editMenu.count; i++) {"
                " var it = _editMenu.itemAt(i);"
                f" if (it && it.text === '{text}') return it }} return null }})()")

    before = b2()
    menu_on = js(edit_item("Undo") + ".enabled")
    js(edit_item("Undo") + ".triggered(); 1")
    wait_until(lambda: b2() != before, "the Undo", 5000, fail=False)
    after_menu = b2()
    redo_on = js(edit_item("Redo") + ".enabled")
    key(Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    after_redo = b2()
    key(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    after_ctrl_z = b2()
    result("undo-edit-menu", [menu_on, before, after_menu, redo_on,
                              after_redo, after_ctrl_z])
    result("no-undo-bar", [js("_find(_editorWin, 'deviceMappingEditorUndoBar')"
                              " === null"),
                           js("_find(_editorWin, 'dmePlaneSwitch') === null"),
                           js("typeof _undoBar === 'undefined'")])

    # Reset Layout asks the shared question; Enter cancels, the red button
    # goes ahead (07 S61, 01 S140).
    count = js("_ed().nodes.length")
    js("for (var i = 0; i < _editMenu.count; i++) {"
       " var it = _editMenu.itemAt(i);"
       " if (it && it.text === 'Reset Layout') { it.triggered(); break } } 1")
    wait_until(question, "the Reset Layout question", 5000, fail=False)
    asked = question_words()
    key(Qt.Key.Key_Return)
    after_enter = [question() is None, js("_ed().nodes.length") == count]
    js("_editorWin.askResetLayout(); 1")
    wait_until(question, "the Reset Layout question", 5000, fail=False)
    click_question("confirmAction")
    result("reset", {"asked": asked, "enter": after_enter,
                     "red": js("_ed().nodes.length")})
    js("_ed().undo(); 1")

    # File choosers open in the last folder used for their kind (01 S143).
    pics = out / "pictures"
    pics.mkdir(exist_ok=True)
    folder = QtCore.QUrl.fromLocalFile(str(pics)).toString()
    js("var m = Qt.createQmlObject('import Gremlin.UI; FolderMemory {}', _editorWin);"
       f" m.remember('picture', {json.dumps(folder)}); m.destroy(); 1")
    result("picker", [
        js("_bgPictureDialog.kind"), js("_overlayDialog.kind"),
        js("_exportPngDialog.kind + ' ' + _exportPngDialog.mode"),
        js("_templateImportFile.kind"),
        str(js("String(_bgPictureDialog.prepare().currentFolder)")).rstrip("/").lower()
        == folder.rstrip("/").lower(),
    ])

    # The Layers search is the shared box: Ctrl+F goes to it, Esc clears it.
    key(Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    wait_until(lambda: js("_layersPanel.searchHasFocus()"), "the search focus",
               5000, fail=False)
    focused = js("_layersPanel.searchHasFocus()")
    for k in (Qt.Key.Key_R, Qt.Key.Key_E, Qt.Key.Key_C, Qt.Key.Key_T):
        QtTest.QTest.keyClick(quick, k)
    wait_until(lambda: js("_layersPanel.searchText") == "rect", "the typed search",
               5000, fail=False)
    typed = js("_layersPanel.searchText")
    key(Qt.Key.Key_Escape)
    result("layers-search", [focused, typed, js("_layersPanel.searchText"),
                             js("_layersPanel.clearButton().objectName"),
                             js("_find(_layersPanel, 'layersSearch')"
                                ".field.objectName")])
    js("_editorWin.discardEdit(); 1")
    wait_until(lambda: not js("_editorWin.editing"), "the edit discarded", 5000,
               fail=False)

    # Templates: Delete is the red button; Esc cancels, the red one deletes.
    js("_hw.saveTemplate('Smoke T', JSON.stringify([{id: 'x', kind: 'draw',"
       " shape: 'rect', fx: 0.1, fy: 0.1, fw: 0.1, fh: 0.1}]), 'Smoke Stick');"
       " _templatesDlg.open(); 1")
    wait_until(lambda: js("_templatesDlg.opened"), "the Templates box", 5000,
               fail=False)
    names = "_hw.templates().map(function(t) { return t.name }).join(',')"
    button = "_find(_templatesDlg.contentItem, 'templateDelete')"
    red = js(f"String({button}).indexOf('DangerButton') === 0")
    click_at(button)
    asked = question_words()
    key(Qt.Key.Key_Escape)
    kept = [question() is None, js(names)]
    click_at(button)
    click_question("confirmAction")
    result("template-delete", {"red": red, "asked": asked, "esc": kept,
                               "deleted": js(names)})
    js("_templatesDlg.close(); 1")
    wait_until(lambda: not js("_templatesDlg.visible"), "the Templates box closed",
               5000, fail=False)

    # Options › Library: the same question and red button.
    js("_hw.saveTemplate('Lib T', JSON.stringify([{id: 'y', kind: 'draw',"
       " shape: 'rect', fx: 0.1, fy: 0.1, fw: 0.1, fh: 0.1}]), 'Smoke Stick'); 1")
    js("var c = Qt.createComponent('OptionDeviceMapLibrary.qml');"
       " var lib = c.createObject(_editorWin.contentItem, {x: 20, y: 120, width: 600});"
       " lib.objectName = 'smokeLibrary'; lib.refreshTemplates(); 1")
    wait_until(
        lambda: js("_find(_find(_editorWin.contentItem, 'smokeLibrary'),"
                   " 'templateDelete') !== null"),
        "the Library's Delete button", 5000, fail=False,
    )
    lib = "_find(_editorWin.contentItem, 'smokeLibrary')"
    button = f"_find({lib}, 'templateDelete')"
    red = js(f"String({button}).indexOf('DangerButton') === 0")
    click_at(button)
    asked = question_words()
    key(Qt.Key.Key_Return)
    kept = [question() is None, js(names)]
    click_at(button)
    click_question("confirmAction")
    result("library-delete", {"red": red, "asked": asked, "enter": kept,
                              "deleted": js(names),
                              "heading": js(f"_find({lib}, 'templatesHeading')"
                                            " !== null")})

    for warning in warnings:
        print("WARN " + warning.encode("ascii", "replace").decode(), flush=True)
    print("done", flush=True)
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

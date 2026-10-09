# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S53-S55 (D-10-UNDO-REDO): runs the real Device Library window off-screen
over the stand-in Library of library_builtin_section_smoke.py (sticks plus
Keyboard and OSC), with the model's Undo/Redo (undoText, redoText, undo(),
redo()) standing in so the window's side is seen on its own: Edit's Undo and
Redo items and their keys, the Undo / Redo buttons beside the right-click
menu's title, the message line's Undo link after Remove, and the Delete key.
Keys and clicks are real Qt events. test_library_undo_ui.py runs it.

    python test/unit/library_undo_ui_smoke.py <out_dir>
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "library_builtin_section_smoke", _HERE / "library_builtin_section_smoke.py"
)
assert _spec and _spec.loader
builtin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builtin)
menus = builtin.menus

from PySide6 import QtCore  # noqa: E402

import gremlin.ui.device_library_model as dlm  # noqa: E402

_REAL = dlm.DeviceLibraryModel
_CALLS: list[str] = []


class UndoStandIn(_REAL):
    """The real model with its Undo/Redo steps standing in (the contract's
    names): the texts are set by the steps, undo()/redo() are recorded."""

    undoStepsChanged = QtCore.Signal()

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._undo_text = ""
        self._redo_text = ""

    def _get_undo_text(self) -> str:
        return self._undo_text

    def _get_redo_text(self) -> str:
        return self._redo_text

    undoText = QtCore.Property(str, fget=_get_undo_text, notify=undoStepsChanged)
    redoText = QtCore.Property(str, fget=_get_redo_text, notify=undoStepsChanged)

    @QtCore.Slot(str, str)
    def setSteps(self, undo: str, redo: str) -> None:
        self._undo_text = undo
        self._redo_text = redo
        self.undoStepsChanged.emit()
        # QML follows the real model's notify signal for these names.
        for name in ("changed", "stepsChanged", "undoChanged", "undoTextChanged"):
            signal = getattr(self, name, None)
            if isinstance(signal, QtCore.SignalInstance):
                signal.emit()

    @QtCore.Slot()
    def undo(self) -> None:
        _CALLS.append("undo")

    @QtCore.Slot()
    def redo(self) -> None:
        _CALLS.append("redo")

    @QtCore.Slot(result=str)
    def stepCalls(self) -> str:
        return json.dumps(_CALLS)


dlm.DeviceLibraryModel = UndoStandIn
menus._KEYS.update(
    {
        "ctrl+z": (QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier),
        "ctrl+y": (QtCore.Qt.Key.Key_Y, QtCore.Qt.KeyboardModifier.ControlModifier),
        "delete": (QtCore.Qt.Key.Key_Delete, QtCore.Qt.KeyboardModifier.NoModifier),
    }
)

_EDIT = (
    "JSON.stringify((function() { _editMenu.open(); var d = _editMenu.describe();"
    " _editMenu.close(); return d })())"
)
_CALLS_JS = "JSON.parse(deviceLibrary.stepCalls())"
_UNDO = "Undo Remove HID Remapper ACHB"
_REDO = "Redo Copy to Another Stick"
_DLG = (
    "JSON.stringify({open: !!_lib.asking,"
    " title: _lib.asking ? _lib.asking.titleText : ''})"
)
_IDLE = "!deviceLibrary.busy"


def _del_key(select: str, focus: str = "_list") -> str:
    return (
        "(_lib.asking && _lib.asking.cancel()); deviceLibrary.setAllOpen(true);"
        f" deviceLibrary.select('{select}'); {focus}.forceActiveFocus();"
        " _bridge.key('delete')"
    )


menus.STEPS = [
    ("edit-none", "deviceLibrary.setSteps('', '')", "!deviceLibrary.busy", _EDIT),
    ("edit-undo", f"deviceLibrary.setSteps('{_UNDO}', '')", _IDLE, _EDIT),
    ("edit-both", f"deviceLibrary.setSteps('{_UNDO}', '{_REDO}')", _IDLE, _EDIT),
    (
        "keys",
        "deviceLibrary.select('dev-00000001'); _list.forceActiveFocus();"
        " _bridge.key('ctrl+z'); _bridge.key('ctrl+y')",
        "",
        "deviceLibrary.stepCalls()",
    ),
    (
        "keys-in-search",
        "_search.focusField(); _bridge.key('ctrl+z'); _bridge.key('ctrl+y')",
        "",
        "deviceLibrary.stepCalls()",
    ),
    (
        "header",
        "_list.forceActiveFocus();"
        " _bridge.click('libraryRow_dev-00000001', 'right', '')",
        "_rowMenu.opened",
        "JSON.stringify({title: _rowMenu.model.title, header:"
        " _rowMenu.model.header.map(h => [h.label, h.enabled])})",
    ),
    (
        "header-run",
        "_rowMenu.model.header[0].run(); _rowMenu.model.header[1].run();"
        " _rowMenu.close()",
        "",
        "deviceLibrary.stepCalls()",
    ),
    (
        "header-none",
        "deviceLibrary.setSteps('', '');"
        " _bridge.click('libraryRow_dev-0000000b', 'right', '')",
        "_rowMenu.opened",
        "JSON.stringify(_rowMenu.model.header.map(h => [h.label, h.enabled]))",
    ),
    (
        "del-key-setup",
        "_rowMenu.close();" + _del_key("set-00000001"),
        "!!_lib.asking",
        _DLG,
    ),
    ("del-key-not-connected", _del_key("dev-00000004"), "!!_lib.asking", _DLG),
    ("del-key-connected", _del_key("dev-00000001"), "", _DLG),
    ("del-key-builtin", _del_key("dev-0000000b"), "", _DLG),
    ("del-key-in-search", _del_key("set-00000001", "_search.field"), "", _DLG),
    (
        "remove-link",
        "(_lib.asking && _lib.asking.cancel());"
        " deviceLibrary.setSteps('Undo Remove Old stick', '');"
        " _bridge.click('libraryRow_dev-00000003', 'right', '');"
        " _rowMenu.activate('Remove from Library…'); _lib.asking.accept()",
        "!deviceLibrary.busy && deviceLibrary.rows.every(r => r.key !== 'dev-00000003')"
        " && _lib.message.length > 0",
        "JSON.stringify({message: _lib.message,"
        " link: _bridge.item('messageUndo') !== null"
        " && _bridge.item('messageUndo').visible})",
    ),
    (
        "remove-link-click",
        "_bridge.clickIn('messageUndo', 'left', -1, -1)",
        "",
        "JSON.stringify({calls: " + _CALLS_JS + ", link:"
        " _bridge.item('messageUndo').visible})",
    ),
    (
        "export-no-link",
        "deviceLibrary.exportCurrent('dev-00000001', 'file:///C:/x/Left%20throttle')",
        "!deviceLibrary.busy && _lib.message.indexOf('Current setup exported') === 0",
        "_bridge.item('messageUndo').visible",
    ),
]
# S53a (D-10-STATUS-LAST): Edit's tooltips and the status bar's last change.
_TIPS = (
    "JSON.stringify({items: (function() { _editMenu.open();"
    " var d = _editMenu.describe(); _editMenu.close(); return d })(),"
    " undo: _undoItem.ToolTip.text, redo: _redoItem.ToolTip.text})"
)
_LAST = (
    "(function() { var l = _bridge.item('undoBarText');"
    " return JSON.stringify({text: l.text, shown: l.visible,"
    " cut: l.truncated, width: l.width,"
    " full: l.implicitWidth, tip: l.ToolTip.text,"
    " tipShown: l.ToolTip.toolTip.visible"
    " && l.ToolTip.toolTip.text === l.text}) })()"
)
_Z = "_list.forceActiveFocus(); _bridge.key('ctrl+z'); "
_Y = "_list.forceActiveFocus(); _bridge.key('ctrl+y'); "
_LONG = "Copy to Another Stick" + " with a very long name" * 12
menus.STEPS += [
    ("edit-tips", f"deviceLibrary.setSteps('{_UNDO}', '{_REDO}')", _IDLE, _TIPS),
    ("status-none", "deviceLibrary.setSteps('', '')", _IDLE, _LAST),
    ("status-change", f"deviceLibrary.setSteps('{_UNDO}', '')", _IDLE, _LAST),
    (
        "status-undone",
        _Z + "deviceLibrary.setSteps('Undo Rename Left throttle',"
        " 'Redo Remove HID Remapper ACHB')",
        _IDLE,
        _LAST,
    ),
    (
        "status-undone-older",
        _Z + "deviceLibrary.setSteps('', 'Redo Rename Left throttle')",
        _IDLE,
        _LAST,
    ),
    (
        "status-redone",
        _Y + "deviceLibrary.setSteps('Undo Rename Left throttle',"
        " 'Redo Remove HID Remapper ACHB')",
        _IDLE,
        _LAST,
    ),
    (
        "status-new-after-undo",
        _Z + "deviceLibrary.setSteps('', 'Redo Rename Left throttle');"
        " deviceLibrary.setSteps('Undo Rename Right stick', '')",
        _IDLE,
        _LAST,
    ),
    (
        "status-long",
        f"deviceLibrary.setSteps('Undo {_LONG}', '');"
        " _bridge.hover('undoBarText')",
        "_bridge.item('undoBarText').ToolTip.toolTip.visible",
        _LAST,
    ),
]
menus.SHOTS = {
    "header": "undo_header",
    "remove-link": "undo_link",
    "status-long": "status_last_long",
}

if __name__ == "__main__":
    sys.argv = sys.argv[:2]
    menus.main()

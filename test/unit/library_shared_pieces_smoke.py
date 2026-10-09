# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S140-S143 in the Device Library: runs the real window off-screen over
the stand-in Library of device_library_CU_menus_smoke.py and checks it uses
the shared pieces: the delete question (Confirm.ask; Enter cancels, a click
on the red button goes ahead), the red Delete button, the search box (Ctrl+F,
"Nothing matches", Esc clears), the message line, the Undo / Redo bar, Tidy's
Remove… asking the shared question, and the Device Pack chooser opening in
the remembered folder (set up, never shown). Keys and clicks are real Qt
events. test_library_shared_pieces.py runs it.

    python test/unit/library_shared_pieces_smoke.py <out_dir>
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "device_library_CU_menus_smoke", _HERE / "device_library_CU_menus_smoke.py"
)
assert _spec and _spec.loader
menus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(menus)

from PySide6 import QtCore  # noqa: E402

menus._KEYS.update(
    {
        "return": (QtCore.Qt.Key.Key_Return, QtCore.Qt.KeyboardModifier.NoModifier),
        "escape": (QtCore.Qt.Key.Key_Escape, QtCore.Qt.KeyboardModifier.NoModifier),
        "ctrl+f": (QtCore.Qt.Key.Key_F, QtCore.Qt.KeyboardModifier.ControlModifier),
    }
)

_Q = "(_bridge.item('confirmDialog') !== null && _bridge.item('confirmDialog').opened)"
_NO_Q = (
    "(_bridge.item('confirmDialog') === null || !_bridge.item('confirmDialog').opened)"
)
_ASKED = (
    "JSON.stringify({open: " + _Q + ", title: _bridge.item('confirmTitle').text,"
    " text: _bridge.item('confirmText').text,"
    " last: _bridge.item('confirmLastLine').text,"
    " action: _bridge.item('confirmAction').text,"
    " cancelFocus: _bridge.item('confirmCancel').activeFocus})"
)
_HAS = "(function(n) { return _bridge.item(n) !== null })"
# A real folder (only existing folders are remembered).
_FOLDER = QtCore.QUrl.fromLocalFile(tempfile.mkdtemp(prefix="packs_")).toString()

menus.STEPS = [
    (
        "delete-ask",
        "deviceLibrary.setAllOpen(true); deviceLibrary.select('set-00000001');"
        " _lib.askDelete()",
        _Q,
        _ASKED,
    ),
    (
        "delete-enter",
        "_bridge.key('return')",
        _NO_Q,
        "JSON.stringify({open: " + _Q + ","
        " still: deviceLibrary.rows.some(r => r.key === 'set-00000001')})",
    ),
    (
        "delete-click",
        "deviceLibrary.select('set-00000001'); _lib.askDelete()",
        _Q,
        "",
    ),
    (
        "delete-click-go",
        "_bridge.clickIn('confirmAction', 'left', -1, -1)",
        "!deviceLibrary.busy"
        " && deviceLibrary.rows.every(r => r.key !== 'set-00000001')",
        "JSON.stringify({open: " + _Q + ", message: _lib.message,"
        " line: " + _HAS + "('messageText'),"
        " link: _bridge.item('messageUndo') !== null})",
    ),
    (
        "delete-button",
        "deviceLibrary.select('set-00000002')",
        "",
        "JSON.stringify({red: Qt.colorEqual(_bridge.item('libraryDeleteButton')"
        ".background.color, Style.danger),"
        " text: _bridge.item('libraryDeleteButton').text})",
    ),
    (
        "search-ctrl-f",
        "_list.forceActiveFocus(); _bridge.key('ctrl+f')",
        "",
        "JSON.stringify({field: " + _HAS + "('searchField'),"
        " focus: _bridge.item('searchField') !== null"
        " && _bridge.item('searchField').activeFocus})",
    ),
    (
        "search-none",
        "_search.text = 'zzzz-nothing'",
        "",
        "JSON.stringify({count: _bridge.item('searchCount').text,"
        " shown: _bridge.item('searchCount').visible,"
        " empty: _bridge.item('libraryEmpty').visible})",
    ),
    (
        "search-esc",
        "_bridge.key('escape')",
        "",
        "JSON.stringify({text: _search.text,"
        " focus: _bridge.item('searchField').activeFocus})",
    ),
    (
        "message-failed",
        "_lib.showMessage('That did not work.', true)",
        "",
        "JSON.stringify({failed: _bridge.item('libraryMessage').failed === true,"
        " text: _bridge.item('messageText').text})",
    ),
    (
        "undo-bar",
        "''",
        "",
        "JSON.stringify({undo: " + _HAS + "('undoBarUndo'),"
        " redo: " + _HAS + "('undoBarRedo')})",
    ),
    (
        "tidy-ask",
        "_tidyDlg.openNow()",
        "_tidyDlg.opened",
        "JSON.stringify({open: _tidyDlg.opened, question: " + _Q + ","
        " remove: _bridge.item('libraryTidyRemove').text,"
        " cancelFocus: _bridge.item('libraryTidyCancel').activeFocus})",
    ),
    (
        "tidy-enter",
        "_bridge.key('return')",
        "!_tidyDlg.opened",
        "JSON.stringify({tidyOpen: _tidyDlg.opened, message: _lib.message})",
    ),
    (
        "tidy-go-click",
        "_tidyDlg.openNow(); _bridge.clickIn('libraryTidyRemove', 'left', -1, -1)",
        "!deviceLibrary.busy && _lib.message.indexOf('tidied') >= 0",
        "JSON.stringify({tidyOpen: _tidyDlg.opened, question: " + _Q + ","
        " message: _lib.message})",
    ),
    (
        "picker",
        "Qt.createQmlObject('import Gremlin.UI; FolderMemory {}', _lib)"
        ".remember('device-pack', '" + _FOLDER + "');"
        " deviceLibrary.select('set-00000002');"
        " _exportFile.currentFile = _lib._packName();"
        " var d = _importFile.prepare(); var e = _exportFile.prepare();"
        " JSON.stringify({want: '" + _FOLDER + "', open: String(d.currentFolder),"
        " save: String(e.selectedFile), shown: d.visible || e.visible})",
        "",
        "",
    ),
]
menus.SHOTS = {"delete-ask": "library_confirm", "tidy-ask": "library_tidy"}

if __name__ == "__main__":
    sys.argv = sys.argv[:2]
    menus.main()

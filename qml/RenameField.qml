// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Style

// The one inline Rename box (01 S135, D-01-ONE-RENAME). The owner sets
// name and opens it (open = true or start()); it shows the name selected
// with the cursor in it. Enter or leaving it (a click away, Esc's leave,
// 01 S134) saves once; its own Esc cancels. An empty or unchanged name
// isn't saved. A name the owner can't take is refused in its renamed
// handler. ended() follows every edit, with open already false.
JGTextField {
    id: _root

    property string name: ""
    property bool open: false

    signal renamed(string newName)
    signal ended()

    function start() { open = true }

    // True from opening until the edit ends; the guard that keeps a
    // save to at most one per edit and none after a cancel.
    property bool _editing: false

    visible: open
    selectByMouse: true

    function _focus() {
        forceActiveFocus()
        selectAll()
    }

    function _finish(save) {
        if (!_editing)
            return
        _editing = false
        var newName = text.trim()
        if (save && newName.length > 0 && newName !== name)
            renamed(newName)
        open = false
        ended()
    }

    onOpenChanged: {
        if (open) {
            _editing = true
            text = name
            _focus()
        } else {
            // Closed by the owner mid-edit: nothing is saved.
            _finish(false)
        }
    }
    // The focus can't land while hidden; take it when shown.
    onVisibleChanged: if (visible && _editing) _focus()
    onAccepted: _finish(true)
    onActiveFocusChanged: if (!activeFocus) _finish(true)
    Keys.onEscapePressed: (event) => { _finish(false); event.accepted = true }
}

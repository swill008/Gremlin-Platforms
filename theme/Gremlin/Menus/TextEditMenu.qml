// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

// A text box's right-click menu in the program's style: only the edits that
// can be made now (nothing to paste, no Paste; read-only, no Cut).
// The control style sets it on every TextField, TextArea, SpinBox and
// editable ComboBox.
ThemedMenu {
    id: control

    // The TextInput or TextEdit it edits.
    property Item editor: null

    readonly property bool _writable: !!editor && !editor.readOnly
    readonly property bool _selected: !!editor && editor.selectedText.length > 0

    ThemedMenuItem {
        text: qsTr("Undo")
        hint: "Ctrl+Z"
        enabled: control._writable && control.editor.canUndo
        onTriggered: control.editor.undo()
    }
    ThemedMenuItem {
        text: qsTr("Redo")
        hint: "Ctrl+Y"
        enabled: control._writable && control.editor.canRedo
        onTriggered: control.editor.redo()
    }
    ThemedMenuSeparator {}
    ThemedMenuItem {
        text: qsTr("Cut")
        hint: "Ctrl+X"
        enabled: control._writable && control._selected
        onTriggered: control.editor.cut()
    }
    ThemedMenuItem {
        text: qsTr("Copy")
        hint: "Ctrl+C"
        enabled: control._selected
        onTriggered: control.editor.copy()
    }
    ThemedMenuItem {
        text: qsTr("Paste")
        hint: "Ctrl+V"
        enabled: control._writable && control.editor.canPaste
        onTriggered: control.editor.paste()
    }
    ThemedMenuItem {
        text: qsTr("Delete")
        enabled: control._writable && control._selected
        onTriggered: control.editor.remove(control.editor.selectionStart, control.editor.selectionEnd)
    }
    ThemedMenuSeparator {}
    ThemedMenuItem {
        text: qsTr("Select All")
        hint: "Ctrl+A"
        enabled: !!control.editor && control.editor.length > 0
                 && control.editor.selectedText.length < control.editor.length
        onTriggered: control.editor.selectAll()
    }
}

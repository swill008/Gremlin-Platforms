// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// 01 S143 (D-01-SHARED-PIECES): the Undo / Redo pair with the last change
// beside it, as the Device Library's status bar (10 S53a, D-10-STATUS-LAST).
// The window keeps its own Ctrl+Z / Ctrl+Y shortcuts.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

RowLayout {
    id: _root

    property bool canUndo: false
    property bool canRedo: false
    // The change each button puts back or redoes, shown as its tooltip.
    property string undoTip: ""
    property string redoTip: ""
    // "Last change: X"; "Undone: X" wins while set (the newest step was an Undo).
    property string lastChange: ""
    property string undone: ""

    readonly property string shownText: undone.length ? undone : lastChange

    signal undo()
    signal redo()

    spacing: Style.dp(6)

    Button {
        id: _undo
        objectName: "undoBarUndo"
        text: "Undo"
        flat: true
        enabled: _root.canUndo
        font.pixelSize: Style.dp(12)
        implicitHeight: Style.dp(24)
        onClicked: _root.undo()
        // A HoverHandler, as the Library's status bar: hovered isn't set
        // everywhere (off-screen, touch).
        HoverHandler { id: _undoHover }
        ToolTip.visible: _undoHover.hovered && _root.undoTip.length > 0
        ToolTip.text: _root.undoTip
    }

    Button {
        id: _redo
        objectName: "undoBarRedo"
        text: "Redo"
        flat: true
        enabled: _root.canRedo
        font.pixelSize: Style.dp(12)
        implicitHeight: Style.dp(24)
        onClicked: _root.redo()
        // A HoverHandler, as the Library's status bar: hovered isn't set
        // everywhere (off-screen, touch).
        HoverHandler { id: _redoHover }
        ToolTip.visible: _redoHover.hovered && _root.redoTip.length > 0
        ToolTip.text: _root.redoTip
    }

    Label {
        id: _text
        objectName: "undoBarText"
        Layout.fillWidth: true
        visible: text.length > 0
        text: _root.shownText
        elide: Text.ElideRight
        font.pixelSize: Style.dp(12)
        color: Style.fgSoft
        HoverHandler { id: _textHover }
        ToolTip.visible: _textHover.hovered && _text.truncated
        ToolTip.text: text
    }
}

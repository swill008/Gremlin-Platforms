// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T

import Gremlin.Style
import "commands.js" as Commands

// The command palette: a search box over every command the program has
// (commands.js) that can be used now. Type part of a name, Up/Down to move,
// Enter to run, Esc to close.
T.Popup {
    id: _palette

    property var results: []
    property int pick: 0
    // Only these owners' commands (a window's own); all when empty.
    property var owners: []
    // Called as it opens, before listing: a window defines its commands.
    property var beforeOpen: null
    // Pinned (a tool row's pin): stays open after a command and when the
    // window is clicked; Esc closes it.
    property bool keepOpen: false

    parent: T.Overlay.overlay
    modal: !keepOpen
    focus: true
    closePolicy: keepOpen ? T.Popup.CloseOnEscape : (T.Popup.CloseOnEscape | T.Popup.CloseOnPressOutside)
    width: Math.min(Style.dp(520), parent ? parent.width - Style.dp(32) : Style.dp(520))
    height: contentItem.implicitHeight + topPadding + bottomPadding
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round(parent.height * 0.12) : 0
    padding: Style.menuPad

    background: MenuSurface {}
    T.Overlay.modal: Rectangle { color: Style.dim }

    function search(text) {
        results = Commands.search(text, owners)
        pick = results.length ? 0 : -1
        _list.positionViewAtBeginning()
    }

    function runPick(i) {
        var c = results[i]
        if (!c || !Commands.isAvailable(c.id))
            return
        if (keepOpen) {
            c.run()
            return
        }
        close()
        // After the palette has closed, so a dialog it opens gets the focus.
        // Runs the command it holds: closing may take the window's commands
        // out of the list (a Button Map's onClosed).
        Qt.callLater(function() { c.run() })
    }

    // Names listed now, for tests.
    function describe() {
        return results.map(function(c) { return c.text })
    }

    onAboutToShow: {
        if (typeof beforeOpen === "function")
            beforeOpen()
        _field.text = ""
        search("")
    }
    onOpened: _field.forceActiveFocus()

    contentItem: Column {
        spacing: 0

        Item {
            id: _fieldBox
            width: parent.width
            height: Style.menuRowH + Style.dp(12)
            T.TextField {
                id: _field
                anchors.fill: parent
                anchors.margins: Style.dp(4)
                leftPadding: Style.dp(10)
                rightPadding: Style.dp(10)
                font.pixelSize: Style.menuTextPx + Style.dp(1)
                color: Style.menuText
                selectionColor: Style.menuAccent
                selectedTextColor: Style.onColor
                verticalAlignment: Text.AlignVCenter
                background: Rectangle {
                    color: Style.bgWell
                    radius: Style.dp(4)
                    border.color: Style.menuAccent
                }
                onTextChanged: _palette.search(text)
                Text {
                    visible: !_field.text.length
                    anchors.verticalCenter: parent.verticalCenter
                    x: _field.leftPadding
                    text: "Type a command"
                    font.pixelSize: Style.menuTextPx + Style.dp(1)
                    color: Style.menuHint
                }
                Keys.onPressed: (e) => {
                    var n = _palette.results.length
                    if (e.key === Qt.Key_Down && n) {
                        _palette.pick = (_palette.pick + 1) % n
                    } else if (e.key === Qt.Key_Up && n) {
                        _palette.pick = (_palette.pick - 1 + n) % n
                    } else if (e.key === Qt.Key_Return || e.key === Qt.Key_Enter) {
                        _palette.runPick(_palette.pick)
                    } else {
                        return
                    }
                    _list.positionViewAtIndex(_palette.pick, ListView.Contain)
                    e.accepted = true
                }
            }
        }

        ListView {
            id: _list
            width: parent.width
            height: Math.min(contentHeight, Style.menuRowH * 14)
            clip: true
            model: _palette.results
            boundsBehavior: Flickable.StopAtBounds
            delegate: MenuRowBackground {
                id: _row
                required property var modelData
                required property int index
                width: _list.width
                height: Style.menuRowH + Style.dp(2)
                hot: _palette.pick === index
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    x: Style.dp(10)
                    width: parent.width - x - _group.width - Style.dp(20)
                    text: _row.modelData.text
                    font.pixelSize: Style.menuTextPx
                    color: Style.menuText
                    elide: Text.ElideRight
                }
                // Where it lives in the menus, and its shortcut.
                Text {
                    id: _group
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: Style.dp(10)
                    text: [_row.modelData.group || "", _row.modelData.shortcut || ""].filter(Boolean).join("   ")
                    font.pixelSize: Style.menuTextPx - Style.dp(1)
                    color: Style.menuHint
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onPositionChanged: _palette.pick = _row.index
                    onClicked: _palette.runPick(_row.index)
                }
            }
        }

        Text {
            visible: !_palette.results.length
            width: parent.width
            height: visible ? Style.menuRowH + Style.dp(4) : 0
            leftPadding: Style.dp(10)
            verticalAlignment: Text.AlignVCenter
            text: "No command matches"
            font.pixelSize: Style.menuTextPx
            color: Style.menuHint
        }
    }
}

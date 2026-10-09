// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The shared search box (01 S141, D-01-SEARCH-BOX): Ctrl+F in its window
// goes to it, × clears it, Esc clears it and leaves the box (01 S134; the
// leaving is done by gremlin.ui.leave_text), and a line under it says
// "N found" or "Nothing matches". The caller does the searching: it reads
// text and sets count (or countText for its own wording).

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

Item {
    id: _box

    property alias text: _field.text
    property alias placeholder: _field.placeholderText
    // -1: no line; 0 or more: "N found" / "Nothing matches" while text isn't blank.
    property int count: -1
    // Replaces the line's words when set (shown while text isn't blank).
    property string countText: ""
    // Ctrl+F anywhere in the window goes to the box. Turn it off where the
    // window has its own Ctrl+F or more than one search box.
    property bool findShortcut: true
    // The text field itself, for a caller's font or height.
    readonly property alias field: _field

    signal accepted()
    signal cleared()

    function focusField() {
        _field.forceActiveFocus(Qt.ShortcutFocusReason)
        _field.selectAll()
    }

    function clear() {
        if (_field.text === "")
            return
        _field.text = ""
        _box.cleared()
    }

    readonly property bool _lineShown: _field.text.trim() !== ""
        && (_box.countText !== "" || _box.count >= 0)

    implicitHeight: _column.implicitHeight
    implicitWidth: _column.implicitWidth

    Shortcut {
        sequences: [StandardKey.Find]
        context: Qt.WindowShortcut
        enabled: _box.findShortcut && _box.visible && _box.enabled
        onActivated: _box.focusField()
    }

    ColumnLayout {
        id: _column
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Style.dp(4)

        JGTextField {
            id: _field
            objectName: "searchField"
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(28)
            placeholderText: "Search…"
            selectByMouse: true
            leftPadding: Style.dp(6)
            rightPadding: Style.dp(24)
            topPadding: 0
            bottomPadding: 0
            verticalAlignment: TextInput.AlignVCenter

            onAccepted: _box.accepted()
            // Esc clears the search; the program then leaves the box (01 S134).
            Keys.onEscapePressed: (event) => {
                _box.clear()
                event.accepted = true
            }

            Label {
                objectName: "searchClear"
                anchors.right: parent.right
                anchors.rightMargin: Style.dp(6)
                anchors.verticalCenter: parent.verticalCenter
                visible: _field.text !== ""
                text: "×"
                font.pixelSize: Style.dp(16)
                color: _clearArea.containsMouse ? Style.fgStrong : Style.fgMuted
                ToolTip.visible: _clearArea.containsMouse
                ToolTip.text: "Clear the search (Esc)"
                MouseArea {
                    id: _clearArea
                    anchors.fill: parent
                    anchors.margins: -Style.dp(4)
                    hoverEnabled: true
                    cursorShape: Qt.ArrowCursor
                    onClicked: _box.clear()
                }
            }
        }

        Label {
            objectName: "searchCount"
            Layout.fillWidth: true
            elide: Text.ElideRight
            visible: _box._lineShown
            color: _box.countText === "" && _box.count === 0 ? Style.fgMuted : Style.fgSoft
            text: _box.countText !== "" ? _box.countText
                : _box.count === 0 ? "Nothing matches"
                : _box.count + " found"
        }
    }
}

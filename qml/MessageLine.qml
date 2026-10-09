// -*- coding: utf-8; -*-
//
// SPDX-License-Identifier: GPL-3.0-only

// The shared message line (01 S142, D-01-MESSAGE-LINE), taken from the
// Device Library's: what just happened, plain for done, red for failed, with
// an Undo link where the change can be taken back. A message stays until the
// next show() or clear() (or its × is clicked).
//
//   MessageLine { id: _message; Layout.fillWidth: true }
//   _message.show("Deleted.", false, "Undo", function() { lib.undo() })

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

Rectangle {
    id: _root
    objectName: "messageLine"

    readonly property string text: _state.text
    readonly property bool failed: _state.failed
    readonly property string undoText: _state.undoText
    // While true the Undo link is hidden (e.g. the window is busy).
    property bool busy: false

    function show(text, failed, undoText, onUndo) {
        _state.text = text === undefined || text === null ? "" : String(text)
        _state.failed = failed === true
        _state.undoText = undoText ? String(undoText) : ""
        _state.onUndo = typeof onUndo === "function" ? onUndo : null
    }

    function clear() {
        show("")
    }

    QtObject {
        id: _state
        property string text: ""
        property bool failed: false
        property string undoText: ""
        property var onUndo: null
    }

    visible: _state.text.length > 0
    implicitHeight: visible ? _label.implicitHeight + Style.dp(12) : 0
    color: _state.failed ? Style.alpha(Style.danger, 0.18) : Style.bgRaised

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Style.dp(12)
        anchors.rightMargin: Style.dp(6)
        Label {
            id: _label
            objectName: "messageText"
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: _state.text
            color: _state.failed ? Style.dangerText : Style.fg
        }
        Label {
            objectName: "messageUndo"
            visible: _state.undoText.length > 0 && _state.onUndo !== null && !_root.busy
            text: _state.undoText
            font.underline: true
            color: Style.accent
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    // Once: the link goes so a second click can't undo twice.
                    let run = _state.onUndo
                    _state.onUndo = null
                    if (run)
                        run()
                }
            }
        }
        ToolButton {
            objectName: "messageClose"
            text: ""
            font.family: Style.iconFont
            onClicked: _root.clear()
        }
    }
}

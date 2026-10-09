// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// 01 S140: the one question asked before every delete, remove or clear.
// Opened through confirm.js (Confirm.ask), which makes one per question.
// Cancel has the focus; Enter and Esc both cancel, so only a click (or
// Space) on the red button goes ahead.
Popup {
    id: _root

    objectName: "confirmDialog"

    property string titleText: ""
    property string bodyText: ""
    property bool undoable: false
    property string note: ""
    property string actionText: ""

    // Exactly one of these, once, after the question closes.
    signal confirmed()
    signal cancelled()

    readonly property string lastLine: note.length > 0 ? note
        : undoable ? "You can restore it from Tools › History." : "This can't be undone."

    property bool _accepted: false

    function accept() {
        _accepted = true
        close()
    }

    function cancel() {
        close()
    }

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    padding: Style.dp(16)
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    width: parent ? Math.min(parent.width - Style.dp(40), Style.dp(460)) : Style.dp(460)

    onOpened: _cancel.forceActiveFocus()
    onClosed: {
        if (_accepted)
            confirmed()
        else
            cancelled()
    }

    background: Rectangle {
        color: Style.background
        border.color: Style.danger
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(12)

        // Enter anywhere in the question cancels (the buttons take theirs first).
        Keys.onReturnPressed: _root.cancel()
        Keys.onEnterPressed: _root.cancel()

        Label {
            objectName: "confirmTitle"
            Layout.fillWidth: true
            text: _root.titleText
            font.bold: true
            font.pixelSize: Style.dp(16)
            wrapMode: Text.Wrap
            color: Style.fg
        }

        Label {
            objectName: "confirmText"
            Layout.fillWidth: true
            visible: text.length > 0
            text: _root.bodyText
            wrapMode: Text.Wrap
            color: Style.fg
        }

        Label {
            objectName: "confirmLastLine"
            Layout.fillWidth: true
            text: _root.lastLine
            wrapMode: Text.Wrap
            color: Style.fg
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Style.dp(8)

            DangerButton {
                id: _go
                objectName: "confirmAction"
                text: _root.actionText
                onClicked: _root.accept()
                Keys.onReturnPressed: _root.cancel()
                Keys.onEnterPressed: _root.cancel()
            }

            Button {
                id: _cancel
                objectName: "confirmCancel"
                text: "Cancel"
                onClicked: _root.cancel()
                Keys.onReturnPressed: _root.cancel()
                Keys.onEnterPressed: _root.cancel()
            }
        }
    }
}

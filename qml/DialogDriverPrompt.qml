// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The one prompt for every driver step (06 S187): what will happen and when,
// then OK or Cancel. The text comes from DriversModel.describe(); the caller
// opens it and runs the step on accepted().
Popup {
    id: _root
    objectName: "driverPrompt"

    property string title: ""
    property string body: ""
    property string okText: "OK"
    property string cancelText: "Cancel"

    signal accepted()
    signal rejected()

    property bool _accepted: false

    function accept() {
        _accepted = true
        close()
    }

    function reject() {
        close()
    }

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    padding: Style.dp(16)
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    width: parent ? Math.min(parent.width - Style.dp(40), Style.dp(480)) : Style.dp(480)

    onAboutToShow: _accepted = false
    onOpened: _ok.forceActiveFocus()
    onClosed: {
        if (_accepted)
            accepted()
        else
            rejected()
    }

    background: Rectangle {
        color: Style.background
        border.color: Style.lineStrong
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(12)

        Label {
            objectName: "driverPromptTitle"
            Layout.fillWidth: true
            text: _root.title
            font.bold: true
            font.pixelSize: Style.dp(16)
            wrapMode: Text.Wrap
            color: Style.fg
        }

        Label {
            objectName: "driverPromptBody"
            Layout.fillWidth: true
            visible: text.length > 0
            text: _root.body
            wrapMode: Text.Wrap
            color: Style.fg
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Style.dp(8)

            Button {
                id: _ok
                objectName: "driverPromptOk"
                text: _root.okText
                onClicked: _root.accept()
            }

            Button {
                objectName: "driverPromptCancel"
                visible: _root.cancelText.length > 0
                text: _root.cancelText
                onClicked: _root.reject()
            }
        }
    }
}

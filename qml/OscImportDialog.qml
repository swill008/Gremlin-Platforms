// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

Popup {
    id: _root

    signal accepted(string text)

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Style.dp(16)
    width: Style.dp(460)

    background: Rectangle {
        color: Style.background
        border.color: Style.accent
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    function resetFields() {
        _messages.text = ""
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(10)

        Label {
            text: "New OSC messages:"
            font.bold: true
            font.pixelSize: Style.dp(16)
        }

        TextArea {
            id: _messages
            objectName: "oscImportText"
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(90)
            wrapMode: TextEdit.NoWrap
            placeholderText: "/button/1"
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _help.implicitHeight + Style.dp(16)
            color: Style.noteFill
            border.color: Style.noteLine

            Label {
                id: _help
                anchors.fill: parent
                anchors.margins: Style.dp(8)
                wrapMode: Text.WordWrap
                color: Style.noteText
                objectName: "oscImportHelp"
                text: "Enter new OSC messages one per line.
" +
                      "Messages must start with a forward slash (/).
" +
                      "Add a suffix after a space or a comma to set the type, such as /osc_msg A or /osc_msg, A. " +
                      "A: axis. B: button (0 = released, not 0 = pressed). BNP: button that presses on each message and releases after the delay. " +
                      "C: change (presses when the value changes). E: encoder, added as an encoder axis (format Auto). " +
                      "No suffix: button. An unknown suffix is added as a button and named in the result.
" +
                      "Messages already in the list are skipped."
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                objectName: "oscImportOk"
                text: "OK"
                onClicked: {
                    _root.accepted(_messages.text)
                    _root.close()
                }
            }
            Button {
                text: "Cancel"
                onClicked: _root.close()
            }
        }
    }
}

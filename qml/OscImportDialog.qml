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
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(90)
            wrapMode: TextEdit.NoWrap
            placeholderText: "/button/1"
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _help.implicitHeight + Style.dp(16)
            color: "#8a7a2a"
            border.color: "#c4b44a"

            Label {
                id: _help
                anchors.fill: parent
                anchors.margins: Style.dp(8)
                wrapMode: Text.WordWrap
                color: "#1b1b1b"
                text: "Enter new OSC messages one per line.\n" +
                      "Messages must start with a forward slash (/).\n" +
                      "Entries may be given a suffix to set the type automatically. The default is a button. If you are importing an axis message, add the suffix A after the message such as /osc_msg A or /osc_msg, A Valid suffixes are A for axis, BNP for a no parameter (auto-release) button, B for a parameter button (0 = released, not 0 = pressed), C for change, E for encoder. Existing entries will be ignored."
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                text: "Ok"
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

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Style

Popup {
    id: root

    property string title: ""
    property string text: ""
    property string detailedText: ""

    signal accepted()
    signal rejected()

    width: Style.dp(800)
    height: Style.dp(500)
    anchors.centerIn: parent

    popupType: Popup.Item
    closePolicy: Popup.NoAutoClose
    modal: true
    dim: false

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)

        Label {
            Layout.fillWidth: true

            text: root.title

            font.bold: true
            font.pixelSize: Style.dp(16)
        }

        Label {
            Layout.fillWidth: true

            text: root.text

            wrapMode: Text.WordWrap
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Fix scrollbar behavior.
            ScrollBar.vertical.interactive: true
            ScrollBar.horizontal.interactive: true
            Component.onCompleted: () => {
                contentItem.boundsMovement = Flickable.StopAtBounds
            }

            TextArea {
                id: _details
                U.Universal.theme: Style.theme

                text: root.detailedText
                selectByMouse: true
                font.family: Style.monoFont
                // Long traceback lines wrap instead of running off the side.
                wrapMode: TextEdit.WrapAnywhere

                readOnly: true
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Style.dp(8)

            // For a bug report: the details as text.
            Button {
                text: "Copy Details"
                visible: root.detailedText.length > 0
                onClicked: () => {
                    _details.selectAll()
                    _details.copy()
                    _details.deselect()
                }
            }

            Button {
                text: "OK"

                onClicked: () => { root.close() }
            }
        }
    }
}

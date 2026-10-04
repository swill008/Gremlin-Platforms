// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

ApplicationWindow {
    id: mainWindow
    font.pixelSize: Style.fontSize
    width: Style.fitWidth(Style.dp(600), Screen)
    height: Style.fitHeight(Style.dp(300), Screen)
    visible: true
    title: qsTr("Gremlin-Platforms R1")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(20)

        Label {
            Layout.fillWidth: true

            text: "An error occurred during startup:"

            font.bold: true
            font.pixelSize: Style.dp(16)
        }

        TextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true

            text: errorString
            selectByMouse: true
            font.family: "Consolas"
            wrapMode: Text.WordWrap

            readOnly: true
        }

        Button {
            Layout.alignment: Qt.AlignBottom | Qt.AlignHCenter
            Layout.preferredWidth: Style.dp(100)

            text: qsTr("OK")

            onClicked: () => { Qt.quit() }
        }
    }
}

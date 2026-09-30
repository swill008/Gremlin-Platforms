// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

ApplicationWindow {
    font.pixelSize: Style.fontSize
    minimumWidth: Style.dp(500)
    minimumHeight: Style.dp(300)

    color: Style.background
    U.Universal.theme: Style.theme

    title: qsTr("About")

    ColumnLayout {
        anchors.fill: parent

        DisplayLabel {
            text: "<b>Gremlin-Platforms</b>"
            font.pixelSize: Style.dp(48)
        }

        DisplayLabel {
            text: "R1"
            font.pixelSize: Style.dp(19)
        }

        DisplayLabel {
            text: "Based on Joystick Gremlin R15."
            font.pixelSize: Style.dp(16)
        }

        DisplayLabel {
            text: "<html><a href='https://whitemagic.github.io/JoystickGremlin/'>https://whitemagic.github.io/JoystickGremlin/</a></html>"
            font.pixelSize: Style.dp(19)
            onLinkActivated: (url) => { Qt.openUrlExternally(url) }
        }
    }

    component DisplayLabel : Label {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignHCenter
        horizontalAlignment: Text.AlignHCenter
    }
}

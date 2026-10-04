// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

ApplicationWindow {
    id: _about

    EscapeCloses { host: _about }
    font.pixelSize: Style.fontSize
    minimumWidth: Style.fitWidth(Style.dp(500), Screen)
    minimumHeight: Style.fitHeight(Style.dp(300), Screen)

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
            // Version from version.json, so About always matches the build.
            text: "R1 " + (backend ? backend.gremlinVersion : "")
            font.pixelSize: Style.dp(19)
        }

        DisplayLabel {
            text: "<html><a href='https://github.com/swill008/Gremlin-Platforms'>github.com/swill008/Gremlin-Platforms</a></html>"
            font.pixelSize: Style.dp(19)
            onLinkActivated: (url) => { Qt.openUrlExternally(url) }
        }

        DisplayLabel {
            text: "<html>Based on <a href='https://whitemagic.github.io/JoystickGremlin/'>Joystick Gremlin</a> R15.</html>"
            font.pixelSize: Style.dp(16)
            onLinkActivated: (url) => { Qt.openUrlExternally(url) }
        }
    }

    component DisplayLabel : Label {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignHCenter
        horizontalAlignment: Text.AlignHCenter
    }
}

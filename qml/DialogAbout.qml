// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

Window {
    minimumWidth: 500
    minimumHeight: 300

    color: Style.background
    Universal.theme: Style.theme

    title: qsTr("About")

    ColumnLayout {
        anchors.fill: parent
        anchors.bottomMargin: 58

        DisplayLabel {
            text: "<b>Gremlin-Platforms</b>"
            font.pointSize: 36
        }

        DisplayLabel {
            text: "R1"
            font.pointSize: 14
        }

        DisplayLabel {
            text: "<html><a href='https://whitemagic.github.io/JoystickGremlin/'>https://whitemagic.github.io/JoystickGremlin/</a></html>"
            font.pointSize: 14
            onLinkActivated: (url) => { Qt.openUrlExternally(url) }
        }
    }

    component DisplayLabel : Label {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignHCenter
        horizontalAlignment: Text.AlignHCenter
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}

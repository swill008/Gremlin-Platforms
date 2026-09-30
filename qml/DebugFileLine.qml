// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

Rectangle {
    id: _bar

    property int tick: 0
    property string moduleFile: ""
    implicitHeight: _col.implicitHeight + Style.dp(10)
    color: "#141416"
    z: 200

    Connections {
        target: backend
        function onProfileChanged() { _bar.tick++ }
        function onWindowTitleChanged() { _bar.tick++ }
    }

    Column {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.dp(8)
        anchors.rightMargin: Style.dp(8)
        spacing: Style.dp(1)

        Label {
            width: parent.width
            color: "#FBBF24"
            font.pixelSize: Style.dp(11)
            elide: Text.ElideMiddle
            text: {
                var n = _bar.tick
                var path = (backend && backend.profilePath) ? backend.profilePath() : ""
                return "Profile: " + (path && path.length ? path : "(none)")
            }
        }
        Label {
            width: parent.width
            color: "#FBBF24"
            font.pixelSize: Style.dp(11)
            elide: Text.ElideMiddle
            text: "Configuration: " + ((backend && backend.configurationPath) ? backend.configurationPath() : "(none)")
        }
        Label {
            width: parent.width
            visible: _bar.moduleFile.length > 0
            color: "#FBBF24"
            font.pixelSize: Style.dp(11)
            elide: Text.ElideMiddle
            text: "Module file: " + _bar.moduleFile
        }
    }
}

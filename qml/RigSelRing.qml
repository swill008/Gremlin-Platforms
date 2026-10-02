// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// Selection ring drawn around a chip or drawing in the Button Map editor.
Rectangle {
    property bool on: false
    property color ringColor: "#FBBF24"
    anchors.fill: parent
    anchors.leftMargin: -Style.dp(4)
    anchors.rightMargin: -Style.dp(4)
    anchors.topMargin: -Style.dp(4)
    anchors.bottomMargin: -Style.dp(4)
    z: -1
    antialiasing: true
    color: "transparent"
    border.width: Style.dp(2)
    border.color: on ? ringColor : "transparent"
    radius: parent.radius > 0 ? parent.radius + Style.dp(4) : 0
}

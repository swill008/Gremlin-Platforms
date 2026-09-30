// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

import Gremlin.Style

Rectangle {
    property int spacing: Style.dp(10)
    property int lineWidth: Style.dp(1)
    property bool dividerVisible: true
    property color dividerColor: Style.accent

    height: spacing
    z: -1

    color: Style.background

    Loader {
        active: dividerVisible

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter

        sourceComponent: Rectangle {
            height: lineWidth
            color: dividerColor
        }
    }
}

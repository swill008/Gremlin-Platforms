// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

import Gremlin.Style


Rectangle {
    property bool showMarker: false

    anchors.left: parent.left
    anchors.right: parent.right
    anchors.verticalCenter: parent.verticalCenter

    height: Style.dp(15)

    opacity: showMarker ? 1.0 : 0.0
    color: Style.accent
    border.color: Qt.darker(Style.accent, 1.2)
    border.width: Style.dp(2)
}
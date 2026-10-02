// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T

import Gremlin.Style

// A menu bar title (File, View…): lit like a menu row, with the accent bar
// along its bottom while it is open or under the pointer.
T.MenuBarItem {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    leftPadding: Style.dp(12)
    rightPadding: Style.dp(12)
    topPadding: Style.dp(6)
    bottomPadding: Style.dp(6)

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? Style.menuText : Style.menuTextOff
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        implicitHeight: Style.dp(32)
        color: control.highlighted || control.down ? Style.menuHover : Style.clear
        Rectangle {
            visible: control.highlighted || control.down
            anchors.bottom: parent.bottom
            width: parent.width
            height: Style.menuBarW
            color: Style.menuAccent
        }
    }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
}

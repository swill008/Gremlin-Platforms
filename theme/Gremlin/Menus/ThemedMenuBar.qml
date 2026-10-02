// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T

import Gremlin.Style

// A window's menu bar in the program's style. Its menus are ThemedMenus.
T.MenuBar {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    delegate: ThemedMenuBarItem {}

    contentItem: Row {
        spacing: control.spacing
        Repeater {
            model: control.contentModel
        }
    }

    background: Rectangle {
        implicitHeight: Style.dp(32)
        color: Style.bgPage
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Style.line
        }
    }
}

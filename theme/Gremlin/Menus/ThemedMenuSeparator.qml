// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T

import Gremlin.Style

// A thin line between groups of menu rows.
T.MenuSeparator {
    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    leftPadding: Style.dp(6)
    rightPadding: Style.dp(6)
    topPadding: Style.dp(3)
    bottomPadding: Style.dp(3)

    contentItem: Rectangle {
        implicitWidth: Style.dp(120)
        implicitHeight: 1
        color: Style.menuDivider
    }
}

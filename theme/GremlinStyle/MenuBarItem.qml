// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal

import Gremlin.Style

T.MenuBarItem {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             implicitIndicatorHeight + topPadding + bottomPadding)

    padding: Style.dp(12)
    topPadding: padding - Style.dp(1)
    bottomPadding: padding + Style.dp(1)
    spacing: Style.dp(12)

    icon.width: Style.dp(20)
    icon.height: Style.dp(20)
    icon.color: !enabled ? Universal.baseLowColor : Universal.baseHighColor

    contentItem: IconLabel {
        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display
        alignment: Qt.AlignLeft

        icon: control.icon
        text: control.text
        font: control.font
        color: !control.enabled ? control.Universal.baseLowColor : control.Universal.baseHighColor
    }

    background: Rectangle {
        implicitWidth: Style.dp(40)
        implicitHeight: Style.dp(40)

        color: !control.enabled ? control.Universal.baseLowColor :
                control.down ? control.Universal.listMediumColor :
                control.highlighted ? control.Universal.listLowColor : "transparent"

        Rectangle {
            x: Style.dp(1); y: Style.dp(1)
            width: parent.width - Style.dp(2)
            height: parent.height - Style.dp(2)

            visible: control.visualFocus
            color: control.Universal.accent
            opacity: control.Universal.theme === Universal.Light ? 0.4 : 0.6
        }
    }
}

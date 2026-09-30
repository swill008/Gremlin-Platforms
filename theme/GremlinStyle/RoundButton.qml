// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.RoundButton {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    padding: Style.dp(8)
    spacing: Style.dp(8)

    icon.width: Style.dp(20)
    icon.height: Style.dp(20)

    property bool useSystemFocusVisuals: true

    contentItem: IconLabel {
        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display

        icon: control.icon
        defaultIconColor: Color.transparent(control.U.Universal.foreground, enabled ? 1.0 : 0.2)
        text: control.text
        font: control.font
        color: defaultIconColor
    }

    background: Rectangle {
        implicitWidth: Style.dp(32)
        implicitHeight: Style.dp(32)

        radius: control.radius
        visible: !control.flat || control.down || control.checked || control.highlighted
        color: control.down ? control.U.Universal.baseMediumLowColor :
               control.enabled && (control.highlighted || control.checked) ? control.U.Universal.accent :
                                                                             control.U.Universal.baseLowColor

        Rectangle {
            width: parent.width
            height: parent.height
            radius: control.radius
            color: "transparent"
            visible: enabled && control.hovered
            border.width: Style.dp(2) // ButtonBorderThemeThickness
            border.color: control.U.Universal.baseMediumLowColor
        }
    }
}

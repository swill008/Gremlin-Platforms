// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Modified by Joystick Gremlin Contributors

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

    padding: Style.dp(4)
    verticalPadding: Style.dp(2)
    spacing: Style.dp(4)

    icon.width: Style.dp(16)
    icon.height: Style.dp(16)
    icon.color: Color.transparent(U.Universal.foreground, enabled ? 1.0 : 0.2)
    font.pixelSize: Style.dp(14)

    property bool useSystemFocusVisuals: true

    contentItem: IconLabel {
        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display

        icon: control.icon
        text: control.text
        font: control.font
        color: Color.transparent(control.U.Universal.foreground, enabled ? 1.0 : 0.2)
    }

    background: Rectangle {
        implicitWidth: Style.dp(24)
        implicitHeight: Style.dp(24)

        radius: height / 2

        visible: !control.flat || control.down || control.checked || control.highlighted
        color: control.down ? control.U.Universal.baseMediumLowColor :
               control.enabled && (control.highlighted || control.checked) ? control.U.Universal.accent :
                                                                             control.U.Universal.baseLowColor

        Rectangle {
            width: parent.width
            height: parent.height
            radius: height / 2
            color: "transparent"
            visible: enabled && control.hovered
            border.width: Style.dp(1)
            border.color: control.U.Universal.baseMediumLowColor
        }
    }
}

// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.ToolButton {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    padding: Style.dp(6)
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
        implicitWidth: Style.dp(68)
        implicitHeight: Style.dp(48) // AppBarThemeCompactHeight

        color: control.enabled && (control.highlighted || control.checked) ? control.U.Universal.accent : "transparent"

        Rectangle {
            width: parent.width
            height: parent.height
            visible: enabled && (control.down || control.hovered)
            color: control.down ? control.U.Universal.listMediumColor : control.U.Universal.listLowColor
        }
    }
}

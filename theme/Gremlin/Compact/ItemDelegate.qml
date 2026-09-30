// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial
// Modified by Joystick Gremlin Contributors

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U
import Gremlin.Style

T.ItemDelegate {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             implicitIndicatorHeight + topPadding + bottomPadding)

    spacing: Style.dp(8)

    padding: Style.dp(6)
    topPadding: Style.dp(4)
    bottomPadding: Style.dp(4)

    icon.width: Style.dp(16)
    icon.height: Style.dp(16)
    icon.color: Color.transparent(U.Universal.foreground, enabled ? 1.0 : 0.2)
    font.pixelSize: Style.dp(14)

    contentItem: IconLabel {
        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display
        alignment: control.display === IconLabel.IconOnly || control.display === IconLabel.TextUnderIcon ? Qt.AlignCenter : Qt.AlignLeft

        icon: control.icon
        text: control.text
        font: control.font
        color: Color.transparent(control.U.Universal.foreground, enabled ? 1.0 : 0.2)
    }

    background: Rectangle {
        implicitWidth: Style.dp(100)
        implicitHeight: Style.dp(24)

        visible: enabled && (control.down || control.highlighted || control.visualFocus || control.hovered)
        color: control.down ? control.U.Universal.listMediumColor :
               control.hovered ? control.U.Universal.listLowColor : control.U.Universal.altMediumLowColor

        Rectangle {
            width: parent.width
            height: parent.height
            visible: control.visualFocus || control.highlighted
            color: control.U.Universal.accent
            opacity: control.U.Universal.theme === U.Universal.Light ? 0.4 : 0.6
        }
    }
}

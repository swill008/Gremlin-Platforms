// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

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

    spacing: Style.dp(12)

    padding: Style.dp(12)
    topPadding: padding - Style.dp(1)
    bottomPadding: padding + Style.dp(1)

    icon.width: Style.dp(20)
    icon.height: Style.dp(20)

    contentItem: IconLabel {
        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display
        alignment: control.display === IconLabel.IconOnly || control.display === IconLabel.TextUnderIcon ? Qt.AlignCenter : Qt.AlignLeft

        icon: control.icon
        defaultIconColor: Color.transparent(control.U.Universal.foreground, enabled ? 1.0 : 0.2)
        text: control.text
        font: control.font
        color: defaultIconColor
    }

    background: Rectangle {
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

// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.TabButton {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    padding: Style.dp(12) // PivotItemMargin
    spacing: Style.dp(8)

    icon.width: Style.dp(20)
    icon.height: Style.dp(20)

    contentItem: IconLabel {
        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display

        icon: control.icon
        defaultIconColor: Color.transparent(enabled && control.hovered
            ? control.U.Universal.baseMediumHighColor : control.U.Universal.foreground,
            control.checked || control.down || (enabled && control.hovered) ? 1.0 : 0.2)
        text: control.text
        font: control.font
        color: defaultIconColor
    }
}

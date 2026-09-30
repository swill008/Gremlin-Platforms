// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.ToolTip {
    id: control

    x: parent ? (parent.width - implicitWidth) / 2 : 0
    y: -implicitHeight - Style.dp(16)

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    margins: Style.dp(8)
    padding: Style.dp(8)
    topPadding: padding - Style.dp(3)
    bottomPadding: padding - Style.dp(1)

    closePolicy: T.Popup.CloseOnEscape | T.Popup.CloseOnPressOutsideParent | T.Popup.CloseOnReleaseOutsideParent

    contentItem: Text {
        text: control.text
        font: control.font
        wrapMode: Text.Wrap
        opacity: enabled ? 1.0 : 0.2
        color: control.U.Universal.foreground
    }

    background: Rectangle {
        color: control.U.Universal.chromeMediumLowColor
        border.color: control.U.Universal.chromeHighColor
        border.width: Style.dp(1) // ToolTipBorderThemeThickness
    }
}

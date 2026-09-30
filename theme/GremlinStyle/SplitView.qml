// Copyright (C) 2018 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.SplitView {
    id: control
    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    handle: Rectangle {
        implicitWidth: control.orientation === Qt.Horizontal ? Style.dp(6) : control.width
        implicitHeight: control.orientation === Qt.Horizontal ? control.height : Style.dp(6)
        color: T.SplitHandle.pressed ? control.U.Universal.baseMediumColor
            : (enabled && T.SplitHandle.hovered ? control.U.Universal.baseMediumLowColor : control.U.Universal.chromeHighColor)
    }
}

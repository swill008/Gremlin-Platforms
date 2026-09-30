// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal

import Gremlin.Style

T.MenuSeparator {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    padding: Style.dp(12)
    topPadding: Style.dp(9)
    bottomPadding: Style.dp(10)

    contentItem: Rectangle {
        implicitWidth: Style.dp(188)
        implicitHeight: Style.dp(1)
        color: control.Universal.baseMediumLowColor
    }

    background: Rectangle {
        color: control.Universal.altMediumLowColor
    }
}

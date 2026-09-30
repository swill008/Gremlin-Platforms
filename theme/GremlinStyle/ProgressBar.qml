// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal
import QtQuick.Controls.Universal.impl

import Gremlin.Style

T.ProgressBar {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    contentItem: ProgressBarImpl {
        implicitHeight: Style.dp(10)

        scale: control.mirrored ? -1 : 1
        color: control.Universal.accent
        progress: control.position
        indeterminate: control.visible && control.indeterminate
    }

    background: Rectangle {
        implicitWidth: Style.dp(100)
        implicitHeight: Style.dp(10)
        y: (control.height - height) / 2
        height: Style.dp(10)
        visible: !control.indeterminate
        color: control.Universal.baseLowColor
    }
}

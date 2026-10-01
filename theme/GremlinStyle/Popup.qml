// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.Popup {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    padding: Style.dp(12)

    background: Rectangle {
        color: (Style.isDarkMode ? control.U.Universal.chromeMediumLowColor : Style._light.popup)
        border.color: control.U.Universal.chromeHighColor
        border.width: Style.dp(1) // FlyoutBorderThemeThickness
    }

    T.Overlay.modal: Rectangle {
        color: control.U.Universal.baseLowColor
    }

    T.Overlay.modeless: Rectangle {
        color: control.U.Universal.baseLowColor
    }
}

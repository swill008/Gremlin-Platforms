// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.Dialog {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding,
                            implicitHeaderWidth,
                            implicitFooterWidth)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding
                             + (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0)
                             + (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0))

    padding: Style.dp(24)
    verticalPadding: Style.dp(18)

    background: Rectangle {
        color: (Style.isDarkMode ? control.U.Universal.chromeMediumLowColor : Style._light.popup)
        border.color: control.U.Universal.chromeHighColor
        border.width: Style.dp(1) // FlyoutBorderThemeThickness
    }

    header: U.Label {
        text: control.title
        visible: parent?.parent === T.Overlay.overlay && control.title
        elide: Label.ElideRight
        topPadding: Style.dp(18)
        leftPadding: Style.dp(24)
        rightPadding: Style.dp(24)
        // TODO: QPlatformTheme::TitleBarFont
        font.pixelSize: Style.dp(20)
        background: Rectangle {
            x: Style.dp(1); y: Style.dp(1) // // FlyoutBorderThemeThickness
            color: (Style.isDarkMode ? control.U.Universal.chromeMediumLowColor : Style._light.popup)
            width: parent.width - Style.dp(2)
            height: parent.height - Style.dp(1)
        }
    }

    footer: DialogButtonBox {
        visible: count > 0
    }

    T.Overlay.modal: Rectangle {
        color: control.U.Universal.baseLowColor
    }

    T.Overlay.modeless: Rectangle {
        color: control.U.Universal.baseLowColor
    }
}

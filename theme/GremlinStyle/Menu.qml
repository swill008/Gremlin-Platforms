// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U
import QtQuick.Window

import Gremlin.Style

T.Menu {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    margins: 0
    overlap: Style.dp(1)

    delegate: MenuItem { }

    contentItem: ListView {
        implicitHeight: contentHeight
        model: control.contentModel
        interactive: Window.window
                     ? contentHeight + control.topPadding + control.bottomPadding > control.height
                     : false
        clip: true
        currentIndex: control.currentIndex

        ScrollIndicator.vertical: ScrollIndicator {}
    }

    background: Rectangle {
        implicitWidth: Style.dp(200)
        implicitHeight: Style.dp(40)
        color: control.U.Universal.chromeMediumLowColor
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

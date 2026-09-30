// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U

import Gremlin.Style

T.Slider {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitHandleWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitHandleHeight + topPadding + bottomPadding)

    padding: Style.dp(6)

    property bool useSystemFocusVisuals: true

    handle: Rectangle {
        implicitWidth: control.horizontal ? Style.dp(8) : Style.dp(24)
        implicitHeight: control.horizontal ? Style.dp(24) : Style.dp(8)

        x: control.leftPadding + (control.horizontal ? control.visualPosition * (control.availableWidth - width) : (control.availableWidth - width) / 2)
        y: control.topPadding + (control.horizontal ? (control.availableHeight - height) / 2 : control.visualPosition * (control.availableHeight - height))

        radius: Style.dp(4)
        color: control.pressed ? control.U.Universal.chromeHighColor :
               control.enabled ? control.hovered ? control.U.Universal.chromeAltLowColor :
               control.U.Universal.accent : control.U.Universal.chromeDisabledHighColor
    }

    background: Item {
        implicitWidth: control.horizontal ? Style.dp(200) : Style.dp(18)
        implicitHeight: control.horizontal ? Style.dp(18) : Style.dp(200)

        x: control.leftPadding + (control.horizontal ? 0 : (control.availableWidth - width) / 2)
        y: control.topPadding + (control.horizontal ? (control.availableHeight - height) / 2 : 0)
        width: control.horizontal ? control.availableWidth : implicitWidth
        height: control.horizontal ? implicitHeight : control.availableHeight

        scale: control.horizontal && control.mirrored ? -1 : 1

        Rectangle {
            x: control.horizontal ? 0 : (parent.width - width) / 2
            y: control.horizontal ? (parent.height - height) / 2 : 0
            width: control.horizontal ? parent.width : Style.dp(2) // SliderTrackThemeHeight
            height: !control.horizontal ? parent.height : Style.dp(2) // SliderTrackThemeHeight

            color: enabled && control.hovered && !control.pressed ? control.U.Universal.baseMediumColor :
                   control.enabled ? control.U.Universal.baseMediumLowColor : control.U.Universal.chromeDisabledHighColor
        }

        Rectangle {
            x: control.horizontal ? 0 : (parent.width - width) / 2
            y: control.horizontal ? (parent.height - height) / 2 : control.visualPosition * parent.height
            width: control.horizontal ? control.position * parent.width : Style.dp(2) // SliderTrackThemeHeight
            height: !control.horizontal ? control.position * parent.height : Style.dp(2) // SliderTrackThemeHeight

            color: control.enabled ? control.U.Universal.accent : control.U.Universal.chromeDisabledHighColor
        }
    }
}

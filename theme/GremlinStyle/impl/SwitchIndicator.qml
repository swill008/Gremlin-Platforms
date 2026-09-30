// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U

import Gremlin.Style

Item {
    id: indicator
    implicitWidth: Style.dp(44)
    implicitHeight: Style.dp(20)

    property T.AbstractButton control

    Rectangle {
        width: parent.width
        height: parent.height

        radius: Style.dp(10)
        color: !indicator.control.enabled ? "transparent" :
                indicator.control.pressed ? indicator.control.U.Universal.baseMediumColor :
                indicator.control.checked ? indicator.control.U.Universal.accent : "transparent"
        border.color: !indicator.control.enabled ? indicator.control.U.Universal.baseLowColor :
                       indicator.control.checked && !indicator.control.pressed ? indicator.control.U.Universal.accent :
                       indicator.control.hovered && !indicator.control.checked && !indicator.control.pressed ? indicator.control.U.Universal.baseHighColor : indicator.control.U.Universal.baseMediumColor
        opacity: enabled && indicator.control.hovered && indicator.control.checked && !indicator.control.pressed ? (indicator.control.U.Universal.theme === U.Universal.Light ? 0.7 : 0.9) : 1.0
        border.width: Style.dp(2)
    }

    Rectangle {
        width: Style.dp(10)
        height: Style.dp(10)
        radius: Style.dp(5)

        color: !indicator.control.enabled ? indicator.control.U.Universal.baseLowColor :
                indicator.control.pressed || indicator.control.checked ? indicator.control.U.Universal.chromeWhiteColor :
                indicator.control.hovered && !indicator.control.checked ? indicator.control.U.Universal.baseHighColor : indicator.control.U.Universal.baseMediumHighColor

        x: Math.max(Style.dp(5), Math.min(parent.width - width - Style.dp(5),
                                indicator.control.visualPosition * parent.width - (width / 2)))
        y: (parent.height - height) / 2

        Behavior on x {
            enabled: !indicator.control.pressed
            SmoothedAnimation { velocity: Style.dp(200) }
        }
    }
}

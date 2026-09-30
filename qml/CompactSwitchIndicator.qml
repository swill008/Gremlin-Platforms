// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U
import Gremlin.Style

Item {
    id: indicator

    implicitWidth: control.contentItem.font.pixelSize * 2.2
    implicitHeight: control.contentItem.font.pixelSize

    property T.AbstractButton control


    Rectangle {
        id: slot

        width: parent.width
        height: parent.height

        radius: height / 2 //10
        color: !indicator.control.enabled ? "transparent" :
                indicator.control.pressed ? indicator.control.U.Universal.baseMediumColor :
                indicator.control.checked ? indicator.control.U.Universal.accent : "transparent"
        border.color: !indicator.control.enabled ? indicator.control.U.Universal.baseLowColor :
                       indicator.control.checked && !indicator.control.pressed ? indicator.control.U.Universal.accent :
                       indicator.control.hovered && !indicator.control.checked && !indicator.control.pressed ? indicator.control.U.Universal.baseHighColor : indicator.control.U.Universal.baseMediumColor
        opacity: enabled && indicator.control.hovered && indicator.control.checked && !indicator.control.pressed ? (indicator.control.U.Universal.theme === U.Universal.Light ? 0.7 : 0.9) : 1.0
        border.width: height < Style.dp(20) ? Style.dp(1) : Style.dp(2)
    }

    Rectangle {
        id: circle

        width: 0.6 * slot.height //10
        height: 0.6 * slot.height //10
        radius: height / 2 //5

        color: !indicator.control.enabled ? indicator.control.U.Universal.baseLowColor :
                indicator.control.pressed || indicator.control.checked ? indicator.control.U.Universal.chromeWhiteColor :
                indicator.control.hovered && !indicator.control.checked ? indicator.control.U.Universal.baseHighColor : indicator.control.U.Universal.baseMediumHighColor

        x: indicator.control.visualPosition < 0.5 ? width / 2 : parent.width - 1.5 * width
        y: (parent.height - height) / 2

        Behavior on x {
            enabled: !indicator.control.pressed
            SmoothedAnimation { velocity: 200 }
        }
    }
}

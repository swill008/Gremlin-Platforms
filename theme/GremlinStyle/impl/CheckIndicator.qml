// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U

import Gremlin.Style

Rectangle {
    id: indicator
    implicitWidth: Style.dp(20)
    implicitHeight: Style.dp(20)

    color: !control.enabled ? "transparent" :
            control.down && !partiallyChecked ? control.U.Universal.baseMediumColor :
            control.checkState === Qt.Checked ? control.U.Universal.accent : "transparent"
    border.color: !control.enabled ? control.U.Universal.baseLowColor :
                   control.down ? control.U.Universal.baseMediumColor :
                   control.checked ? control.U.Universal.accent : control.U.Universal.baseMediumHighColor
    border.width: Style.dp(2) // CheckBoxBorderThemeThickness

    property Item control
    readonly property bool partiallyChecked: control.checkState === Qt.PartiallyChecked

    ColorImage {
        width: Style.dp(20)
        height: Style.dp(20)
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2

        visible: indicator.control.checkState === Qt.Checked
        color: !indicator.control.enabled ? indicator.control.U.Universal.baseLowColor : indicator.control.U.Universal.chromeWhiteColor
        source: "qrc:/qt-project.org/imports/QtQuick/Controls/Universal/images/checkmark.png"
    }

    Rectangle {
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        width: indicator.partiallyChecked ? parent.width / 2 : parent.width
        height: indicator.partiallyChecked ? parent.height / 2 : parent.height

        visible: !indicator.control.pressed && enabled && indicator.control.hovered || indicator.partiallyChecked
        color: !indicator.partiallyChecked ? "transparent" :
               !indicator.control.enabled ? indicator.control.U.Universal.baseLowColor :
                indicator.control.down ? indicator.control.U.Universal.baseMediumColor :
                indicator.control.hovered ? indicator.control.U.Universal.baseHighColor : indicator.control.U.Universal.baseMediumHighColor
        border.width: indicator.partiallyChecked ? 0 : Style.dp(2) // CheckBoxBorderThemeThickness
        border.color: indicator.control.U.Universal.baseMediumLowColor
    }
}

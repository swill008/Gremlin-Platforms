// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal

import Gremlin.Style

T.MenuItem {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             implicitIndicatorHeight + topPadding + bottomPadding)

    padding: Style.dp(12)
    topPadding: padding - Style.dp(1)
    bottomPadding: padding + Style.dp(1)
    spacing: Style.dp(12)

    icon.width: Style.dp(20)
    icon.height: Style.dp(20)

    contentItem: IconLabel {
        readonly property real arrowPadding: control.subMenu && control.arrow ? control.arrow.width + control.spacing : 0
        readonly property real indicatorPadding: control.checkable && control.indicator ? control.indicator.width + control.spacing : 0
        leftPadding: !control.mirrored ? indicatorPadding : arrowPadding
        rightPadding: control.mirrored ? indicatorPadding : arrowPadding

        spacing: control.spacing
        mirrored: control.mirrored
        display: control.display
        alignment: Qt.AlignLeft

        icon: control.icon
        defaultIconColor: !control.enabled ? control.Universal.baseLowColor : control.Universal.baseHighColor
        text: control.text
        font: control.font
        color: defaultIconColor
    }

    arrow: ColorImage {
        width: Style.dp(12)
        height: Style.dp(12)
        x: control.mirrored ? control.leftPadding : control.width - width - control.rightPadding
        y: control.topPadding + (control.availableHeight - height) / 2

        visible: control.subMenu
        mirror: control.mirrored
        color: !enabled ? control.Universal.baseLowColor : control.Universal.baseHighColor
        source: "qrc:/qt-project.org/imports/QtQuick/Controls/Universal/images/rightarrow.png"
    }

    indicator: ColorImage {
        width: Style.dp(20)
        height: Style.dp(20)
        x: control.text ? (control.mirrored ? control.width - width - control.rightPadding : control.leftPadding) : control.leftPadding + (control.availableWidth - width) / 2
        y: control.topPadding + (control.availableHeight - height) / 2

        visible: control.checked
        color: !control.enabled ? control.Universal.baseLowColor : control.down ? control.Universal.baseHighColor : control.Universal.baseMediumHighColor
        source: !control.checkable ? "" : "qrc:/qt-project.org/imports/QtQuick/Controls/Universal/images/checkmark.png"
    }

    background: Rectangle {
        implicitWidth: Style.dp(200)
        implicitHeight: Style.dp(40)

        color: !control.enabled ? control.Universal.baseLowColor :
                control.down ? control.Universal.listMediumColor :
                control.highlighted ? control.Universal.listLowColor : control.Universal.altMediumLowColor

        Rectangle {
            x: Style.dp(1); y: Style.dp(1)
            width: parent.width - Style.dp(2)
            height: parent.height - Style.dp(2)

            visible: control.visualFocus
            color: control.Universal.accent
            opacity: control.Universal.theme === Universal.Light ? 0.4 : 0.6
        }
    }
}

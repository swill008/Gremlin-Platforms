// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U
import QtQuick.Controls.Universal.impl

import Gremlin.Menus as Menus
import Gremlin.Style

T.SpinBox {
    id: control


    // Note: the width of the indicators are calculated into the padding
    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            contentItem.implicitWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             up.implicitIndicatorHeight, down.implicitIndicatorHeight)

    // TextControlThemePadding + 2 (border)
    padding: Style.dp(12)
    topPadding: padding - Style.dp(7)
    leftPadding: padding + (control.mirrored ? (up.indicator ? up.indicator.width : 0) : (down.indicator ? down.indicator.width : 0))
    rightPadding: padding + (control.mirrored ? (down.indicator ? down.indicator.width : 0) : (up.indicator ? up.indicator.width : 0))
    bottomPadding: padding - Style.dp(5)

    U.Universal.theme: activeFocus ? U.Universal.Light : undefined

    validator: IntValidator {
        locale: control.locale.name
        bottom: Math.min(control.from, control.to)
        top: Math.max(control.from, control.to)
    }

    contentItem: TextInput {
        text: control.displayText

        font: control.font
        color: !enabled ? control.U.Universal.chromeDisabledLowColor :
                activeFocus ? control.U.Universal.chromeBlackHighColor : control.U.Universal.foreground
        selectionColor: control.U.Universal.accent
        selectedTextColor: control.U.Universal.chromeWhiteColor
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter

        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: control.inputMethodHints
        clip: width < implicitWidth

        ContextMenu.menu: Menus.TextEditMenu {
            editor: parent
        }
    }

    up.indicator: Item {
        implicitWidth: Style.dp(28)
        height: control.height + Style.dp(4)
        y: -Style.dp(2)
        x: control.mirrored ? 0 : control.width - width

        Rectangle {
            x: Style.dp(2); y: Style.dp(4)
            width: parent.width - Style.dp(4)
            height: parent.height - Style.dp(8)
            color: control.activeFocus ? control.U.Universal.accent :
                   control.up.pressed ? control.U.Universal.baseMediumLowColor :
                   control.up.hovered ? control.U.Universal.baseLowColor : "transparent"
            visible: control.up.pressed || control.up.hovered
            opacity: control.activeFocus && !control.up.pressed ? 0.4 : 1.0
        }

        ColorImage {
            width: Style.dp(12)
            height: Style.dp(12)
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            color: !enabled ? control.U.Universal.chromeDisabledLowColor :
                              control.activeFocus ? control.U.Universal.chromeBlackHighColor : control.U.Universal.baseHighColor
            source: "qrc:/qt-project.org/imports/QtQuick/Controls/Universal/images/" + (control.mirrored ? "left" : "right") + "arrow.png"
        }
    }

    down.indicator: Item {
        implicitWidth: Style.dp(28)
        height: control.height + Style.dp(4)
        y: -Style.dp(2)
        x: control.mirrored ? control.width - width : 0

        Rectangle {
            x: Style.dp(2); y: Style.dp(4)
            width: parent.width - Style.dp(4)
            height: parent.height - Style.dp(8)
            color: control.activeFocus ? control.U.Universal.accent :
                   control.down.pressed ? control.U.Universal.baseMediumLowColor :
                   control.down.hovered ? control.U.Universal.baseLowColor : "transparent"
            visible: control.down.pressed || control.down.hovered
            opacity: control.activeFocus && !control.down.pressed ? 0.4 : 1.0
        }

        ColorImage {
            width: Style.dp(12)
            height: Style.dp(12)
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            color: !enabled ? control.U.Universal.chromeDisabledLowColor :
                              control.activeFocus ? control.U.Universal.chromeBlackHighColor : control.U.Universal.baseHighColor
            source: "qrc:/qt-project.org/imports/QtQuick/Controls/Universal/images/" + (control.mirrored ? "right" : "left") + "arrow.png"
        }
    }

    background: Rectangle {
        implicitWidth: Style.dp(60) + Style.dp(28) // TextControlThemeMinWidth - 4 (border)
        implicitHeight: Style.dp(28) // TextControlThemeMinHeight - 4 (border)

        border.width: Style.dp(2) // TextControlBorderThemeThickness
        border.color: !control.enabled ? control.U.Universal.baseLowColor :
                       control.activeFocus ? control.U.Universal.accent :
                       control.hovered ? control.U.Universal.baseMediumColor : control.U.Universal.chromeDisabledLowColor
        color: control.enabled ? (Style.isDarkMode ? control.U.Universal.background : Style._light.field) : control.U.Universal.baseLowColor
    }
}

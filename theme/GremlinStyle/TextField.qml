// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl
import QtQuick.Controls.Universal as U
import QtQuick.Controls.Universal.impl

import Gremlin.Style

T.TextField {
    id: control

    // TextControlThemePadding + 2 (border)
    padding: Style.dp(12)
    topPadding: padding - Style.dp(7)
    rightPadding: padding - Style.dp(4)
    bottomPadding: padding - Style.dp(5)

    implicitWidth: implicitBackgroundWidth + leftInset + rightInset
                   || Math.max(contentWidth, placeholder.implicitWidth) + leftPadding + rightPadding
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             contentHeight + topPadding + bottomPadding,
                             placeholder.implicitHeight + topPadding + bottomPadding)

    U.Universal.theme: activeFocus ? U.Universal.Light : undefined

    color: !enabled ? U.Universal.chromeDisabledLowColor : U.Universal.foreground
    selectionColor: U.Universal.accent
    selectedTextColor: U.Universal.chromeWhiteColor
    placeholderTextColor: !enabled ? U.Universal.chromeDisabledLowColor :
                                     activeFocus ? U.Universal.chromeBlackMediumLowColor :
                                                   U.Universal.baseMediumColor
    verticalAlignment: TextInput.AlignVCenter

    ContextMenu.menu: TextEditingContextMenu {
        editor: control
    }

    PlaceholderText {
        id: placeholder
        x: control.leftPadding
        y: control.topPadding
        width: control.width - (control.leftPadding + control.rightPadding)
        height: control.height - (control.topPadding + control.bottomPadding)

        text: control.placeholderText
        font: control.font
        color: control.placeholderTextColor
        visible: !control.length && !control.preeditText && (!control.activeFocus || control.horizontalAlignment !== Qt.AlignHCenter)
        verticalAlignment: control.verticalAlignment
        elide: Text.ElideRight
        renderType: control.renderType
    }

    background: Rectangle {
        implicitWidth: Style.dp(60) // TextControlThemeMinWidth - 4 (border)
        implicitHeight: Style.dp(28) // TextControlThemeMinHeight - 4 (border)

        border.width: Style.dp(2) // TextControlBorderThemeThickness
        border.color: !control.enabled ? control.U.Universal.baseLowColor :
                       control.activeFocus ? control.U.Universal.accent :
                       control.hovered ? control.U.Universal.baseMediumColor : control.U.Universal.chromeDisabledLowColor
        color: control.enabled ? (Style.isDarkMode ? control.U.Universal.background : Style._light.field) : control.U.Universal.baseLowColor
    }
}

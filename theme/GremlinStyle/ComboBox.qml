// Copyright (C) 2017 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
// Qt-Security score:significant reason:default

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQuick.Controls.impl
import QtQuick.Templates as T
import QtQuick.Controls.Universal as U
import QtQuick.Controls.Universal.impl

import Gremlin.Style
import Gremlin.Menus as Menus

T.ComboBox {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding,
                             // The arrow image keeps its natural implicit size, so use its scaled height.
                             (indicator ? indicator.height : 0) + topPadding + bottomPadding)

    leftPadding: padding + (!control.mirrored || !indicator || !indicator.visible ? 0 : indicator.width + spacing)
    rightPadding: padding + (control.mirrored || !indicator || !indicator.visible ? 0 : indicator.width + spacing)

    U.Universal.theme: editable && activeFocus ? U.Universal.Light : undefined

    // Rows and list in the menus' style (Gremlin.Menus); long lists get a
    // search box.
    delegate: Menus.DropdownRow {
        combo: control
    }

    indicator: ColorImage {
        width: Style.dp(32)
        height: Style.dp(32)
        x: control.mirrored ? control.padding : control.width - width - control.padding
        y: control.topPadding + (control.availableHeight - height) / 2
        color: !control.enabled ? control.U.Universal.baseLowColor : control.U.Universal.baseMediumHighColor
        source: "qrc:/qt-project.org/imports/QtQuick/Controls/Universal/images/downarrow.png"

        Rectangle {
            z: -1
            width: parent.width
            height: parent.height
            color: control.activeFocus ? control.U.Universal.accent :
                   control.pressed ? control.U.Universal.baseMediumLowColor :
                   control.hovered ? control.U.Universal.baseLowColor : "transparent"
            visible: control.editable && !control.contentItem.hovered && (control.pressed || control.hovered)
            opacity: control.activeFocus && !control.pressed ? 0.4 : 1.0
        }
    }

    contentItem: T.TextField {
        implicitHeight: contentHeight + topPadding + bottomPadding

        leftPadding: control.mirrored ? Style.dp(1) : Style.dp(12)
        rightPadding: control.mirrored ? Style.dp(10) : Style.dp(1)
        topPadding: Style.dp(5) - control.topPadding
        bottomPadding: Style.dp(7) - control.bottomPadding

        text: control.editable ? control.editText : control.displayText

        enabled: control.editable
        autoScroll: control.editable
        readOnly: control.down
        inputMethodHints: control.inputMethodHints
        validator: control.validator
        selectByMouse: control.selectTextByMouse

        color: !control.enabled ? control.U.Universal.chromeDisabledLowColor :
                control.editable && control.activeFocus ? control.U.Universal.chromeBlackHighColor : control.U.Universal.foreground
        selectionColor: control.U.Universal.accent
        selectedTextColor: control.U.Universal.chromeWhiteColor
        verticalAlignment: Text.AlignVCenter

        ContextMenu.menu: Menus.TextEditMenu {
            editor: parent
        }
    }

    background: Rectangle {
        implicitWidth: Style.dp(120)
        implicitHeight: Style.dp(32)

        border.width: control.flat ? 0 : Style.dp(2) // ComboBoxBorderThemeThickness
        border.color: !control.enabled ? control.U.Universal.baseLowColor :
                       control.editable && control.activeFocus ? control.U.Universal.accent :
                       control.down ? control.U.Universal.baseMediumLowColor :
                       control.hovered ? control.U.Universal.baseMediumColor : control.U.Universal.baseMediumLowColor
        color: !control.enabled ? control.U.Universal.baseLowColor :
                control.down ? control.U.Universal.listMediumColor :
                control.flat && control.hovered ? control.U.Universal.listLowColor :
                control.editable && control.activeFocus ? (Style.isDarkMode ? control.U.Universal.background : Style._light.field) : (Style.isDarkMode ? control.U.Universal.altMediumLowColor : Style._light.item)
        visible: !control.flat || control.pressed || control.hovered || control.visualFocus

        Rectangle {
            x: Style.dp(2)
            y: Style.dp(2)
            width: parent.width - Style.dp(4)
            height: parent.height - Style.dp(4)

            visible: control.visualFocus && !control.editable
            color: control.U.Universal.accent
            opacity: control.U.Universal.theme === U.Universal.Light ? 0.4 : 0.6
        }
    }

    popup: Menus.DropdownPopup {
        combo: control
    }
}

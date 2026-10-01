// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Templates as T
import Gremlin.Style

ComboBox {
    id: control

    property bool enableTooltips: true
    property int scrollStep: 3

    delegate: ItemDelegate {
        required property var model
        required property int index

        width: ListView.view.width
        text: model[control.textRole]
        font.weight: control.currentIndex === index ? Font.DemiBold : Font.Normal
        highlighted: control.highlightedIndex === index
        hoverEnabled: control.hoverEnabled

        // The current value: an accent bar as well as the bold text.
        Rectangle {
            visible: control.currentIndex === index
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: Style.dp(3)
            color: control.U.Universal.accent
        }

        WrappingTooltip {
            text: parent.text
            visible: parent.hovered && control.enableTooltips
        }
    }

    popup: T.Popup {
        // Open below the box. Opened on top, the first entry sat under the pointer
        // and was highlighted instead of the current value.
        y: control.height
        width: control.width
        height: Math.min(contentItem.implicitHeight, control.Window.height - topMargin - bottomMargin)
        topMargin: Style.dp(8)
        bottomMargin: Style.dp(8)

        U.Universal.theme: control.U.Universal.theme
        U.Universal.accent: control.U.Universal.accent

        contentItem: ComboBoxScrollableEntries {
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            scrollStep: control.scrollStep
        }

        background: Rectangle {
            color: control.U.Universal.chromeMediumLowColor
            border.color: control.U.Universal.chromeHighColor
            border.width: Style.dp(1)
        }
    }

    WrappingTooltip {
        text: control.currentText
        visible: _hoverHandler.hovered && control.enableTooltips
    }

    HoverHandler {
        id: _hoverHandler
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    }
}

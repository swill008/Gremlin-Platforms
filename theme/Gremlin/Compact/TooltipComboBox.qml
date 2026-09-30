// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Templates as T
import Gremlin.Base as Base
import Gremlin.Compact as Compact
import Gremlin.Style

Compact.ComboBox {
    id: control

    property bool enableTooltips: true
    property int scrollStep: 3

    delegate: ItemDelegate {
        required property var model
        required property int index

        width: ListView.view.width
        text: model[control.textRole]
        font.pixelSize: Style.dp(14)
        topPadding: Style.dp(4)
        bottomPadding: Style.dp(4)
        font.weight: control.currentIndex === index ? Font.DemiBold : Font.Normal
        highlighted: control.highlightedIndex === index
        hoverEnabled: control.hoverEnabled

        Base.WrappingTooltip {
            text: parent.text
            visible: parent.hovered && control.enableTooltips
        }
    }

    popup: T.Popup {
        width: control.width
        height: Math.min(contentItem.implicitHeight, control.Window.height - topMargin - bottomMargin)
        topMargin: Style.dp(4)
        bottomMargin: Style.dp(4)

        U.Universal.theme: control.U.Universal.theme
        U.Universal.accent: control.U.Universal.accent

        contentItem: Base.ComboBoxScrollableEntries {
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

    Base.WrappingTooltip {
        text: control.currentText
        visible: _hoverHandler.hovered && control.enableTooltips
    }

    HoverHandler {
        id: _hoverHandler
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    }
}

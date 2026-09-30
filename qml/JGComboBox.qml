// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.Style

ComboBox {
    id: _combobox

    property bool enableTooltips: true

    delegate: ItemDelegate {
        required property var model
        required property int index

        width: ListView.view.width
        text: model[_combobox.textRole]
        font.weight: _combobox.currentIndex === index ? Font.DemiBold : Font.Normal
        highlighted: _combobox.highlightedIndex === index
        hoverEnabled: _combobox.hoverEnabled

        HoverHandler {
            id: _rowHover
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        }

        ToolTip {
            text: parent.text
            width: contentWidth > Style.dp(500) ? Style.dp(500) : contentWidth + Style.dp(20)
            visible: _rowHover.hovered && _combobox.enableTooltips
            delay: 500
            x: _rowHover.point.position.x - width / 2
            y: _rowHover.point.position.y - height - Style.dp(8)
        }
    }

    ToolTip {
        text: parent.currentText
        // Set an upper width of the tooltip to force word wrap
        // on long selection names.
        width: contentWidth > Style.dp(500) ? Style.dp(500) : contentWidth + Style.dp(20)
        visible: _hoverHandler.hovered && enableTooltips
        delay: 500
        x: _hoverHandler.point.position.x - width / 2
        y: _hoverHandler.point.position.y - height - Style.dp(8)
    }

    HoverHandler {
        id: _hoverHandler
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    }
}
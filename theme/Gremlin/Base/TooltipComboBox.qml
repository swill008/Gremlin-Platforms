// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Templates as T
import Gremlin.Style
import Gremlin.Menus as Menus

ComboBox {
    id: control

    property bool enableTooltips: true
    property int scrollStep: 3

    delegate: Menus.DropdownRow {
        combo: control

        WrappingTooltip {
            text: parent.text
            visible: parent.hovered && control.enableTooltips
        }
    }

    popup: Menus.DropdownPopup {
        combo: control
        scrollStep: control.scrollStep
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

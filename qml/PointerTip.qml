// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only
// Status/chrome tip: centered on the pointer, 8 px above.

import QtQuick
import QtQuick.Controls

Item {
    id: _root

    anchors.fill: parent
    property string text: ""
    property int delay: 400
    property int timeout: -1
    property bool show: true

    HoverHandler {
        id: _hover
        enabled: _root.show && _root.text.length > 0
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    }

    ToolTip {
        visible: _root.show && _hover.hovered && _root.text.length > 0
        text: _root.text
        delay: _root.delay
        timeout: _root.timeout < 0 ? -1 : _root.timeout
        x: _hover.point.position.x - width / 2
        y: _hover.point.position.y - height - 8
    }
}

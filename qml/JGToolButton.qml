// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

ToolButton {
    property alias color: _icon.color
    property alias tooltip: _tooltip.text
    property string caption: ""

    contentItem: Column {
        spacing: 0

        Label {
            id: _icon
            text: parent.parent.text
            font.family: "bootstrap-icons"
            font.pixelSize: 48
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            width: parent.width
        }

        Label {
            visible: caption.length > 0
            text: caption
            font.pixelSize: 9
            horizontalAlignment: Text.AlignHCenter
            width: parent.width
        }
    }

    ToolTip {
        id: _tooltip
        visible: parent.hovered
        delay: 500
    }
}

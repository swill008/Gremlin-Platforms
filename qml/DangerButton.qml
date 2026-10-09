// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U

import Gremlin.Style

// 01 S140: the red button for every delete, remove or clear. White text on
// red, darker on hover and press; disabled it greys out as other buttons do.
Button {
    id: _root

    contentItem: Label {
        objectName: "dangerButtonLabel"
        text: _root.text
        font: _root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        color: _root.enabled ? Style.onColor : Style.fgDisabled
    }

    background: Rectangle {
        objectName: "dangerButtonFill"
        implicitWidth: Style.dp(32)
        implicitHeight: Style.dp(32)
        color: !_root.enabled ? _root.U.Universal.baseLowColor
             : _root.down ? Style.dangerPressed
             : _root.hovered ? Style.dangerHover
             : Style.danger
        // The keyboard focus ring, as other buttons show it.
        border.width: _root.visualFocus ? Style.dp(2) : 0
        border.color: Style.onColor
    }
}

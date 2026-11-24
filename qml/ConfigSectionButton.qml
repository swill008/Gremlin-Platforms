// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// A row in the Options sidebar (a section, or one of the open profile's
// pages). The chosen one is highlighted with an accent bar.
AbstractButton {
    id: _button

    property bool current: false

    Layout.fillWidth: true
    implicitHeight: Style.dp(36)
    hoverEnabled: true

    background: Rectangle {
        radius: Style.dp(6)
        color: _button.current ? Style.bgSelected
            : (_button.hovered ? Style.bgHover : "transparent")

        Rectangle {
            visible: _button.current
            x: Style.dp(4)
            width: Style.dp(3)
            height: Style.dp(18)
            radius: Style.dp(2)
            anchors.verticalCenter: parent.verticalCenter
            color: Style.accent
        }
    }

    contentItem: Label {
        leftPadding: Style.dp(16)
        text: _button.text
        color: _button.current ? Style.fgStrong : Style.fgSoft
        font.pixelSize: Style.dp(14)
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}

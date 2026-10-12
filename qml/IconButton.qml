// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Style

Button {
    property alias textColor: _text.color

    font.family: Style.iconFont
    font.pixelSize: Style.dp(17)

    contentItem: Text {
        id: _text

        text: parent.text
        font: parent.font
        color: parent.hovered ? Style.accent : Style.foreground

        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        anchors.fill: parent
        color: "transparent"
    }
}
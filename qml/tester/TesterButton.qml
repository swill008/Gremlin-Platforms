// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// A plain button in the program's look (raised surface, strong line).

import QtQuick

import Gremlin.Style

Rectangle {
    id: _button

    property string text: ""
    property bool checked: false
    signal clicked()

    implicitWidth: _label.implicitWidth + Style.dp(22)
    implicitHeight: _label.implicitHeight + Style.dp(10)
    radius: Style.dp(4)
    color: _area.pressed ? Style.bgSelected
        : (_area.containsMouse || checked) ? Style.bgHover : Style.bgRaised
    border.color: checked ? Style.accent : Style.lineStrong

    Accessible.role: Accessible.Button
    Accessible.name: text

    Text {
        id: _label
        anchors.centerIn: parent
        text: _button.text
        font.family: Style.uiFont
        font.pixelSize: Style.dp(13)
        color: Style.fg
    }

    MouseArea {
        id: _area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: _button.clicked()
    }
}

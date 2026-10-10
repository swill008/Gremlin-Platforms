// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// A hat as a compass: a dot at the direction it points (degrees, 0 = up,
// 90 = right; -1 = centred), at the middle when centred.

import QtQuick

import Gremlin.Style

Rectangle {
    id: _hat

    property int value: -1
    property string label: ""

    readonly property bool centred: value < 0 || value >= 360
    readonly property real angle: centred ? 0 : value * Math.PI / 180.0
    readonly property real reach: width / 2 - _pip.width / 2 - Style.dp(5)

    width: Style.dp(72)
    height: width
    radius: width / 2
    color: Style.bgWell
    border.color: Style.line

    Rectangle {
        id: _pip
        objectName: "hatPip"
        width: Style.dp(12)
        height: width
        radius: width / 2
        color: _hat.centred ? Style.fgDisabled : Style.ok
        x: _hat.width / 2 - width / 2 + (_hat.centred ? 0 : Math.sin(_hat.angle) * _hat.reach)
        y: _hat.height / 2 - height / 2 - (_hat.centred ? 0 : Math.cos(_hat.angle) * _hat.reach)
    }

    Text {
        anchors.top: parent.bottom
        anchors.topMargin: Style.dp(3)
        anchors.horizontalCenter: parent.horizontalCenter
        text: _hat.label
        font.family: Style.uiFont
        font.pixelSize: Style.dp(11)
        color: Style.fgMuted
    }
}

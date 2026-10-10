// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// A small on/off switch with its label (Follow, Follow input).

import QtQuick

import Gremlin.Style

Item {
    id: _switch

    property string text: ""
    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: _track.width + Style.dp(6) + _label.implicitWidth
    implicitHeight: Math.max(_track.height, _label.implicitHeight)

    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    Accessible.checked: checked

    Rectangle {
        id: _track
        anchors.verticalCenter: parent.verticalCenter
        width: Style.dp(34)
        height: Style.dp(18)
        radius: height / 2
        color: _switch.checked ? Style.ok : Style.bgRaised
        border.color: _switch.checked ? Style.ok : Style.lineStrong

        Rectangle {
            width: Style.dp(14)
            height: width
            radius: width / 2
            anchors.verticalCenter: parent.verticalCenter
            x: _switch.checked ? parent.width - width - Style.dp(2) : Style.dp(2)
            color: _switch.checked ? Style.onColor : Style.fgMuted
        }
    }
    Text {
        id: _label
        anchors.left: _track.right
        anchors.leftMargin: Style.dp(6)
        anchors.verticalCenter: parent.verticalCenter
        text: _switch.text
        font.family: Style.uiFont
        font.pixelSize: Style.dp(13)
        color: Style.fg
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: _switch.toggled(!_switch.checked)
    }
}

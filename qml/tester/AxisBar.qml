// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// One axis: its name, a bar filled from the centre to the value (-1..1)
// and the value as a number.

import QtQuick
import QtQuick.Layouts

import Gremlin.Style

RowLayout {
    id: _axis

    property string name: ""
    property real value: 0.0

    spacing: Style.dp(10)

    Text {
        Layout.preferredWidth: Style.dp(56)
        text: _axis.name
        elide: Text.ElideRight
        font.family: Style.uiFont
        font.pixelSize: Style.dp(13)
        font.bold: true
        color: Style.fgStrong
    }

    Rectangle {
        id: _track
        objectName: "axisTrack"
        Layout.fillWidth: true
        Layout.preferredHeight: Style.dp(15)
        color: Style.bgWell
        border.color: Style.line
        radius: Style.dp(3)

        readonly property real clamped: Math.max(-1, Math.min(1, _axis.value))

        Rectangle {
            objectName: "axisFill"
            y: Style.dp(2)
            height: parent.height - Style.dp(4)
            x: _track.clamped < 0 ? _track.width / 2 * (1 + _track.clamped) : _track.width / 2
            width: Math.abs(_track.clamped) * _track.width / 2
            color: Style.accent
            radius: Style.dp(2)
        }
        Rectangle {
            x: parent.width / 2
            y: -Style.dp(2)
            width: 1
            height: parent.height + Style.dp(4)
            color: Style.lineStrong
        }
    }

    Text {
        Layout.preferredWidth: Style.dp(64)
        horizontalAlignment: Text.AlignRight
        text: (_axis.value >= 0 ? "+" : "\u2212") + Math.abs(_axis.value).toFixed(3)
        font.family: Style.monoFont
        font.pixelSize: Style.dp(13)
        color: Style.fg
    }
}

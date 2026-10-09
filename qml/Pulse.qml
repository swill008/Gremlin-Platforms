// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

import Gremlin.Style

// Points at a control for Help's "Show me ›" links (01 S139): a 2 px accent
// border over the control that fades three times in about 2 s, then removes
// itself. Make one with the control as its parent:
//     Qt.createComponent("Pulse.qml").createObject(control)
Rectangle {
    id: _pulse

    objectName: "helpPulse"
    anchors.fill: parent
    z: 10000
    color: "transparent"
    border.width: 2
    border.color: Style.accent
    radius: Style.dp(2)
    opacity: 0

    // The control it marks (its parent).
    readonly property Item target: parent
    readonly property bool running: _fades.running

    SequentialAnimation {
        id: _fades
        running: true
        loops: 3
        NumberAnimation { target: _pulse; property: "opacity"; from: 1; to: 1; duration: 250 }
        NumberAnimation { target: _pulse; property: "opacity"; from: 1; to: 0; duration: 417; easing.type: Easing.InQuad }
        onFinished: _pulse.destroy()
    }
}

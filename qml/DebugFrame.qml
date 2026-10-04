// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

import Gremlin.Style
import Gremlin.UI
import "helpers.js" as Helpers

// Red debug mode (gremlin/ui/debug_mode.py adds this to every window): while
// Diagnostic logs is ALL or the Live log feed runs, a subtle red frame and a
// DEBUG badge at the top. Only the badge takes clicks (it opens the Live Log
// Reader); everything else passes through to the window.
Item {
    id: _frame

    anchors.fill: parent
    z: 1000000
    visible: _mode.active

    readonly property real edge: 28
    readonly property real strength: 0.28
    readonly property color red: Style.danger

    DebugMode {
        id: _mode
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: Qt.rgba(_frame.red.r, _frame.red.g, _frame.red.b, 0.55)
        border.width: 1
    }
    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: _frame.edge
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(_frame.red.r, _frame.red.g, _frame.red.b, _frame.strength) }
            GradientStop { position: 1; color: "transparent" }
        }
    }
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: _frame.edge
        gradient: Gradient {
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 1; color: Qt.rgba(_frame.red.r, _frame.red.g, _frame.red.b, _frame.strength) }
        }
    }
    Rectangle {
        anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
        width: _frame.edge
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Qt.rgba(_frame.red.r, _frame.red.g, _frame.red.b, _frame.strength) }
            GradientStop { position: 1; color: "transparent" }
        }
    }
    Rectangle {
        anchors { top: parent.top; bottom: parent.bottom; right: parent.right }
        width: _frame.edge
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 1; color: Qt.rgba(_frame.red.r, _frame.red.g, _frame.red.b, _frame.strength) }
        }
    }

    Rectangle {
        id: _badge
        anchors.horizontalCenter: parent.horizontalCenter
        y: 0
        width: _label.implicitWidth + Style.dp(24)
        height: _label.implicitHeight + Style.dp(6)
        radius: Style.dp(3)
        color: _badgeMouse.containsMouse ? Qt.darker(_frame.red, 1.15) : _frame.red

        Text {
            id: _label
            anchors.centerIn: parent
            text: "DEBUG"
            color: "white"
            font.bold: true
            font.pixelSize: Style.dp(12)
            font.letterSpacing: Style.dp(1.5)
        }

        MouseArea {
            id: _badgeMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: Helpers.createComponent("DialogLiveLog.qml")
        }
    }
}

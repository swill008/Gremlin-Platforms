// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// One device in the "All devices" view: name, section, small axis bars,
// a strip of button lights and the hats as numbers.

import QtQuick
import QtQuick.Layouts

import Gremlin.Style

Rectangle {
    id: _card

    property var device: ({})
    signal clicked()

    implicitHeight: _col.implicitHeight + Style.dp(18)
    color: Style.bgCard
    border.color: _area.containsMouse ? Style.lineStrong : Style.line
    radius: Style.dp(6)

    ColumnLayout {
        id: _col
        anchors.fill: parent
        anchors.margins: Style.dp(9)
        spacing: Style.dp(4)

        Text {
            Layout.fillWidth: true
            text: _card.device.name || ""
            elide: Text.ElideRight
            font.family: Style.uiFont
            font.pixelSize: Style.dp(13)
            font.bold: true
            color: Style.fgStrong
        }
        Text {
            Layout.fillWidth: true
            text: _card.device.section || ""
            elide: Text.ElideRight
            font.family: Style.uiFont
            font.pixelSize: Style.dp(11)
            color: Style.fgMuted
        }
        Repeater {
            model: _card.device.axes || []
            delegate: Rectangle {
                required property var modelData
                readonly property real v: Math.max(-1, Math.min(1, modelData))
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(6)
                color: Style.bgWell
                radius: Style.dp(2)
                Rectangle {
                    x: parent.v < 0 ? parent.width / 2 * (1 + parent.v) : parent.width / 2
                    width: Math.abs(parent.v) * parent.width / 2
                    height: parent.height
                    color: Style.accent
                    radius: Style.dp(2)
                }
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Style.dp(2)
            Repeater {
                model: _card.device.buttons || []
                delegate: Rectangle {
                    required property var modelData
                    width: Style.dp(6)
                    height: Style.dp(6)
                    radius: Style.dp(1)
                    color: modelData ? Style.ok : Style.bgWell
                    border.color: Style.line
                    border.width: modelData ? 0 : 1
                }
            }
        }
        Text {
            Layout.fillWidth: true
            visible: (_card.device.hats || []).length > 0
            text: "Hats: " + (_card.device.hats || []).map(function (h) {
                return h < 0 ? "centre" : h + "°"
            }).join(" · ")
            font.family: Style.monoFont
            font.pixelSize: Style.dp(11)
            color: Style.fg
        }
    }

    MouseArea {
        id: _area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: _card.clicked()
    }
}

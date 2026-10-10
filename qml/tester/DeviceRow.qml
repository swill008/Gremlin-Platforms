// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// One device in the left list: verdict icon, name, tag, sub line and the
// activity dot that blinks while its values change.

import QtQuick
import QtQuick.Layouts

import Gremlin.Style

Rectangle {
    id: _row

    property var row: ({})
    property bool selected: false
    property bool active: false
    signal clicked()

    readonly property bool bad: row.verdict === "bad" || row.verdict === "missing"

    implicitHeight: _content.implicitHeight + Style.dp(14)
    color: selected ? Style.bgSelected
        : bad ? Style.alpha(Style.dangerFill, 0.45)
        : _area.containsMouse && row.live ? Style.alpha(Style.bgHover, 0.4)
        : Style.clear

    Rectangle {
        width: Style.dp(3)
        height: parent.height
        color: _row.selected ? Style.accent : _row.bad ? Style.danger : Style.clear
    }

    GridLayout {
        id: _content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.dp(14)
        anchors.rightMargin: Style.dp(14)
        columns: 4
        columnSpacing: Style.dp(8)
        rowSpacing: Style.dp(2)

        Text {
            Layout.preferredWidth: Style.dp(18)
            horizontalAlignment: Text.AlignHCenter
            text: _row.row.icon || ""
            font.family: Style.uiFont
            font.pixelSize: Style.dp(14)
            font.weight: Font.ExtraBold
            color: _row.row.iconStyle === "ok" ? Style.ok
                : _row.row.iconStyle === "no" ? Style.dangerText
                : _row.row.iconStyle === "q" ? Style.warn
                : Style.fgDisabled
        }
        Text {
            objectName: "rowName"
            Layout.fillWidth: true
            text: _row.row.name || ""
            elide: Text.ElideRight
            font.family: Style.uiFont
            font.pixelSize: Style.dp(13)
            font.bold: true
            color: _row.row.greyed ? Style.fgMuted : Style.fgStrong
        }
        TesterTag {
            text: _row.row.tag || ""
            kind: _row.row.tagStyle || ""
        }
        Rectangle {
            id: _dot
            objectName: "activityDot"
            Layout.preferredWidth: Style.dp(8)
            Layout.preferredHeight: Style.dp(8)
            radius: width / 2
            visible: !!_row.row.live
            color: _row.active ? Style.live : Style.bgRaised
            border.color: Style.line

            SequentialAnimation on opacity {
                running: _row.active
                loops: Animation.Infinite
                onStopped: _dot.opacity = 1
                NumberAnimation { to: 0.3; duration: 180 }
                NumberAnimation { to: 1.0; duration: 180 }
            }
        }
        Item { Layout.preferredWidth: Style.dp(18) }
        Text {
            Layout.columnSpan: 3
            Layout.fillWidth: true
            text: _row.row.sub || ""
            visible: text !== ""
            elide: Text.ElideRight
            textFormat: Text.PlainText
            font.family: Style.uiFont
            font.pixelSize: Style.dp(11.5)
            color: Style.fgMuted
        }
    }

    MouseArea {
        id: _area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: _row.clicked()
    }
}

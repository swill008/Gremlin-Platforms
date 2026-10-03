// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// One setting in an Options window (main Options and Button Map Options):
// its name, a short description under it, and its control on the right. A
// wide control (a list, a path, a custom panel) goes under the text instead.
// Rows sit in a ConfigGroup card; every row after the first has a divider.
Item {
    id: root

    property string title: "No title"
    property string explanation: ""
    property bool divider: false
    property bool wide: false
    default property alias optionElement: _control.data

    implicitHeight: _layout.implicitHeight + Style.dp(20)

    Rectangle {
        visible: root.divider
        width: parent.width
        height: Style.dp(1)
        color: Style.line
    }

    GridLayout {
        id: _layout

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.dp(14)
        anchors.rightMargin: Style.dp(14)
        columns: root.wide ? 1 : 2
        columnSpacing: Style.dp(16)
        rowSpacing: Style.dp(8)

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Style.dp(2)

            Label {
                Layout.fillWidth: true
                text: root.title
                color: Style.fgStrong
                font.pixelSize: Style.dp(14)
                wrapMode: Text.WordWrap
            }
            Label {
                Layout.fillWidth: true
                visible: root.explanation.length > 0
                text: root.explanation
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
                wrapMode: Text.WordWrap
            }
        }

        ColumnLayout {
            id: _control

            Layout.fillWidth: root.wide
            Layout.alignment: root.wide ? Qt.AlignLeft : (Qt.AlignRight | Qt.AlignVCenter)
            Layout.maximumWidth: root.wide ? -1 : Style.dp(360)
        }
    }
}

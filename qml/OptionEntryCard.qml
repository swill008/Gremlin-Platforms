// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import "helpers.js" as Helpers
import Gremlin.Style

Pane {
    id: root

    property string title: "No title"
    property string explanation: "No description"
    default property alias optionElement: _optionElementContainer.data

    padding: Style.dp(10)

    background: Rectangle {
        color: Style.isDarkMode ? Universal.chromeLowColor : Style.bgCard
        border.color: (Style.isDarkMode ? Universal.chromeMediumColor : Style._light.bar)
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right

        ColumnLayout {
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: Style.dp(400)
            Layout.minimumWidth: Style.dp(400)
            Layout.maximumWidth: Style.dp(400)
            Layout.rightMargin: Style.dp(10)

            Label {
                Layout.fillWidth: true

                text: root.title

                font.weight: 600
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true

                text: root.explanation

                // horizontalAlignment: Text.AlignJustify
                wrapMode: Text.WordWrap
            }
        }

        Item {
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: Style.dp(5)
            Layout.fillWidth: true
            Layout.preferredHeight: _optionElementContainer.implicitHeight

            ColumnLayout {
                id: _optionElementContainer

                anchors.left: parent.left
                anchors.right: parent.right
            }
        }
    }

}

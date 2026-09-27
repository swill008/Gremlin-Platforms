// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style
import "help_topics.js" as HelpTopics

Window {
    id: _win
    width: 920
    height: 640
    minimumWidth: 720
    minimumHeight: 480
    title: qsTr("User Guide")
    color: Style.background
    Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "help"
        defaultWidth: 920
        defaultHeight: 640
    }

    property var _topics: HelpTopics.topics()
    property int _index: 0

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        anchors.bottomMargin: 58
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 260
            Layout.fillHeight: true
            color: "#111113"
            border.color: "#3F3F46"
            radius: 3

            ListView {
                id: _contents
                anchors.fill: parent
                anchors.margins: 6
                clip: true
                model: _win._topics
                currentIndex: _win._index
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                section.property: "section"
                section.delegate: Label {
                    required property string section
                    width: _contents.width
                    text: section
                    color: "#E4E4E7"
                    font.pixelSize: 18
                    font.bold: true
                    leftPadding: 8
                    topPadding: 14
                    bottomPadding: 6
                }
                delegate: ItemDelegate {
                    required property int index
                    required property string title
                    width: _contents.width
                    text: title
                    font.pixelSize: 13
                    highlighted: index === _win._index
                    onClicked: _win._index = index
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            Label {
                text: _win._topics[_win._index].title
                color: "#E4E4E7"
                font.pixelSize: 20
                font.bold: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#111113"
                border.color: "#3F3F46"
                radius: 3

                ScrollView {
                    id: _topicScroll
                    anchors.fill: parent
                    anchors.margins: 12
                    clip: true
                    Text {
                        width: _topicScroll.availableWidth
                        text: _win._topics[_win._index].body
                        textFormat: Text.RichText
                        wrapMode: Text.WordWrap
                        color: "#E4E4E7"
                        font.pixelSize: 14
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: qsTr("Close")
                    onClicked: _win.close()
                }
            }
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}

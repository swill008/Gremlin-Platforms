// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style
import "help_topics.js" as HelpTopics

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 920
    height: 640
    minimumWidth: Style.dp(720)
    minimumHeight: Style.dp(480)
    title: qsTr("User Guide")
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "help"
        defaultWidth: Style.dp(920)
        defaultHeight: Style.dp(640)
    }

    property string initialSection: ""
    property var _topics: HelpTopics.topics()
    property int _index: 0

    function _showSection(name) {
        if (!name)
            return
        for (var i = 0; i < _topics.length; ++i) {
            if (_topics[i].section === name) {
                _index = i
                return
            }
        }
    }

    Component.onCompleted: _showSection(initialSection)
    onInitialSectionChanged: _showSection(initialSection)

    RowLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(12)

        Rectangle {
            Layout.preferredWidth: Style.dp(260)
            Layout.fillHeight: true
            color: "#111113"
            border.color: "#3F3F46"
            radius: Style.dp(3)

            ListView {
                id: _contents
                anchors.fill: parent
                anchors.margins: Style.dp(6)
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
                    font.pixelSize: Style.dp(18)
                    font.bold: true
                    font.underline: true
                    leftPadding: Style.dp(8)
                    topPadding: Style.dp(14)
                    bottomPadding: Style.dp(6)
                }
                delegate: ItemDelegate {
                    required property int index
                    required property string title
                    width: _contents.width
                    text: title
                    font.pixelSize: Style.dp(13)
                    highlighted: index === _win._index
                    onClicked: _win._index = index
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.dp(8)

            Label {
                text: _win._topics[_win._index].title
                color: "#E4E4E7"
                font.pixelSize: Style.dp(20)
                font.bold: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#111113"
                border.color: "#3F3F46"
                radius: Style.dp(3)

                ScrollView {
                    id: _topicScroll
                    anchors.fill: parent
                    anchors.margins: Style.dp(12)
                    clip: true
                    Text {
                        width: _topicScroll.availableWidth
                        text: _win._topics[_win._index].body
                        textFormat: Text.RichText
                        wrapMode: Text.WordWrap
                        color: "#E4E4E7"
                        font.pixelSize: Style.dp(14)
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
}

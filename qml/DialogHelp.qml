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

    EscapeCloses { host: _win }
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 920
    height: 640
    minimumWidth: Style.fitWidth(Style.dp(720), Screen)
    minimumHeight: Style.fitHeight(Style.dp(480), Screen)
    title: qsTr("User Guide")
    color: Style.background
    U.Universal.theme: Style.theme

    // "" for the program's User Guide; "buttonmap" for the Button Map's own
    // guide (DialogButtonMapGuide.qml), which covers only the Button Map.
    property string guide: ""

    ToolWindowMemory {
        host: _win
        name: _win.guide.length ? "help-" + _win.guide : "help"
        defaultWidth: Style.dp(920)
        defaultHeight: Style.dp(640)
    }

    property string initialSection: ""
    property var _topics: guide === "buttonmap" ? HelpTopics.buttonMapTopics() : HelpTopics.topics()
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

    // Shows a section's first topic, also when the window is already open.
    function showSection(name) {
        _showSection(name)
        // The section's heading at the top of the contents, its topics below.
        Qt.callLater(function() {
            _contents.positionViewAtIndex(_index, ListView.Beginning)
            _contents.contentY = Math.max(_contents.originY, _contents.contentY - Style.dp(48))
        })
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
            color: Style.bgPage
            border.color: Style.line
            radius: Style.dp(3)

            ListView {
                id: _contents
                anchors.fill: parent
                anchors.margins: Style.dp(6)
                clip: true
                model: _win._topics
                currentIndex: _win._index
                // Jumping to a section (Button Map's F1) scrolls the list to it.
                onCurrentIndexChanged: Qt.callLater(function() { _contents.positionViewAtIndex(currentIndex, ListView.Contain) })
                Component.onCompleted: Qt.callLater(function() { _contents.positionViewAtIndex(currentIndex, ListView.Contain) })
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                section.property: "section"
                section.delegate: Label {
                    required property string section
                    width: _contents.width
                    text: section
                    color: Style.fg
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
                color: Style.fg
                font.pixelSize: Style.dp(20)
                font.bold: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Style.bgPage
                border.color: Style.line
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
                        color: Style.fg
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

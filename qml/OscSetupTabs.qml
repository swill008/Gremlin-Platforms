// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// OSC's Module Setup settings as tabs: Server · Output · Feedback · Discovery
// (D-09-OSC-TABS). One server model is shared by the first, second and last
// tab; each tab scrolls on its own. Every change is written to OSC's file at
// once (D-09-OSC-FILE point 4), not by Save Module.
ColumnLayout {
    id: _root
    objectName: "oscSetupTabs"
    spacing: 0

    property alias model: _model
    property alias current: _strip.current

    // A box still being typed in when the window closes is saved too.
    function commit() {
        _server.commit()
    }

    OscServerModel {
        id: _model
        onMessageChanged: {
            if (message.length)
                _message.show(message, messageFailed)
            else
                _message.clear()
        }
    }

    // The tab strip, as the Button Map's ToolRow.
    Rectangle {
        id: _strip
        property int current: 0
        readonly property var names: ["Server", "Output", "Feedback", "Discovery"]
        Layout.fillWidth: true
        implicitHeight: Style.dp(30)
        color: Style.bgRaised

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Style.lineStrong
        }
        Row {
            x: Style.dp(6)
            y: Style.dp(4)
            spacing: Style.dp(2)
            Repeater {
                model: _strip.names
                delegate: Rectangle {
                    id: _tab
                    required property string modelData
                    required property int index
                    readonly property bool open: _strip.current === index
                    objectName: "oscTab" + modelData
                    width: _tabText.implicitWidth + Style.dp(24)
                    // The open tab covers the strip's line: it joins the page.
                    height: _strip.height - Style.dp(4) + (open ? 1 : 0)
                    color: open || _tabArea.containsMouse ? Style.bgCard : Style.clear
                    border.color: open ? Style.lineStrong : Style.line
                    border.width: 1
                    Rectangle {
                        width: parent.width
                        height: Style.dp(2)
                        color: Style.accent
                        visible: _tab.open
                    }
                    Label {
                        id: _tabText
                        anchors.centerIn: parent
                        text: _tab.modelData
                        font.pixelSize: Style.dp(12)
                        font.bold: _tab.open
                        color: _tab.open ? Style.fg : Style.fgMuted
                    }
                    MouseArea {
                        id: _tabArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _strip.current = _tab.index
                    }
                }
            }
        }
    }

    // The open tab's page.
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: Style.bgCard
        border.color: Style.lineStrong
        border.width: 1

        StackLayout {
            id: _pages
            anchors.fill: parent
            anchors.margins: 1
            currentIndex: _strip.current

            OscServerTab {
                id: _server
                server: _model
            }
            OscOutputTab {
                server: _model
            }
            // CFB's section, unchanged, in its own scrolling page.
            Flickable {
                id: _feedbackPage
                objectName: "oscFeedbackPage"
                clip: true
                contentWidth: width
                contentHeight: _feedback.implicitHeight + Style.dp(24)
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {
                    policy: _feedbackPage.contentHeight > _feedbackPage.height
                            ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                }
                OscFeedbackSection {
                    id: _feedback
                    x: Style.dp(14)
                    y: Style.dp(12)
                    width: _feedbackPage.width - Style.dp(28)
                }
            }
            OscDiscoveryTab {
                server: _model
            }
        }
    }

    MessageLine {
        id: _message
        objectName: "oscServerMessage"
        Layout.fillWidth: true
        Layout.topMargin: Style.dp(4)
    }
}

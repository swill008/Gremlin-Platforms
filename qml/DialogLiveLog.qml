// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts

import Gremlin.Style
import Gremlin.UI

Window {
    id: _win
    width: 960
    height: 640
    minimumWidth: 720
    minimumHeight: 480
    title: qsTr("Live Log Reader")
    color: Style.background
    Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "liveLog"
        defaultWidth: 960
        defaultHeight: 640
    }

    LiveLog {
        id: _log
    }

    property bool _follow: true

    Timer {
        interval: 400
        running: _win.visible
        repeat: true
        onTriggered: _log.refresh()
    }

    Connections {
        target: _log
        function onTextChanged() {
            var at = _view.cursorPosition
            _view.text = _log.text
            if (_win._follow) {
                _view.cursorPosition = _view.length
                Qt.callLater(_flick.scrollToEnd)
            } else {
                _view.cursorPosition = Math.min(at, _view.length)
            }
        }
    }

    Component.onCompleted: _log.refresh()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Label {
            text: _log.path
            color: "#A1A1AA"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#111113"
            border.color: "#3F3F46"
            radius: 3

            Flickable {
                id: _flick
                anchors.fill: parent
                anchors.margins: 2
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.HorizontalAndVerticalFlick
                contentWidth: _view.width
                contentHeight: _view.height

                function scrollToEnd() {
                    contentY = Math.max(0, contentHeight - height)
                }

                onMovementEnded: {
                    _win._follow = height <= 0
                            || (contentY + height >= contentHeight - 16)
                }

                TextEdit {
                    id: _view
                    width: Math.max(_flick.width - 14, contentWidth + 16)
                    height: Math.max(_flick.height - 14, contentHeight + 16)
                    leftPadding: 8
                    topPadding: 8
                    rightPadding: 8
                    bottomPadding: 8
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.NoWrap
                    color: "#E4E4E7"
                    selectionColor: "#3F3F46"
                    selectedTextColor: "#E4E4E7"
                    font.family: "Consolas"
                    font.pixelSize: 13
                    textFormat: TextEdit.PlainText
                }

                ScrollBar.vertical: ScrollBar {
                    id: _vbar
                    policy: ScrollBar.AlwaysOn
                    contentItem: Rectangle {
                        implicitWidth: 8
                        radius: 4
                        color: _vbar.pressed ? "#E4E4E7" : "#71717A"
                    }
                    background: Rectangle {
                        implicitWidth: 12
                        color: "#27272A"
                    }
                }
                ScrollBar.horizontal: ScrollBar {
                    id: _hbar
                    policy: ScrollBar.AlwaysOn
                    contentItem: Rectangle {
                        implicitHeight: 8
                        radius: 4
                        color: _hbar.pressed ? "#E4E4E7" : "#71717A"
                    }
                    background: Rectangle {
                        implicitHeight: 12
                        color: "#27272A"
                    }
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                text: qsTr("Clear log")
                onClicked: {
                    _win._follow = true
                    _log.clear()
                }
            }
            Button {
                text: qsTr("Copy all logs")
                onClicked: _log.copyAll()
            }
        }
    }
}

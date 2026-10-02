// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Style
import Gremlin.UI

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 960
    height: 640
    minimumWidth: Style.dp(720)
    minimumHeight: Style.dp(480)
    title: qsTr("Live Log Reader")
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "liveLog"
        defaultWidth: Style.dp(960)
        defaultHeight: Style.dp(640)
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
        anchors.margins: Style.dp(12)
        spacing: Style.dp(8)

        Label {
            text: _log.path
            color: Style.fgMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Style.bgPage
            border.color: Style.line
            radius: Style.dp(3)

            Flickable {
                id: _flick
                anchors.fill: parent
                anchors.margins: Style.dp(2)
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
                    width: Math.max(_flick.width - Style.dp(14), contentWidth + Style.dp(16))
                    height: Math.max(_flick.height - Style.dp(14), contentHeight + Style.dp(16))
                    leftPadding: Style.dp(8)
                    topPadding: Style.dp(8)
                    rightPadding: Style.dp(8)
                    bottomPadding: Style.dp(8)
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.NoWrap
                    color: Style.fg
                    selectionColor: Style.line
                    selectedTextColor: Style.fg
                    font.family: "Consolas"
                    font.pixelSize: Style.dp(13)
                    textFormat: TextEdit.PlainText
                }

                ScrollBar.vertical: ScrollBar {
                    id: _vbar
                    policy: ScrollBar.AlwaysOn
                    contentItem: Rectangle {
                        implicitWidth: Style.dp(8)
                        radius: Style.dp(4)
                        color: _vbar.pressed ? Style.fg : Style.fgDisabled
                    }
                    background: Rectangle {
                        implicitWidth: Style.dp(12)
                        color: Style.bgRaised
                    }
                }
                ScrollBar.horizontal: ScrollBar {
                    id: _hbar
                    policy: ScrollBar.AlwaysOn
                    contentItem: Rectangle {
                        implicitHeight: Style.dp(8)
                        radius: Style.dp(4)
                        color: _hbar.pressed ? Style.fg : Style.fgDisabled
                    }
                    background: Rectangle {
                        implicitHeight: Style.dp(12)
                        color: Style.bgRaised
                    }
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                text: qsTr("Clear log")
                onClicked: {
                    _clearGate.confirmThen("Clear log?",
                        "Clear everything shown here? (The log starts empty at every start anyway.)",
                        "Clear", function() {
                            _win._follow = true
                            _log.clear()
                        }, null, true)
                }
            }
            Button {
                text: qsTr("Copy all logs")
                onClicked: _log.copyAll()
            }
        }
    }

    DismissibleDialog {
        id: _clearGate
    }
}

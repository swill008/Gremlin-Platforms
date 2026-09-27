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
            if (_win._follow)
                _view.cursorPosition = _view.length
            else
                _view.cursorPosition = Math.min(at, _view.length)
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

            TextArea {
                id: _view
                anchors.fill: parent
                anchors.margins: 8
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.NoWrap
                color: "#E4E4E7"
                font.family: "Consolas"
                font.pixelSize: 13
                background: null
                clip: true
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
            }

            Connections {
                target: _view.contentItem
                ignoreUnknownSignals: true
                function onMovementEnded() {
                    var flick = _view.contentItem
                    if (!flick)
                        return
                    _win._follow = flick.height <= 0
                            || (flick.contentY + flick.height >= flick.contentHeight - 16)
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button {
                text: qsTr("Copy all logs")
                onClicked: _log.copyAll()
            }
        }
    }
}

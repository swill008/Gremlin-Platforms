// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The Logs tab: pick a log (tester.log, Gremlin's trace.log / system.log,
// the DirectInput reader's dill_debug.log), follow it live, find, show only
// warnings, copy, open its folder. Reads only.

import QtQuick
import QtQuick.Layouts

import Gremlin.Style

Rectangle {
    id: _logs
    objectName: "logsView"
    color: Style.bgPage

    // The shown lines; refreshed on tester.logChanged so the scroll position
    // can be kept (or moved to the end while following).
    property var lines: tester.logLines

    readonly property var sources: tester.logSources
    readonly property int sourceIndex: {
        for (let i = 0; i < sources.length; ++i)
            if (sources[i].id === tester.logSource)
                return i
        return 0
    }

    function showLine(pos) {
        if (pos >= 0)
            _lineList.positionViewAtIndex(pos, ListView.Center)
    }

    Connections {
        target: tester
        function onLogChanged() {
            const y = _lineList.contentY
            _logs.lines = tester.logLines
            if (tester.logFollow)
                _lineList.positionViewAtEnd()
            else
                _lineList.contentY = Math.min(y, Math.max(0,
                    _lineList.contentHeight - _lineList.height))
        }
    }
    Component.onCompleted: if (tester.logFollow) _lineList.positionViewAtEnd()

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Tool bar.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: _bar.implicitHeight + Style.dp(20)
            z: 10
            color: Style.bgPage

            RowLayout {
                id: _bar
                anchors.fill: parent
                anchors.leftMargin: Style.dp(12)
                anchors.rightMargin: Style.dp(12)
                spacing: Style.dp(10)

                Text {
                    text: "Log"
                    font.family: Style.uiFont
                    font.pixelSize: Style.dp(13)
                    color: Style.fg
                }
                TesterCombo {
                    objectName: "logPicker"
                    Layout.preferredWidth: Style.dp(270)
                    choices: _logs.sources.map(s => s.label)
                    currentIndex: _logs.sourceIndex
                    onPicked: index => tester.logSource = _logs.sources[index].id
                }
                TesterSwitch {
                    objectName: "logFollow"
                    text: "Follow"
                    checked: tester.logFollow
                    onToggled: on => {
                        tester.logFollow = on
                        if (on)
                            _lineList.positionViewAtEnd()
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: _find.implicitHeight + Style.dp(12)
                    color: Style.bgWell
                    radius: Style.dp(3)
                    border.color: _find.activeFocus ? Style.accent : Style.lineStrong

                    TextInput {
                        id: _find
                        objectName: "logFind"
                        anchors.fill: parent
                        anchors.leftMargin: Style.dp(10)
                        anchors.rightMargin: Style.dp(70)
                        verticalAlignment: TextInput.AlignVCenter
                        clip: true
                        text: tester.logFind
                        font.family: Style.uiFont
                        font.pixelSize: Style.dp(13)
                        color: Style.fg
                        selectByMouse: true
                        onTextEdited: tester.logFind = text
                        Keys.onReturnPressed: event => _logs.showLine(
                            (event.modifiers & Qt.ShiftModifier)
                                ? tester.findPrevious() : tester.findNext())
                        Keys.onEnterPressed: _logs.showLine(tester.findNext())
                        Keys.onEscapePressed: {
                            text = ""
                            tester.logFind = ""
                        }
                    }
                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: Style.dp(10)
                        anchors.verticalCenter: parent.verticalCenter
                        visible: _find.text === ""
                        text: "Find…"
                        font.family: Style.uiFont
                        font.pixelSize: Style.dp(13)
                        color: Style.fgDisabled
                    }
                    Text {
                        objectName: "logFindCount"
                        anchors.right: parent.right
                        anchors.rightMargin: Style.dp(10)
                        anchors.verticalCenter: parent.verticalCenter
                        visible: tester.logFind !== ""
                        text: tester.logFindCount === 0 ? "none"
                            : tester.logFindCount
                              + (tester.logFindCount === 1 ? " line" : " lines")
                        font.family: Style.uiFont
                        font.pixelSize: Style.dp(12)
                        color: Style.fgMuted
                    }
                }
                Text {
                    text: "Show"
                    font.family: Style.uiFont
                    font.pixelSize: Style.dp(13)
                    color: Style.fg
                }
                TesterCombo {
                    objectName: "logShow"
                    Layout.preferredWidth: Style.dp(120)
                    choices: ["All", "Warnings"]
                    currentIndex: tester.logWarningsOnly ? 1 : 0
                    onPicked: index => tester.logWarningsOnly = index === 1
                }
                TesterButton {
                    objectName: "logCopy"
                    text: "Copy"
                    onClicked: tester.copyLog()
                }
                TesterButton {
                    objectName: "logOpenFolder"
                    text: "Open folder"
                    visible: tester.logFolder !== ""
                    onClicked: tester.openLogFolder()
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Style.line
            }
        }

        // Note: last 512 KB only, file not found, kept in memory only.
        Text {
            objectName: "logNote"
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(12)
            Layout.rightMargin: Style.dp(12)
            Layout.topMargin: Style.dp(8)
            visible: tester.logNote !== ""
            text: tester.logNote
            wrapMode: Text.Wrap
            font.family: Style.uiFont
            font.pixelSize: Style.dp(12)
            color: Style.fgMuted
        }

        // The lines.
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Style.dp(12)
            Layout.bottomMargin: Style.dp(10)
            color: Style.bgWell
            border.color: Style.line
            radius: Style.dp(6)

            ListView {
                id: _lineList
                objectName: "logLines"
                anchors.fill: parent
                anchors.margins: 1
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: _logs.lines
                // A user scroll away from the end stops Follow.
                onMovementEnded: if (tester.logFollow && !atYEnd) tester.logFollow = false

                delegate: Rectangle {
                    id: _line
                    required property var modelData
                    required property int index
                    objectName: "logLine"
                    readonly property bool warn: !!modelData.warn
                    readonly property bool match: !!modelData.match
                    readonly property string lineText: modelData.text || ""
                    width: _lineList.width - Style.dp(8)
                    implicitHeight: _lineText.implicitHeight + Style.dp(6)
                    height: implicitHeight
                    color: index === tester.logFindPos ? Style.alpha(Style.findCurrent, 0.35)
                        : match ? Style.alpha(Style.findMatch, 0.16)
                        : warn ? Style.alpha(Style.warn, 0.14)
                        : Style.clear

                    Text {
                        id: _lineText
                        x: Style.dp(10)
                        y: Style.dp(3)
                        width: parent.width - Style.dp(20)
                        textFormat: Text.StyledText
                        wrapMode: Text.WrapAnywhere
                        font.family: Style.monoFont
                        font.pixelSize: Style.dp(12)
                        color: _line.warn ? Style.warn : Style.fg
                        text: (_line.modelData.time
                               ? "<font color=\"" + Style.fgMuted + "\">"
                                 + _line.modelData.time + "</font>&nbsp;&nbsp;"
                               : "")
                            + _line.lineText.replace(/&/g, "&amp;").replace(/</g, "&lt;")
                                .replace(/>/g, "&gt;")
                    }
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Style.alpha(Style.line, 0.4)
                    }
                }

                // Scroll bar.
                Rectangle {
                    visible: _lineList.visibleArea.heightRatio < 1
                    parent: _lineList
                    x: _lineList.width - Style.dp(7)
                    y: _lineList.visibleArea.yPosition * _lineList.height
                    width: Style.dp(5)
                    height: Math.max(Style.dp(20), _lineList.visibleArea.heightRatio * _lineList.height)
                    radius: width / 2
                    color: Style.lineStrong
                }
            }
            Text {
                anchors.centerIn: parent
                visible: _logs.lines.length === 0
                text: tester.logWarningsOnly ? "No warnings in this log." : "This log is empty."
                font.family: Style.uiFont
                font.pixelSize: Style.dp(13)
                color: Style.fgMuted
            }
        }

        // Status line.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: _logStatus.implicitHeight + Style.dp(14)
            color: Style.bgCard
            Rectangle { width: parent.width; height: 1; color: Style.line }
            Text {
                id: _logStatus
                objectName: "logStatus"
                anchors.fill: parent
                anchors.leftMargin: Style.dp(12)
                verticalAlignment: Text.AlignVCenter
                text: tester.logStatus + (tester.logFollow ? "   ·   Following" : "")
                font.family: Style.uiFont
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
        }
    }
}

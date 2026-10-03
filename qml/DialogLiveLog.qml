// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Style
import Gremlin.UI

// Debug → Live Log Reader. Config: what the program read and saved this run
// (logs.txt), for checking how profiles, modules and other files load.
// Debug: the diagnostic log files that Options → General → Diagnostics
// writes (system, script and event logs).
ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win
    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1000
    height: 640
    minimumWidth: Style.dp(720)
    minimumHeight: Style.dp(480)
    title: qsTr("Live Log Reader")
    color: Style.background
    U.Universal.theme: Style.theme

    ToolWindowMemory {
        host: _win
        name: "liveLog"
        defaultWidth: Style.dp(1000)
        defaultHeight: Style.dp(640)
    }

    LiveLog {
        id: _log
    }

    DebugLog {
        id: _debug
        warningColor: String(Style.warn)
        errorColor: String(Style.dangerText)
    }

    readonly property bool _onDebug: _tabs.currentIndex === 1

    Timer {
        interval: 400
        running: _win.visible
        repeat: true
        onTriggered: _win._onDebug ? _debug.refresh() : _log.refresh()
    }

    Connections {
        target: _log
        function onTextChanged() { _configView.show(_log.text) }
    }

    Connections {
        target: _debug
        function onChanged() { _debugView.show(_debug.html) }
    }

    Component.onCompleted: {
        _log.refresh()
        _debug.refresh()
        _debugView.show(_debug.html)
    }

    // A read-only log area that keeps to the end while it is scrolled there.
    component LogView: Rectangle {
        id: _area

        property bool follow: true
        property int textFormat: TextEdit.PlainText

        function show(text) {
            var at = _view.cursorPosition
            _view.text = text
            if (follow) {
                _view.cursorPosition = _view.length
                Qt.callLater(_flick.scrollToEnd)
            } else {
                _view.cursorPosition = Math.min(at, _view.length)
            }
        }

        function toEnd() {
            follow = true
            Qt.callLater(_flick.scrollToEnd)
        }

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
                _area.follow = height <= 0
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
                textFormat: _area.textFormat
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(8)

        TabBar {
            id: _tabs
            Layout.fillWidth: true
            TabButton { text: "Config"; width: implicitWidth }
            TabButton { text: "Debug"; width: implicitWidth }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: _tabs.currentIndex

            // Config: what was read and saved this run.
            ColumnLayout {
                spacing: Style.dp(8)

                Label {
                    text: _log.path
                    color: Style.fgMuted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                LogView {
                    id: _configView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }

                RowLayout {
                    Layout.alignment: Qt.AlignRight
                    Button {
                        text: qsTr("Clear Log")
                        onClicked: {
                            _clearGate.confirmThen("Clear Log?",
                                "Clear everything shown here? (The log starts empty at every start anyway.)",
                                "Clear", function() {
                                    _configView.follow = true
                                    _log.clear()
                                }, null, true)
                        }
                    }
                    Button {
                        text: qsTr("Copy All Logs")
                        onClicked: _log.copyAll()
                    }
                }
            }

            // Debug: the diagnostic log files.
            ColumnLayout {
                spacing: Style.dp(8)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(8)

                    Label { text: "Log" }
                    ComboBox {
                        id: _file
                        textRole: "text"
                        valueRole: "value"
                        implicitContentWidthPolicy: ComboBox.WidestText
                        model: [
                            { text: "System", value: "system" },
                            { text: "Scripts", value: "user" },
                            { text: "Events", value: "event" }
                        ]
                        onActivated: {
                            _debug.file = currentValue
                            _debugView.toEnd()
                        }
                    }

                    Label {
                        text: "Show"
                        Layout.leftMargin: Style.dp(8)
                    }
                    ComboBox {
                        id: _level
                        implicitContentWidthPolicy: ComboBox.WidestText
                        model: ["All", "Info", "Warning", "Error"]
                        onActivated: _debug.level = currentText
                    }

                    TextField {
                        id: _find
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(8)
                        placeholderText: "Find"
                        onTextChanged: _debug.find = text
                    }
                }

                // Nothing new is written while Diagnostic logs is Off.
                Rectangle {
                    visible: !_debug.loggingOn
                    Layout.fillWidth: true
                    implicitHeight: _offText.implicitHeight + Style.dp(16)
                    radius: Style.dp(3)
                    color: Style.noteFill
                    border.color: Style.noteLine

                    Label {
                        id: _offText
                        anchors.fill: parent
                        anchors.margins: Style.dp(8)
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                        color: Style.noteText
                        text: "Diagnostic logs are off, so nothing new is written. "
                            + "Pick a level below to turn them on."
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: _debug.path
                        color: Style.fgMuted
                        elide: Text.ElideMiddle
                    }
                    Label {
                        color: Style.fgMuted
                        text: !_debug.exists ? "No file yet"
                            : _debug.shownCount === _debug.totalCount
                                ? _debug.totalCount + " entries"
                                : _debug.shownCount + " of " + _debug.totalCount + " entries"
                    }
                }

                // A big file: only its end is read until asked for all of it.
                RowLayout {
                    visible: _debug.truncated
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: "Showing the last " + _debug.tailKilobytes
                            + " KB of a large file."
                        color: Style.fgMuted
                        wrapMode: Text.WordWrap
                    }
                    Button {
                        text: qsTr("Load Whole File")
                        onClicked: {
                            _debugView.follow = true
                            _debug.loadWhole()
                        }
                    }
                }

                LogView {
                    id: _debugView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    textFormat: TextEdit.RichText
                }

                // Levels on the left, buttons on the right; on a narrow window
                // the buttons go under the levels.
                GridLayout {
                    id: _bottom
                    Layout.fillWidth: true
                    columns: _bottom.width >= _levels.implicitWidth + _actions.implicitWidth
                        + Style.dp(24) ? 2 : 1
                    columnSpacing: Style.dp(16)
                    rowSpacing: Style.dp(8)

                    // The same setting as Options → General → Diagnostics.
                    RowLayout {
                        id: _levels
                        spacing: Style.dp(8)
                        Label {
                            text: "Diagnostic logs"
                            color: Style.fgSoft
                        }
                        OptionLogLevel {
                            // Wide enough for "Warning" on its button.
                            Layout.preferredWidth: Style.dp(400)
                            Layout.minimumWidth: Style.dp(400)
                        }
                    }

                    RowLayout {
                        id: _actions
                        Layout.fillWidth: true

                        Item { Layout.fillWidth: true }

                        Button {
                            text: qsTr("Clear Log")
                            enabled: _debug.exists
                            onClicked: {
                                _clearGate.confirmThen("Clear Log?",
                                    "Empty " + _debug.path.split(/[\\/]/).pop()
                                        + "? Everything in it is removed for good.",
                                    "Clear", function() {
                                        _debugView.follow = true
                                        _debug.clear()
                                    }, null, true)
                            }
                        }
                        Button {
                            text: qsTr("Open Logs Folder")
                            onClicked: _debug.openFolder()
                        }
                        Button {
                            text: qsTr("Copy Shown")
                            onClicked: _debug.copyShown()
                        }
                    }
                }
            }
        }
    }

    DismissibleDialog {
        id: _clearGate
    }
}

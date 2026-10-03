// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Dialogs
import QtQuick.Layouts

import Gremlin.Style
import Gremlin.UI

// Debug → Live Log Reader.
// Config: what the program read and saved this run (logs.txt), for checking
// how profiles, modules and other files load.
// Debug: the diagnostic log files that Options → General → Diagnostics
// writes; Live adds every line the program logs as it happens, whatever
// the Diagnostic logs level (gremlin/log_feed.py).
// Input Monitor: each input the running profile handles and the actions it
// ran (gremlin/input_monitor.py).
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
        dividerColor: String(Style.dangerText)
    }

    InputMonitor {
        id: _monitor
        mutedColor: String(Style.fgMuted)
    }

    // Live and the Input Monitor stop when the window closes.
    function _stopAll() {
        _debug.live = false
        _monitor.monitoring = false
    }
    onClosing: _stopAll()
    Component.onDestruction: _stopAll()

    Timer {
        interval: 400
        running: _win.visible
        repeat: true
        onTriggered: {
            if (_tabs.currentIndex === 0)
                _log.refresh()
            else if (_tabs.currentIndex === 1)
                _debug.refresh()
            else
                _monitor.refresh()
        }
    }

    Connections {
        target: _log
        function onTextChanged() { _configView.show(_log.text) }
    }

    Connections {
        target: _debug
        function onChanged() {
            _debugView.show(_debug.html)
            _file.currentIndex = _file.indexOfValue(_debug.file)
        }
    }

    Connections {
        target: _monitor
        function onChanged() { _monitorView.show(_monitor.html) }
    }

    Component.onCompleted: {
        _log.refresh()
        _debug.refresh()
        _debugView.show(_debug.html)
        _monitor.refresh()
        _monitorView.show(_monitor.html)
    }

    // A red on/off button (Live, Monitor): dark red with ○ when off, bright
    // red with ● when on.
    component RedToggle: Button {
        id: _toggle

        property string caption: ""
        property string tipOn: ""
        property string tipOff: ""

        checkable: true
        ToolTip.visible: hovered
        ToolTip.delay: 500
        ToolTip.text: checked ? tipOn : tipOff
        contentItem: Label {
            text: (_toggle.checked ? "● " : "○ ") + _toggle.caption
            color: "white"
            font.bold: _toggle.checked
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitWidth: Style.dp(92)
            implicitHeight: Style.dp(32)
            radius: Style.dp(3)
            color: _toggle.checked
                ? (_toggle.hovered ? Style.dangerHover : Style.danger)
                : (_toggle.hovered ? Style.dangerHover : Style.dangerFill)
            border.color: Style.danger
            border.width: Style.dp(1)
        }
    }

    // A yellow note across the page.
    component Note: Rectangle {
        property alias text: _noteText.text

        Layout.fillWidth: true
        implicitHeight: _noteText.implicitHeight + Style.dp(16)
        radius: Style.dp(3)
        color: Style.noteFill
        border.color: Style.noteLine

        Label {
            id: _noteText
            anchors.fill: parent
            anchors.margins: Style.dp(8)
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            color: Style.noteText
        }
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
                height: Math.max(_flick.height - Style.dp(14), contentHeight + topPadding + bottomPadding)
                leftPadding: Style.dp(8)
                topPadding: Style.dp(8)
                rightPadding: Style.dp(8)
                // Room under the last line (clear of the horizontal scroll bar)
                // so the end of the log is plain to see.
                bottomPadding: Style.dp(48)
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
            // A red dot while Live or the monitor runs, seen from any tab.
            TabButton { text: _debug.live ? "Debug ●" : "Debug"; width: implicitWidth }
            TabButton {
                text: _monitor.monitoring ? "Input Monitor ●" : "Input Monitor"
                width: implicitWidth
            }
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

            // Debug: the diagnostic log files; with Live on, a session view that
            // keeps what was shown and adds every new line as it happens.
            ColumnLayout {
                spacing: Style.dp(8)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(8)

                    RedToggle {
                        id: _liveButton
                        caption: "Live"
                        checked: _debug.live
                        tipOff: "Catch every line the program logs, as it happens"
                        tipOn: "Stop Live (what was caught stays on screen)"
                        onToggled: {
                            _debug.live = checked
                            _debugView.toEnd()
                        }
                    }
                    CheckBox {
                        text: "Start empty"
                        checked: _debug.startEmpty
                        onToggled: _debug.startEmpty = checked
                        ToolTip.visible: hovered
                        ToolTip.delay: 500
                        ToolTip.text: "When Live starts, clear the view first "
                            + "(otherwise it keeps what is shown and adds to it)"
                    }

                    Label {
                        text: "Log"
                        Layout.leftMargin: Style.dp(8)
                    }
                    ComboBox {
                        id: _file
                        textRole: "text"
                        valueRole: "value"
                        implicitContentWidthPolicy: ComboBox.WidestText
                        // All logs only while a Live session is shown.
                        model: _debug.session
                            ? [
                                { text: "All logs", value: "all" },
                                { text: "System", value: "system" },
                                { text: "Scripts", value: "user" },
                                { text: "Events", value: "event" }
                            ]
                            : [
                                { text: "System", value: "system" },
                                { text: "Scripts", value: "user" },
                                { text: "Events", value: "event" }
                            ]
                        onModelChanged: currentIndex = indexOfValue(_debug.file)
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
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(8)
                        placeholderText: "Find"
                        onTextChanged: _debug.find = text
                    }
                }

                // Nothing new is written while Diagnostic logs is Off (Live
                // still catches everything).
                Note {
                    visible: !_debug.session && !_debug.loggingOn
                    text: "Diagnostic logs are off, so nothing new is written. "
                        + "Pick a level below to turn them on, or use Live."
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: _debug.live
                            ? "Live: every line the program logs, as it happens "
                                + "(the files keep the Diagnostic logs level)"
                            : _debug.session ? "Live stopped. Showing this session."
                            : _debug.path
                        color: _debug.live ? Style.dangerText : Style.fgMuted
                        elide: Text.ElideMiddle
                    }
                    Button {
                        visible: _debug.session && !_debug.live
                        text: qsTr("Show Log File")
                        onClicked: {
                            _debug.showFile()
                            _debugView.toEnd()
                        }
                    }
                    Label {
                        color: Style.fgMuted
                        text: !_debug.session && !_debug.exists ? "No file yet"
                            : _debug.shownCount === _debug.totalCount
                                ? _debug.totalCount + " entries"
                                : _debug.shownCount + " of " + _debug.totalCount + " entries"
                    }
                }

                // A big file: only its end is read until asked for all of it.
                RowLayout {
                    visible: _debug.truncated && !_debug.session
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

                    // The same setting as Options → General → Diagnostics:
                    // what is written to the files.
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
                            // A session: empty the view only, never a file.
                            text: _debug.session ? qsTr("Clear View") : qsTr("Clear Log")
                            enabled: _debug.session || _debug.exists
                            onClicked: {
                                if (_debug.session) {
                                    _debugView.follow = true
                                    _debug.clearView()
                                    return
                                }
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
                        Button {
                            visible: _debug.session
                            text: qsTr("Save Feed…")
                            onClicked: _saveFeed.open()
                        }
                    }
                }
            }

            // Input Monitor: each input the running profile handles, as it
            // happens, with the actions it ran.
            ColumnLayout {
                spacing: Style.dp(8)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(8)

                    RedToggle {
                        caption: "Monitor"
                        checked: _monitor.monitoring
                        tipOff: "Show each input the running profile handles, as it happens"
                        tipOn: "Stop the Input Monitor"
                        onToggled: {
                            _monitor.monitoring = checked
                            _monitorView.toEnd()
                        }
                    }

                    TextField {
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(8)
                        placeholderText: "Find"
                        onTextChanged: _monitor.find = text
                    }
                }

                Note {
                    visible: _monitor.monitoring && !_monitor.running
                    text: "No profile is running. Run the profile, then use your "
                        + "devices: each input shows here with the actions it ran."
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: _monitor.monitoring
                            ? "Inputs the running profile handles, as they happen"
                            : "Click Monitor to watch inputs and the actions they run."
                        color: _monitor.monitoring ? Style.dangerText : Style.fgMuted
                        elide: Text.ElideRight
                    }
                    Label {
                        color: Style.fgMuted
                        text: _monitor.shownCount === _monitor.totalCount
                            ? _monitor.totalCount + " entries"
                            : _monitor.shownCount + " of " + _monitor.totalCount + " entries"
                    }
                }

                LogView {
                    id: _monitorView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    textFormat: TextEdit.RichText
                }

                RowLayout {
                    Layout.fillWidth: true

                    CheckBox {
                        text: "Inputs with no actions"
                        checked: _monitor.showUnbound
                        onToggled: _monitor.showUnbound = checked
                        ToolTip.visible: hovered
                        ToolTip.delay: 500
                        ToolTip.text: "Also show inputs that have no actions (dimmed)"
                    }

                    Item { Layout.fillWidth: true }

                    Button {
                        text: qsTr("Clear")
                        onClicked: {
                            _monitorView.follow = true
                            _monitor.clear()
                        }
                    }
                    Button {
                        text: qsTr("Copy Shown")
                        onClicked: _monitor.copyShown()
                    }
                }
            }
        }
    }

    FileDialog {
        id: _saveFeed
        title: "Save Feed"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: ["Text files (*.txt)"]
        onAccepted: _debug.saveTo(String(selectedFile))
    }

    DismissibleDialog {
        id: _clearGate
    }
}

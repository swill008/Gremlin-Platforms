// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

// Tools › Drivers (06 S185): vJoy, ViGEmBus and HidHide with what is
// installed and what is available, the vJoy device choice, and Apply, which
// asks first (S187, DialogDriverPrompt) and then sends the jobs to Gremlin
// Device Helper. Progress, the result of every step and any restart show
// here.
ApplicationWindow {
    id: _win
    objectName: "driversWindow"
    font.pixelSize: Style.fontSize
    width: 640
    height: 720
    minimumWidth: Style.fitWidth(Style.dp(560), Screen)
    minimumHeight: Style.fitHeight(Style.dp(420), Screen)
    title: "Drivers"
    color: Style.background
    U.Universal.theme: Style.theme

    readonly property DriversModel drivers: _drv

    // The HidHide update's step 2 (06 S186): true runs the install once the
    // window is open (Main's start prompt and Home's Finish update set it).
    property bool finishHidHideOnOpen: false
    property bool _finishing: false
    // What the open prompt is for: "apply", "run", "info", "inuse",
    // "alike", "restart" or "lost".
    property string _promptMode: "apply"

    // "Restart later" hides the restart buttons until the next Apply.
    property bool _restartDismissed: false
    // Shown when Apply had nothing to do (or could not start).
    property string _note: ""

    ToolWindowMemory {
        host: _win
        name: "drivers"
        defaultWidth: Style.dp(640)
        defaultHeight: Style.dp(720)
    }

    EscapeCloses { host: _win }

    // Made by ModelFactory (PYSIDE-1407: PySide6 never frees a Python object
    // QML declares); it lives as long as this window.
    readonly property DriversModel _drv: ModelFactory.create("DriversModel", _win)

    // Our own Run holds vJoy devices: they aren't "in use by another
    // program" (S185); the model reads the busy ids again after Stop.
    // Set by hand, not with Binding: runActive's notify signal is the
    // shared "changed".
    function _syncRunActive() {
        _drv.runActive = typeof backend !== "undefined" && backend !== null
                         && backend.gremlinActive === true
    }
    Connections {
        target: typeof backend !== "undefined" ? backend : null
        ignoreUnknownSignals: true
        function onActivityChanged() { _win._syncRunActive() }
    }

    // Yes on the Run box: Run is stopped, then the busy ids are read again
    // before the in-use box (bounded: 15 s).
    property bool _waitingStop: false
    property bool _waitingInUse: false

    Timer {
        id: _stopTimer
        interval: 15000
        onTriggered: {
            if (!_win._waitingStop && !_win._waitingInUse)
                return
            _win._waitingStop = false
            _win._waitingInUse = false
            _win._note = "Run did not stop, so nothing was started."
        }
    }

    Connections {
        target: typeof backend !== "undefined" ? backend : null
        ignoreUnknownSignals: true
        function onActivityChanged() {
            if (!_win._waitingStop || backend.gremlinActive)
                return
            _win._waitingStop = false
            _win._waitingInUse = true
            // runActive turning false starts the re-read; inUseRead follows.
            if (!_drv.runActive)
                _drv.refreshInUse()
        }
    }

    Connections {
        target: _drv
        function onInUseRead() {
            if (!_win._waitingInUse)
                return
            _win._waitingInUse = false
            _stopTimer.stop()
            _win._askInfo()
        }
    }

    function _runFinish() {
        if (!finishHidHideOnOpen || _finishing)
            return
        finishHidHideOnOpen = false
        _finishing = true
        _restartDismissed = false
        if (!_drv.finishHidHide()) {
            _finishing = false
            _note = "Nothing was started."
        }
    }
    Component.onCompleted: {
        _syncRunActive()
        _drv.reload()
        Qt.callLater(_runFinish)
    }
    onFinishHidHideOnOpenChanged: if (finishHidHideOnOpen) Qt.callLater(_runFinish)

    Connections {
        target: _drv
        function onFinished() {
            if (!_win._finishing)
                return
            _win._finishing = false
            _win._promptMode = "restart"
            _prompt.title = "HidHide is installed: one more restart"
            _prompt.body = "Restart Windows to finish. Your devices aren't hidden until then."
            _prompt.okText = "Restart now"
            _prompt.cancelText = "Restart later"
            _prompt.open()
        }
    }

    // After the results (06 S185): the vJoy update lost devices, so the
    // model's text and Repair Now / Repair Later.
    Connections {
        target: _drv
        function onFinished() {
            if (_win._finishing)
                return
            var lost = String(_drv.lostText())
            if (lost.length === 0)
                return
            _win._promptMode = "lost"
            _prompt.title = "The vJoy update lost a device"
            _prompt.body = lost
            _prompt.okText = "Repair Now"
            _prompt.cancelText = "Repair Later"
            _prompt.open()
        }
    }

    // Apply: the prompt says what will happen and when; OK runs it.
    function startApply() {
        _note = ""
        var text = String(_drv.describe())
        if (text.length === 0) {
            _note = "Nothing to apply."
            return
        }
        _promptMode = "apply"
        _prompt.okText = "OK"
        _prompt.cancelText = "Cancel"
        _prompt.title = "Apply driver changes"
        _prompt.body = text
        _prompt.open()
    }

    // After OK: devices another program holds get a Yes/No box first
    // (D-01-VJOY-IN-USE), then devices that can't be told apart
    // (D-01-VJOY-COUNTDOWN); the texts and the rules are the model's.
    function _applyOrAsk() {
        // Our own Run first (user 2026-11-22, "a"): Yes stops it.
        if (_drv.runActive && _drv.changesVjoy()) {
            _promptMode = "run"
            _prompt.okText = "Yes"
            _prompt.cancelText = "No"
            _prompt.title = "Run is on"
            _prompt.body = "Run stops while the vJoy devices change. Continue?"
            _prompt.open()
            return
        }
        _askInfo()
    }

    // Before a vJoy update (06 S185): the information box, OK only.
    function _askInfo() {
        var info = String(_drv.updateInfo())
        if (info.length > 0) {
            _promptMode = "info"
            _prompt.okText = "OK"
            _prompt.cancelText = ""
            _prompt.title = "vJoy update and your devices"
            _prompt.body = info
            _prompt.open()
            return
        }
        _askInUse()
    }

    function _stopRunThenAsk() {
        _waitingStop = true
        _stopTimer.restart()
        backend.toggleActiveState()
    }

    function _askInUse() {
        var inUse = String(_drv.inUseWarning())
        if (inUse.length > 0) {
            _promptMode = "inuse"
            _prompt.okText = "Yes"
            _prompt.cancelText = "No"
            _prompt.title = "Devices in use"
            _prompt.body = inUse
            _prompt.open()
            return
        }
        _askAlike()
    }

    function _askAlike() {
        var alike = String(_drv.alikeWarning())
        if (alike.length > 0) {
            _promptMode = "alike"
            _prompt.okText = "Yes"
            _prompt.cancelText = "No"
            _prompt.title = "Devices that can't be told apart"
            _prompt.body = alike
            _prompt.open()
            return
        }
        _runApply()
    }

    function _runApply() {
        _restartDismissed = false
        if (!_drv.apply())
            _note = "Nothing was started."
    }

    // The device list's columns, shared by the heading band and the rows.
    readonly property int _nameW: Style.dp(64)
    readonly property int _axisW: Style.dp(30)
    readonly property int _buttonsW: Style.dp(76)
    readonly property int _hatsW: Style.dp(60)
    readonly property int _removeW: Style.dp(28)
    readonly property int _colGap: Style.dp(2)

    DialogDriverPrompt {
        id: _prompt
        parent: Overlay.overlay
        okText: "OK"
        cancelText: "Cancel"
        onAccepted: {
            if (_win._promptMode === "restart") {
                _drv.restartNow()
                return
            }
            if (_win._promptMode === "run") {
                Qt.callLater(_win._stopRunThenAsk)
                return
            }
            if (_win._promptMode === "lost") {
                _win._restartDismissed = false
                Qt.callLater(_win._repairNow)
                return
            }
            if (_win._promptMode === "info") {
                Qt.callLater(_win._askInUse)
                return
            }
            if (_win._promptMode === "inuse") {
                Qt.callLater(_win._askAlike)
                return
            }
            if (_win._promptMode === "alike") {
                _win._runApply()
                return
            }
            // The box reopens once this one has closed.
            Qt.callLater(_win._applyOrAsk)
        }
        onRejected: {
            if (_win._promptMode === "lost")
                _drv.repairLater()
        }
    }

    function _repairNow() {
        if (!_drv.repairNow())
            _note = "Nothing was started."
    }

    // The page fits the window: the device list grows until there is no
    // more room, then scrolls inside itself (S185). The window itself
    // scrolls only when even the smallest list doesn't fit.
    ScrollView {
        id: _page
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            id: _col
            width: _page.availableWidth
            height: Math.max(_page.availableHeight,
                             implicitHeight - _vjoySection.Layout.preferredHeight
                             + _vjoySection.Layout.minimumHeight)
            spacing: Style.dp(12)

            Item { Layout.preferredHeight: Style.dp(4) }

            Label {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                wrapMode: Text.Wrap
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
                text: "Tick the drivers to install or update, then press Apply. "
                      + "Windows asks for administrator permission once."
            }

            // One row per driver.
            Repeater {
                model: _drv.rows
                delegate: Rectangle {
                    required property var modelData
                    objectName: "driverRow_" + modelData.key
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(16)
                    Layout.rightMargin: Style.dp(16)
                    implicitHeight: _rowLayout.implicitHeight + Style.dp(20)
                    radius: Style.dp(3)
                    color: Style.bgPage
                    border.color: Style.line

                    RowLayout {
                        id: _rowLayout
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.margins: Style.dp(10)
                        spacing: Style.dp(10)

                        CheckBox {
                            objectName: "driverTick_" + modelData.key
                            visible: modelData.tickable
                            checked: modelData.ticked
                            onToggled: _drv.setTicked(modelData.key, checked)
                        }
                        Label {
                            objectName: "driverName_" + modelData.key
                            text: modelData.name
                            font.bold: true
                            color: Style.fg
                            wrapMode: Text.Wrap
                            Layout.preferredWidth: Style.dp(100)
                        }
                        Label {
                            objectName: "driverLabel_" + modelData.key
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: modelData.state === "missing" ? Style.warn
                                   : (modelData.state === "older" ? Style.warn : Style.fgMuted)
                            text: modelData.label
                        }
                    }
                }
            }

            // The vJoy devices (S185, layout b like setup's page): heading,
            // Preset and Devices, the bordered list, the hint and the
            // Showing line.
            Rectangle {
                id: _vjoySection
                objectName: "vjoySection"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                // Full size: every row; smallest: two rows.
                Layout.preferredHeight: _vjoy.implicitHeight + Style.dp(20)
                Layout.maximumHeight: Layout.preferredHeight
                Layout.minimumHeight: Layout.preferredHeight - _rows.contentHeight
                                      + Math.min(_rows.contentHeight, Style.dp(80))
                radius: Style.dp(3)
                color: Style.bgPage
                border.color: Style.line

                ColumnLayout {
                    id: _vjoy
                    anchors.fill: parent
                    anchors.margins: Style.dp(10)
                    spacing: Style.dp(8)

                    Label {
                        objectName: "vjoyHeading"
                        text: "vJoy devices"
                        font.bold: true
                        color: Style.fg
                    }

                    RowLayout {
                        spacing: Style.dp(10)
                        Label { text: "Preset"; color: Style.fg }
                        ComboBox {
                            id: _preset
                            objectName: "vjoyPreset"
                            Layout.preferredWidth: Style.dp(200)
                            model: _drv.presets
                            currentIndex: Math.max(0, _drv.presets.indexOf(_drv.vjoyPreset))
                            onActivated: _drv.setPreset(currentText)
                        }
                        Item { Layout.preferredWidth: Style.dp(6) }
                        Label { text: "Devices"; color: Style.fg }
                        SpinBox {
                            objectName: "vjoyDeviceCount"
                            from: 1
                            to: 16
                            value: _drv.vjoyDevices.length
                            onValueModified: _drv.setDeviceCount(value)
                        }
                    }

                    // One bordered list: the column headings in a grey band,
                    // then a row per device.
                    Rectangle {
                        objectName: "vjoyList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: _band.height + _rows.contentHeight + 2
                        color: Style.bgCard
                        border.color: Style.line

                        Rectangle {
                            id: _band
                            objectName: "vjoyHeadBand"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 1
                            height: Style.dp(24)
                            color: Style.bgRaised

                            Row {
                                anchors.left: parent.left
                                anchors.leftMargin: Style.dp(6)
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: _win._colGap

                                Item { width: _win._nameW; height: 1 }
                                Repeater {
                                    model: _drv.vjoyAxes
                                    delegate: Label {
                                        required property var modelData
                                        required property int index
                                        objectName: "vjoyHead_" + index
                                        width: _win._axisW
                                        horizontalAlignment: Text.AlignHCenter
                                        text: modelData.label
                                        color: Style.fg
                                        font.pixelSize: Style.dp(12)
                                    }
                                }
                                Label {
                                    objectName: "vjoyHeadButtons"
                                    width: _win._buttonsW
                                    leftPadding: Style.dp(4)
                                    text: "Buttons"
                                    color: Style.fg
                                    font.pixelSize: Style.dp(12)
                                }
                                Label {
                                    objectName: "vjoyHeadHats"
                                    width: _win._hatsW
                                    leftPadding: Style.dp(4)
                                    text: "Hats"
                                    color: Style.fg
                                    font.pixelSize: Style.dp(12)
                                }
                            }
                        }

                        Flickable {
                            id: _rows
                            objectName: "vjoyRows"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: _band.bottom
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: 1
                            anchors.rightMargin: 1
                            anchors.bottomMargin: 1
                            clip: true
                            contentWidth: width
                            contentHeight: _rowsColumn.height
                            boundsBehavior: Flickable.StopAtBounds
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                            // The rows in view, for the Showing line.
                            function firstShown() {
                                var top = contentY + 0 * _rowsColumn.height
                                for (var i = 0; i < _devRows.count; i++) {
                                    var r = _devRows.itemAt(i)
                                    if (r && r.y + r.height > top + 1)
                                        return i
                                }
                                return 0
                            }
                            function shownCount() {
                                if (contentHeight <= height + 1)
                                    return _devRows.count
                                var first = firstShown()
                                var bottom = contentY + height
                                var n = 0
                                for (var i = first; i < _devRows.count; i++) {
                                    var r = _devRows.itemAt(i)
                                    if (!r || r.y >= bottom - 1)
                                        break
                                    n++
                                }
                                return n
                            }

                            Column {
                                id: _rowsColumn
                                width: _rows.width

                                Repeater {
                                    id: _devRows
                                    model: _drv.vjoyDevices
                                    delegate: Rectangle {
                                        id: _dev
                                        required property var modelData
                                        required property int index
                                        objectName: "vjoyRow_" + index
                                        width: _rowsColumn.width
                                        height: _devCol.implicitHeight + Style.dp(4)
                                        color: index % 2 ? Style.bgPage : Style.bgCard

                                        function push(buttons, hats) {
                                            _drv.setDevice(_dev.index, _dev.modelData.axes, buttons, hats)
                                        }

                                        Column {
                                            id: _devCol
                                            x: Style.dp(6)
                                            anchors.verticalCenter: parent.verticalCenter

                                            Row {
                                                spacing: _win._colGap

                                                Label {
                                                    objectName: "vjoyName_" + _dev.index
                                                    width: _win._nameW
                                                    height: _buttons.height
                                                    verticalAlignment: Text.AlignVCenter
                                                    text: "vJoy " + _dev.modelData.id
                                                    // In use by another program (S185, user
                                                    // 2026-11-22: 1a, 2a): the name in red, the
                                                    // words only on hover.
                                                    property bool inUse: _dev.modelData.inUse === true
                                                    color: inUse ? Style.danger : Style.fg
                                                    font.bold: inUse
                                                    HoverHandler { id: _nameHover }
                                                    ToolTip.visible: inUse && _nameHover.hovered
                                                    property string tip: inUse ? "in use by another program" : ""
                                                    ToolTip.text: tip
                                                }
                                                Repeater {
                                                    model: _drv.vjoyAxes
                                                    delegate: Item {
                                                        required property var modelData
                                                        width: _win._axisW
                                                        height: _buttons.height
                                                        CheckBox {
                                                            objectName: "vjoyAxis_" + _dev.index + "_" + modelData.name
                                                            anchors.centerIn: parent
                                                            padding: 0
                                                            spacing: 0
                                                            // The text is for tests and screen readers; the
                                                            // heading band shows it.
                                                            text: modelData.label
                                                            contentItem: Item {}
                                                            // Just the box: no room for the text.
                                                            implicitWidth: indicator.implicitWidth
                                                            implicitHeight: indicator.implicitHeight
                                                            checked: _dev.modelData.axes.indexOf(modelData.name) >= 0
                                                            // The last ticked axis can't be unticked (the model's rule).
                                                            enabled: !_drv.busy
                                                                     && _dev.modelData.locked.indexOf(modelData.name) < 0
                                                            onToggled: _drv.setAxis(_dev.index, modelData.name, checked)
                                                        }
                                                    }
                                                }
                                                ComboBox {
                                                    id: _buttons
                                                    objectName: "vjoyButtons_" + _dev.index
                                                    width: _win._buttonsW
                                                    enabled: !_drv.busy
                                                    model: 129
                                                    currentIndex: _dev.modelData.buttons
                                                    onActivated: _dev.push(currentIndex, _dev.modelData.hats)
                                                }
                                                ComboBox {
                                                    objectName: "vjoyHats_" + _dev.index
                                                    width: _win._hatsW
                                                    enabled: !_drv.busy
                                                    model: 5
                                                    currentIndex: _dev.modelData.hats
                                                    onActivated: _dev.push(_dev.modelData.buttons, currentIndex)
                                                }
                                                ToolButton {
                                                    objectName: "vjoyRemove_" + _dev.index
                                                    width: _win._removeW
                                                    height: _buttons.height
                                                    text: "✕"
                                                    enabled: !_drv.busy && _drv.vjoyDevices.length > 1
                                                    ToolTip.visible: hovered
                                                    ToolTip.text: "Remove vJoy " + _dev.modelData.id
                                                    onClicked: _drv.removeDevice(_dev.index)
                                                }
                                            }
                                        }
                                    }
                                }

                                // Devices the vJoy update lost (06 S185), as
                                // they were, each with its own Repair.
                                Repeater {
                                    model: _drv.vjoyLost
                                    delegate: Rectangle {
                                        id: _lostRow
                                        required property var modelData
                                        required property int index
                                        objectName: "vjoyLostRow_" + index
                                        width: _rowsColumn.width
                                        height: _lostLine.implicitHeight + Style.dp(8)
                                        color: Style.bgPage

                                        RowLayout {
                                            id: _lostLine
                                            x: Style.dp(6)
                                            width: parent.width - Style.dp(12)
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: Style.dp(8)

                                            Label {
                                                objectName: "vjoyLostName_" + _lostRow.index
                                                Layout.preferredWidth: _win._nameW
                                                text: "vJoy " + _lostRow.modelData.id
                                                color: Style.warn
                                                font.bold: true
                                            }
                                            Label {
                                                objectName: "vjoyLostSummary_" + _lostRow.index
                                                Layout.fillWidth: true
                                                wrapMode: Text.Wrap
                                                text: _lostRow.modelData.summary
                                                color: Style.fgMuted
                                                font.pixelSize: Style.dp(12)
                                            }
                                            Label {
                                                objectName: "vjoyLostMark_" + _lostRow.index
                                                text: "lost in the vJoy update"
                                                color: Style.warn
                                                font.pixelSize: Style.dp(12)
                                            }
                                            Button {
                                                objectName: "vjoyLostRepair_" + _lostRow.index
                                                text: "Repair"
                                                enabled: !_drv.busy
                                                onClicked: {
                                                    _win._note = ""
                                                    _win._restartDismissed = false
                                                    if (!_drv.repairDevice(_lostRow.modelData.id))
                                                        _win._note = "Nothing was started."
                                                }
                                            }
                                        }
                                    }
                                }

                                // The last row of the list (S185): the whole
                                // line adds the lowest free id.
                                Rectangle {
                                    id: _addRow
                                    objectName: "vjoyAddRow"
                                    visible: _drv.addPreview !== ""
                                    width: _rowsColumn.width
                                    height: visible ? Style.dp(34) : 0
                                    color: _addMouse.containsMouse ? Style.bgHover : "transparent"

                                    Rectangle {
                                        anchors.top: parent.top
                                        width: parent.width
                                        height: 1
                                        color: Style.line
                                    }
                                    Label {
                                        objectName: "vjoyAddLabel"
                                        x: Style.dp(6)
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "+  Add device"
                                        color: _addMouse.containsMouse ? Style.fg : Style.fgMuted
                                        font.pixelSize: Style.dp(13)
                                    }
                                    Label {
                                        objectName: "vjoyAddPreview"
                                        anchors.right: parent.right
                                        anchors.rightMargin: Style.dp(12)
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: _drv.addPreview
                                        color: Style.fgMuted
                                        font.pixelSize: Style.dp(12)
                                    }
                                    MouseArea {
                                        id: _addMouse
                                        objectName: "vjoyAddMouse"
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: !_drv.busy
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: _drv.addDevice()
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.dp(10)
                        Label {
                            objectName: "vjoyHint"
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(12)
                            text: "Each device needs its own number of axes, buttons or hats, "
                                  + "so Gremlin-Platforms can tell them apart."
                        }
                        Label {
                            objectName: "vjoyShowing"
                            Layout.alignment: Qt.AlignRight | Qt.AlignTop
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(12)
                            text: _drv.showingText(
                                      _rows.contentY >= 0 && _rows.height > 0 && _rowsColumn.height >= 0
                                          ? _rows.firstShown() : 0,
                                      _rows.shownCount())
                        }
                    }

                    Label {
                        objectName: "vjoyWarning"
                        visible: _drv.vjoyWarning.length > 0
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Style.warn
                        text: _drv.vjoyWarning
                    }
                }
            }

            // Apply and the progress line.
            RowLayout {
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                spacing: Style.dp(10)

                Button {
                    objectName: "driversApply"
                    text: "Apply"
                    enabled: !_drv.busy
                    onClicked: _win.startApply()
                }
                Label {
                    objectName: "driversProgress"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Style.fg
                    text: _drv.busy ? (_drv.progress.length > 0 ? _drv.progress
                      : (_win._finishing ? "Installing HidHide " + _drv.pendingVersion + "…" : ""))
                      : _win._note
                }
            }

            // The result of every step.
            ColumnLayout {
                objectName: "driversResults"
                visible: _drv.results.length > 0
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                spacing: Style.dp(4)

                Repeater {
                    model: _drv.results
                    delegate: Label {
                        required property var modelData
                        required property int index
                        objectName: "driverResult_" + index
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: modelData.state === "failed" ? Style.danger : Style.fg
                        text: modelData.driver + ": " + modelData.message
                    }
                }
            }

            // After the steps, when Windows needs a restart.
            RowLayout {
                objectName: "driversRestart"
                visible: _drv.restartNeeded && !_win._restartDismissed
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                spacing: Style.dp(8)

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Style.warn
                    text: "Restart needed to finish."
                }
                Button {
                    objectName: "driversRestartNow"
                    text: "Restart now"
                    onClicked: _drv.restartNow()
                }
                Button {
                    objectName: "driversRestartLater"
                    text: "Restart later"
                    onClicked: _win._restartDismissed = true
                }
            }

            Item {
                Layout.fillHeight: true
                Layout.preferredHeight: Style.dp(8)
                Layout.minimumHeight: Style.dp(8)
            }
        }
    }
}

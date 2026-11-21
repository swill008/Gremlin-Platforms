// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

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

    readonly property alias drivers: _drv

    // The HidHide update's step 2 (06 S186): true runs the install once the
    // window is open (Main's start prompt and Home's Finish update set it).
    property bool finishHidHideOnOpen: false
    property bool _finishing: false
    // What the open prompt is for: "apply" or "restart".
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

    DriversModel {
        id: _drv
        Component.onCompleted: reload()
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
    Component.onCompleted: Qt.callLater(_runFinish)
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

    function _deviceText(d) {
        return "Device " + d.id + ": " + d.axes + " axes, " + d.buttons
               + " buttons, " + d.hats + " hats"
    }

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
            _win._restartDismissed = false
            if (!_drv.apply())
                _win._note = "Nothing was started."
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Style.dp(12)
            anchors.margins: Style.dp(16)

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

            // The vJoy devices.
            Rectangle {
                objectName: "vjoySection"
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                implicitHeight: _vjoy.implicitHeight + Style.dp(20)
                radius: Style.dp(3)
                color: Style.bgPage
                border.color: Style.line

                ColumnLayout {
                    id: _vjoy
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Style.dp(10)
                    spacing: Style.dp(8)

                    Label {
                        text: "vJoy devices"
                        font.bold: true
                        color: Style.fg
                    }

                    // What vJoy has now.
                    Label {
                        objectName: "vjoyCurrentTitle"
                        text: _drv.vjoyCurrent.length > 0 ? "Now:" : "Now: no vJoy devices found"
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                    }
                    Repeater {
                        model: _drv.vjoyCurrent
                        delegate: Label {
                            required property var modelData
                            objectName: "vjoyCurrent_" + modelData.id
                            text: _win._deviceText(modelData)
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(12)
                        }
                    }

                    RowLayout {
                        spacing: Style.dp(10)
                        Label { text: "Set up"; color: Style.fg }
                        ComboBox {
                            id: _preset
                            objectName: "vjoyPreset"
                            Layout.preferredWidth: Style.dp(220)
                            model: _drv.presets
                            currentIndex: Math.max(0, _drv.presets.indexOf(_drv.vjoyPreset))
                            onActivated: _drv.setPreset(currentText)
                        }
                    }

                    // Custom: the number of devices, then each one's size.
                    ColumnLayout {
                        objectName: "vjoyCustom"
                        visible: _drv.vjoyPreset === "Custom"
                        Layout.fillWidth: true
                        spacing: Style.dp(6)

                        RowLayout {
                            spacing: Style.dp(10)
                            Label { text: "Number of devices"; color: Style.fg }
                            SpinBox {
                                objectName: "vjoyDeviceCount"
                                from: 1
                                to: 16
                                value: _drv.vjoyDevices.length
                                onValueModified: _drv.setDeviceCount(value)
                            }
                        }

                        Repeater {
                            model: _drv.vjoyDevices
                            delegate: RowLayout {
                                id: _dev
                                required property var modelData
                                required property int index
                                spacing: Style.dp(8)

                                function push() {
                                    _drv.setDevice(_dev.index, _axes.value, _buttons.value, _hats.value)
                                }

                                Label {
                                    text: "Device " + modelData.id
                                    color: Style.fg
                                    Layout.preferredWidth: Style.dp(70)
                                }
                                Label { text: "Axes"; color: Style.fgMuted }
                                SpinBox {
                                    id: _axes
                                    objectName: "vjoyAxes_" + _dev.index
                                    from: 0
                                    to: 8
                                    value: modelData.axes
                                    onValueModified: _dev.push()
                                }
                                Label { text: "Buttons"; color: Style.fgMuted }
                                SpinBox {
                                    id: _buttons
                                    objectName: "vjoyButtons_" + _dev.index
                                    from: 0
                                    to: 128
                                    value: modelData.buttons
                                    onValueModified: _dev.push()
                                }
                                Label { text: "Hats"; color: Style.fgMuted }
                                SpinBox {
                                    id: _hats
                                    objectName: "vjoyHats_" + _dev.index
                                    from: 0
                                    to: 4
                                    value: modelData.hats
                                    onValueModified: _dev.push()
                                }
                            }
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

            Item { Layout.preferredHeight: Style.dp(8) }
        }
    }
}

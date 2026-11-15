// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

// Screen Saver Mode (12 S1-S15): Gremlin's own idle time from the keyboard
// and mouse only; when it runs out, the screen saver or the displays off.
// The status is read once a second while the window is open; the two
// checks list what keeps the PC awake.
ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win
    objectName: "screenSaverModeWindow"

    // Opens at the size it was left at (capped to the screen).
    ToolWindowMemory {
        host: _win
        name: "screenSaverMode"
        defaultWidth: Math.max(Style.dp(760), _win.minimumWidth)
        defaultHeight: Math.max(Style.dp(820), _win.minimumHeight)
    }
    width: 760
    height: 820
    minimumWidth: Style.fitWidth(Style.dp(620), Screen)
    minimumHeight: Style.fitHeight(Style.dp(480), Screen)
    title: "Screen Saver Mode"
    color: Style.background
    U.Universal.theme: Style.theme

    EscapeCloses { host: _win }

    ScreenSaverModeModel { id: _ssm }
    readonly property alias ssm: _ssm

    onVisibleChanged: _ssm.setOpen(visible)
    Component.onCompleted: _ssm.setOpen(visible)
    onClosing: _ssm.setOpen(false)

    // The typed wait (minutes) is saved when the box is left or Enter is
    // pressed; text that isn't a time goes back to what is saved.
    function commitWait() {
        if (!_ssm.setWaitText(_wait.text))
            _wait.text = _ssm.waitText
    }

    ScrollView {
        id: _scroll
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            id: _body
            width: _scroll.availableWidth
            spacing: Style.dp(10)

            Item { Layout.preferredHeight: Style.dp(6) }

            // S2: the on/off switch.
            Switch {
                id: _enabled
                objectName: "ssmEnabled"
                Layout.leftMargin: Style.dp(16)
                text: "Screen Saver Mode"
                font.bold: true
                property bool shown: _ssm.enabled
                onShownChanged: if (!pressed) checked = shown
                Component.onCompleted: checked = shown
                onToggled: _ssm.setEnabled(checked)
            }
            Label {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                wrapMode: Text.Wrap
                color: Style.fgMuted
                text: "Keeps its own idle time from your keyboard and mouse only, so sticks "
                      + "and other devices that never go quiet can't keep your screens on. "
                      + "Works only while Gremlin-Platforms is open."
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(16)
                spacing: Style.dp(8)

                // S4: one action.
                SectionHeading { Layout.fillWidth: true; text: "Action" }
                RowLayout {
                    spacing: Style.dp(16)
                    RadioButton {
                        objectName: "ssmActionScreenSaver"
                        text: "Screen saver"
                        checked: _ssm.action === "screen_saver"
                        onToggled: if (checked) _ssm.setAction("screen_saver")
                    }
                    RadioButton {
                        objectName: "ssmActionPowerOff"
                        text: "Power off displays"
                        checked: _ssm.action === "power_off"
                        onToggled: if (checked) _ssm.setAction("power_off")
                    }
                }

                // S5: empty shows (greyed) and uses Windows' time.
                SectionHeading { Layout.fillWidth: true; text: "Wait time" }
                RowLayout {
                    spacing: Style.dp(8)
                    TextField {
                        id: _wait
                        objectName: "ssmWaitBox"
                        Layout.preferredWidth: Style.dp(110)
                        placeholderText: _ssm.windowsWaitText
                        text: _ssm.waitText
                        validator: RegularExpressionValidator {
                            regularExpression: /^\s*\d{0,3}([.,]\d{0,2})?\s*(min)?\s*$/
                        }
                        onEditingFinished: _win.commitWait()
                        Connections {
                            target: _ssm
                            function onSettingsChanged() {
                                if (!_wait.activeFocus)
                                    _wait.text = _ssm.waitText
                            }
                        }
                    }
                    Label {
                        text: "min"
                        color: Style.fgMuted
                        visible: _wait.text.length > 0
                    }
                    ToolButton {
                        objectName: "ssmWaitClear"
                        text: "✕"
                        visible: _wait.text.length > 0
                        ToolTip.visible: hovered
                        ToolTip.text: "Use Windows' time"
                        onClicked: {
                            _wait.text = ""
                            _ssm.clearWait()
                        }
                    }
                    Label {
                        objectName: "ssmWindowsWait"
                        text: _ssm.windowsWaitLabel
                        color: _wait.text.length > 0 ? Style.fgMuted : Style.fg
                    }
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    text: "Type a time to use your own; clear it to go back to Windows' time."
                }

                // S7
                Switch {
                    objectName: "ssmHoldFullscreen"
                    text: "Hold off during full-screen programs"
                    property bool shown: _ssm.holdFullscreen
                    onShownChanged: if (!pressed) checked = shown
                    Component.onCompleted: checked = shown
                    onToggled: _ssm.setHoldFullscreen(checked)
                }

                // S9, S15: the status line.
                SectionHeading { Layout.fillWidth: true; text: "Status" }
                Label {
                    objectName: "ssmListening"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: _ssm.listeningText
                    color: !_ssm.enabled ? Style.fgMuted
                         : _ssm.listening ? Style.okText : Style.dangerText
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(24)
                    Label {
                        objectName: "ssmIdleText"
                        text: _ssm.idleText
                        color: Style.fg
                    }
                    Label {
                        objectName: "ssmWindowsIdleText"
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        text: _ssm.windowsIdleText
                        color: Style.fgMuted
                    }
                }
                Label {
                    objectName: "ssmHoldText"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                    text: _ssm.holdText
                    color: _ssm.onHold ? Style.warn : Style.fg
                }
                Label {
                    objectName: "ssmProblemText"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                    text: _ssm.problemText
                    color: Style.dangerText
                }

                // S12-S14: what keeps the PC awake.
                SectionHeading { Layout.fillWidth: true; text: "What keeps the PC awake" }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: Style.dp(16)
                    rowSpacing: Style.dp(4)

                    Button {
                        objectName: "ssmRefreshDevices"
                        text: _ssm.scanningDevices ? "Checking… (4 s)" : "Refresh Devices"
                        enabled: !_ssm.scanningDevices
                        onClicked: _ssm.refreshDevices()
                    }
                    Button {
                        objectName: "ssmRefreshPrograms"
                        text: _ssm.scanningPrograms ? "Checking…" : "🛡 Refresh Programs"
                        enabled: !_ssm.scanningPrograms
                        onClicked: _ssm.refreshPrograms()
                    }
                    Label {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        wrapMode: Text.Wrap
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                        text: "Lists the devices that never go quiet and keep Windows thinking "
                              + "someone is using the PC."
                    }
                    Label {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        wrapMode: Text.Wrap
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                        text: "Lists the programs asking Windows to keep the display on. "
                              + "Needs administrator rights each time."
                    }
                }

                // The devices list (S12): empty until the first press.
                RowLayout {
                    Layout.fillWidth: true
                    visible: _ssm.devices.length > 0
                    Label { text: "Device"; color: Style.fgMuted; Layout.fillWidth: true }
                    Label { text: "Reports / s"; color: Style.fgMuted }
                }
                ListView {
                    objectName: "ssmDeviceList"
                    Layout.fillWidth: true
                    Layout.preferredHeight: contentHeight
                    interactive: false
                    model: _ssm.devices
                    delegate: RowLayout {
                        required property var modelData
                        width: ListView.view.width
                        Label {
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            text: modelData.name
                            color: Style.fg
                        }
                        Label {
                            text: Math.round(modelData.rate)
                            color: Style.fg
                        }
                    }
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    text: _ssm.devicesMessage
                }

                // The programs list (S13) with Ignore this program (S14).
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(6)
                    visible: _ssm.programs.length > 0
                    Label { text: "Program"; color: Style.fgMuted; Layout.fillWidth: true }
                    Label { text: "Asks for"; color: Style.fgMuted; Layout.preferredWidth: Style.dp(140) }
                    Label { text: "Ignore this program"; color: Style.fgMuted }
                }
                ListView {
                    objectName: "ssmProgramList"
                    Layout.fillWidth: true
                    Layout.preferredHeight: contentHeight
                    interactive: false
                    model: _ssm.programs
                    delegate: RowLayout {
                        required property var modelData
                        width: ListView.view.width
                        Label {
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                            text: modelData.name
                            color: Style.fg
                        }
                        Label {
                            Layout.preferredWidth: Style.dp(140)
                            elide: Text.ElideRight
                            text: modelData.kinds
                            color: Style.fgMuted
                        }
                        Switch {
                            id: _ignore
                            objectName: "ssmIgnoreSwitch"
                            enabled: _ssm.pendingIgnore.length === 0
                            // What Windows has, read again after every
                            // change, so a refused one goes back (S14).
                            Component.onCompleted: checked = _ssm.isIgnored(modelData.name)
                            onToggled: _ssm.setIgnored(modelData.name, checked)
                            Connections {
                                target: _ssm
                                function onProgramsChanged() {
                                    _ignore.checked = _ssm.isIgnored(modelData.name)
                                }
                            }
                        }
                    }
                }
                Label {
                    objectName: "ssmProgramsMessage"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    text: _ssm.programsMessage
                }

                Item { Layout.preferredHeight: Style.dp(10) }
            }
        }
    }
}

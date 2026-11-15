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
// The status is read once a second while the window is open; three
// sections (Devices, Programs, System; S12, S13, S17) list what keeps the
// PC awake, each with its own Refresh button.
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

    // A framed section of "What keeps the PC awake": title, its Refresh
    // button on the right, a one-line description, then its list.
    component AwakeSection: Rectangle {
        id: _section
        property string title
        property string description
        property string buttonName
        property string buttonText
        property bool buttonEnabled: true
        signal refresh()
        default property alias content: _content.data
        Layout.fillWidth: true
        implicitHeight: _col.implicitHeight + Style.dp(24)
        radius: Style.dp(4)
        color: Style.backgroundShade
        border.color: Style.line
        ColumnLayout {
            id: _col
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Style.dp(12)
            spacing: Style.dp(6)
            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: _section.title
                    font.bold: true
                    color: Style.fg
                }
                Button {
                    objectName: _section.buttonName
                    text: _section.buttonText
                    enabled: _section.buttonEnabled
                    onClicked: _section.refresh()
                }
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
                text: _section.description
            }
            ColumnLayout {
                id: _content
                Layout.fillWidth: true
                spacing: Style.dp(4)
            }
        }
    }

    // The Programs or System list (S13, S14, S17): name, "(driver)" or
    // "(service)", "also keeps the PC awake", the detail line, Ignore.
    component RequestList: ColumnLayout {
        id: _list
        property var ssm
        property var rows: []
        property string listName
        property string heading
        property string message
        property string messageName
        Layout.fillWidth: true
        spacing: Style.dp(4)
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(4)
            visible: _list.rows.length > 0
            Label { text: _list.heading; color: Style.fgMuted; Layout.fillWidth: true }
            Label { text: "Ignore"; color: Style.fgMuted }
        }
        ListView {
            objectName: _list.listName
            Layout.fillWidth: true
            Layout.preferredHeight: contentHeight
            interactive: false
            model: _list.rows
            delegate: RowLayout {
                id: _rowItem
                required property var modelData
                width: ListView.view.width
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.dp(4)
                        Label {
                            objectName: "ssmProgramName"
                            Layout.fillWidth: !_kindWord.visible
                            Layout.maximumWidth: parent.width
                                                 - (_kindWord.visible ? _kindWord.implicitWidth + Style.dp(4) : 0)
                            elide: Text.ElideMiddle
                            text: _rowItem.modelData.name
                            color: Style.fg
                        }
                        Label {
                            id: _kindWord
                            objectName: "ssmProgramKind"
                            visible: (_rowItem.modelData.kindWord || "").length > 0
                            text: "(" + (_rowItem.modelData.kindWord || "") + ")"
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(12)
                        }
                        Item { Layout.fillWidth: _kindWord.visible }
                    }
                    Label {
                        objectName: "ssmAlsoAwake"
                        visible: !!_rowItem.modelData.alsoAwake
                        text: "also keeps the PC awake"
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                    }
                    Label {
                        objectName: "ssmProgramDetail"
                        Layout.fillWidth: true
                        visible: (_rowItem.modelData.detail || "").length > 0
                        wrapMode: Text.Wrap
                        text: _rowItem.modelData.detail || ""
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                    }
                }
                Switch {
                    id: _ignore
                    objectName: "ssmIgnoreSwitch"
                    enabled: _list.ssm.pendingIgnore.length === 0
                    // What Windows has, read again after every change, so a
                    // refused one goes back (S14). Every row has it:
                    // programs, drivers and services alike.
                    function reread() {
                        checked = _list.ssm.isIgnored(_rowItem.modelData.name, _rowItem.modelData.kind)
                    }
                    Component.onCompleted: reread()
                    onToggled: _list.ssm.setIgnored(_rowItem.modelData.name, checked, _rowItem.modelData.kind)
                    Connections {
                        target: _list.ssm
                        function onProgramsChanged() { _ignore.reread() }
                        function onSystemChanged() { _ignore.reread() }
                    }
                }
            }
        }
        Label {
            objectName: _list.messageName
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: text.length > 0
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
            text: _list.message
        }
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
                // S18: what last reset the idle time, next to it.
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(16)
                    Label {
                        objectName: "ssmIdleText"
                        text: _ssm.idleText
                        color: Style.fg
                    }
                    Label {
                        objectName: "ssmLastReset"
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        visible: text.length > 0
                        text: _ssm.lastResetText
                        color: Style.fgMuted
                    }
                }
                Label {
                    objectName: "ssmWindowsIdleText"
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: _ssm.windowsIdleText
                    color: Style.fgMuted
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

                // S12-S14, S17: what keeps the PC awake, in three sections.
                SectionHeading { Layout.fillWidth: true; text: "What keeps the PC awake" }

                AwakeSection {
                    objectName: "ssmSectionDevices"
                    title: "Devices"
                    description: "Devices that never go quiet and keep Windows' idle time at 0. "
                                 + "Screen Saver Mode ignores them."
                    buttonName: "ssmRefreshDevices"
                    buttonText: _ssm.scanningDevices ? "Checking… (4 s)" : "Refresh Devices"
                    buttonEnabled: !_ssm.scanningDevices
                    onRefresh: _ssm.refreshDevices()

                    // The devices list (S12): empty until the first press.
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Style.dp(4)
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
                }

                AwakeSection {
                    objectName: "ssmSectionPrograms"
                    title: "Programs"
                    description: "Programs keeping the display on. These hold Screen Saver Mode "
                                 + "off until they stop. Needs administrator rights."
                    buttonName: "ssmRefreshPrograms"
                    buttonText: _ssm.scanningPrograms ? "Checking…" : "🛡 Refresh Programs"
                    buttonEnabled: !_ssm.scanningPrograms
                    onRefresh: _ssm.refreshPrograms()

                    RequestList {
                        ssm: _ssm
                        rows: _ssm.programs
                        listName: "ssmProgramList"
                        heading: "Program"
                        message: _ssm.programsMessage
                        messageName: "ssmProgramsMessage"
                    }
                }

                AwakeSection {
                    objectName: "ssmSectionSystem"
                    title: "System"
                    description: "Programs, drivers and services keeping the PC awake. They stop "
                                 + "sleep, not the screens. Needs administrator rights."
                    buttonName: "ssmRefreshSystem"
                    buttonText: _ssm.scanningSystem ? "Checking…" : "🛡 Refresh System"
                    buttonEnabled: !_ssm.scanningSystem
                    onRefresh: _ssm.refreshSystem()

                    RequestList {
                        ssm: _ssm
                        rows: _ssm.system
                        listName: "ssmSystemList"
                        heading: "Program, driver or service"
                        message: _ssm.systemMessage
                        messageName: "ssmSystemMessage"
                    }
                }

                Item { Layout.preferredHeight: Style.dp(10) }
            }
        }
    }
}

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

// Screen Saver Mode (12 S1-S20): Gremlin's own idle time from the keyboard
// and mouse only; two timers on it, the screen saver and the displays off,
// each with its own switch and wait.
// The status is read once a second while the window is open; three
// sections (Devices, Programs, System; S12, S13, S17) list what keeps the
// PC awake, each with its own Refresh button.
// Two tabs (S28): Settings (all of the above) and Wake PC, the keyboards
// and mice allowed to reset the idle time; a key or button pressed while
// Wake PC is open ticks its device (S30).
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

    // Made by ModelFactory (PYSIDE-1407: PySide6 never frees a Python object
    // QML declares); it lives as long as this window.
    readonly property ScreenSaverModeModel _ssm:
        ModelFactory.create("ScreenSaverModeModel", _win)
    readonly property ScreenSaverModeModel ssm: _ssm

    onVisibleChanged: _ssm.setOpen(visible)
    Component.onCompleted: _ssm.setOpen(visible)
    onClosing: _ssm.setOpen(false)

    // S30: presses are detected only while the Wake PC tab is shown.
    readonly property bool wakeShown: visible && _tabs.currentIndex === 1
    onWakeShownChanged: _ssm.wakeTabOpen(wakeShown)

    // One timer (S4, S5): its switch, its wait box (minutes; empty shows
    // Windows' time greyed and uses it), ✕ to clear, Windows' time named
    // next to it, and the row's problem under it. The typed wait is saved
    // when the box is left or Enter is pressed; text that isn't a time goes
    // back to what is saved.
    component TimerRow: ColumnLayout {
        id: _row
        property string title
        property bool on
        property string waitText
        property string placeholder
        property string windowsLabel
        property string problem
        property string switchName
        property string boxName
        property string clearName
        property string windowsName
        property string problemName
        property var setOn: function(on) {}
        property var setWait: function(text) { return true }
        property var clearWait: function() {}
        Layout.fillWidth: true
        spacing: Style.dp(4)
        RowLayout {
            spacing: Style.dp(8)
            Switch {
                objectName: _row.switchName
                Layout.preferredWidth: Style.dp(200)
                text: _row.title
                property bool shown: _row.on
                onShownChanged: if (!pressed) checked = shown
                Component.onCompleted: checked = shown
                onToggled: _row.setOn(checked)
            }
            TextField {
                id: _box
                objectName: _row.boxName
                Layout.preferredWidth: Style.dp(110)
                placeholderText: _row.placeholder
                validator: RegularExpressionValidator {
                    regularExpression: /^\s*\d{0,3}([.,]\d{0,2})?\s*(min)?\s*$/
                }
                property string saved: _row.waitText
                onSavedChanged: if (!activeFocus) text = saved
                Component.onCompleted: text = saved
                onEditingFinished: {
                    if (!_row.setWait(text))
                        text = _row.waitText
                }
            }
            Label {
                text: "min"
                color: Style.fgMuted
                visible: _box.text.length > 0
            }
            ToolButton {
                objectName: _row.clearName
                text: "✕"
                visible: _box.text.length > 0
                ToolTip.visible: hovered
                ToolTip.text: "Use Windows' time"
                onClicked: {
                    _box.text = ""
                    _row.clearWait()
                }
            }
            Label {
                objectName: _row.windowsName
                text: _row.windowsLabel
                color: _box.text.length > 0 ? Style.fgMuted : Style.fg
            }
        }
        Label {
            objectName: _row.problemName
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: text.length > 0
            text: _row.problem
            color: Style.dangerText
        }
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

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: _tabs
            objectName: "ssmTabs"
            Layout.fillWidth: true
            TabButton { objectName: "ssmTabSettings"; text: "Settings"; width: implicitWidth }
            TabButton { objectName: "ssmTabWake"; text: "Wake PC"; width: implicitWidth }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: _tabs.currentIndex

            ScrollView {
                id: _scroll
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    id: _body
                    width: _scroll.availableWidth
                    spacing: Style.dp(10)

                    Item { Layout.preferredHeight: Style.dp(6) }

                    // S2: the on/off switch; Test now on the right.
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(16)
                        Layout.rightMargin: Style.dp(16)
                        Switch {
                            id: _enabled
                            objectName: "ssmEnabled"
                            text: "Screen Saver Mode"
                            font.bold: true
                            property bool shown: _ssm.enabled
                            onShownChanged: if (!pressed) checked = shown
                            Component.onCompleted: checked = shown
                            onToggled: _ssm.setEnabled(checked)
                        }
                        Item { Layout.fillWidth: true }
                        Button {
                            objectName: "ssmTestNow"
                            highlighted: true
                            // Greyed unless Screen Saver Mode is on (canTest);
                            // a running countdown can always be cancelled.
                            enabled: countdown > 0 || _ssm.canTest !== false
                            ToolTip.visible: hovered && !enabled
                            ToolTip.text: "Turn Screen Saver Mode on first"
                            readonly property int countdown: _ssm.testCountdown || 0
                            text: countdown > 0 ? "Cancel test (" + countdown + ")" : "Test now"
                            onClicked: countdown > 0 ? _ssm.cancelTest() : _ssm.testNow()
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(16)
                        Layout.rightMargin: Style.dp(16)
                        wrapMode: Text.Wrap
                        color: Style.fgMuted
                        text: "Keeps its own idle time from your keyboard and mouse only, so sticks "
                              + "and other devices that never go quiet can't keep your screens on. "
                              + "Works only while Gremlin-Platforms is open. "
                              + "Test now runs the whole sequence after 5 s."
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(16)
                        Layout.rightMargin: Style.dp(16)
                        spacing: Style.dp(8)

                        // S4, S5: two timers, each with its own switch and wait.
                        SectionHeading { Layout.fillWidth: true; text: "Timers" }
                        TimerRow {
                            title: "Screen saver"
                            on: _ssm.saverOn
                            waitText: _ssm.saverWaitText
                            placeholder: _ssm.saverWindowsWaitText
                            windowsLabel: _ssm.saverWindowsWaitLabel
                            problem: _ssm.saverProblemText
                            switchName: "ssmSaverOn"
                            boxName: "ssmSaverWaitBox"
                            clearName: "ssmSaverWaitClear"
                            windowsName: "ssmSaverWindowsWait"
                            problemName: "ssmSaverProblem"
                            setOn: function(on) { _ssm.setSaverOn(on) }
                            setWait: function(text) { return _ssm.setSaverWaitText(text) }
                            clearWait: function() { _ssm.clearSaverWait() }
                        }
                        TimerRow {
                            title: "Power off displays"
                            on: _ssm.offOn
                            waitText: _ssm.offWaitText
                            placeholder: _ssm.offWindowsWaitText
                            windowsLabel: _ssm.offWindowsWaitLabel
                            problem: _ssm.offProblemText
                            switchName: "ssmOffOn"
                            boxName: "ssmOffWaitBox"
                            clearName: "ssmOffWaitClear"
                            windowsName: "ssmOffWindowsWait"
                            problemName: "ssmOffProblem"
                            setOn: function(on) { _ssm.setOffOn(on) }
                            setWait: function(text) { return _ssm.setOffWaitText(text) }
                            clearWait: function() { _ssm.clearOffWait() }
                        }
                        // Wait for devices to switch off: no switch, seconds.
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Style.dp(8)
                            Label {
                                Layout.preferredWidth: Style.dp(200)
                                text: "Wait for devices to switch off"
                                color: Style.fg
                                elide: Text.ElideRight
                            }
                            TextField {
                                id: _waitBox
                                objectName: "ssmDevicesWait"
                                Layout.preferredWidth: Style.dp(110)
                                validator: RegularExpressionValidator {
                                    regularExpression: /^\s*\d{0,2}\s*(s)?\s*$/
                                }
                                readonly property int saved: _ssm.devicesWaitS || 10
                                function show() { text = saved + " s" }
                                onSavedChanged: if (!activeFocus) show()
                                Component.onCompleted: show()
                                onEditingFinished: {
                                    var n = parseInt(text)
                                    if (isNaN(n)) { show(); return }
                                    n = Math.max(1, Math.min(60, n))
                                    _ssm.setDevicesWaitS(n)
                                    text = n + " s"
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                color: Style.fgMuted
                                font.pixelSize: Style.dp(12)
                                text: "at most; the displays go off as soon as they're done"
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(12)
                            text: "Both count from your last keyboard or mouse input."
                        }
                        Label {
                            objectName: "ssmOrderWarning"
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            visible: text.length > 0
                            text: _ssm.orderWarning
                            color: Style.warn
                        }

                        // S7
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Style.dp(8)
                            Switch {
                                objectName: "ssmHoldFullscreen"
                                text: "Hold off during full-screen programs"
                                property bool shown: _ssm.holdFullscreen
                                onShownChanged: if (!pressed) checked = shown
                                Component.onCompleted: checked = shown
                                onToggled: _ssm.setHoldFullscreen(checked)
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                color: Style.fgMuted
                                font.pixelSize: Style.dp(12)
                                text: "Gremlin-Platforms' own window never counts"
                            }
                        }

                        // S9, S15: the status table (label | value Â· detail).
                        SectionHeading { Layout.fillWidth: true; text: "Status" }
                        GridLayout {
                            objectName: "ssmStatusGrid"
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: Style.dp(12)
                            rowSpacing: Style.dp(4)
                            Repeater {
                                model: _ssm.statusRows || []
                                delegate: Item {
                                    id: _stRow
                                    required property var modelData
                                    required property int index
                                    Layout.columnSpan: 2
                                    Layout.fillWidth: true
                                    implicitHeight: _stLine.implicitHeight
                                    RowLayout {
                                        id: _stLine
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        spacing: Style.dp(12)
                                        Label {
                                            objectName: "ssmStatusLabel_" + _stRow.index
                                            Layout.preferredWidth: Style.dp(150)
                                            Layout.alignment: Qt.AlignTop
                                            text: _stRow.modelData.label || ""
                                            color: Style.fgMuted
                                        }
                                        Flow {
                                            Layout.fillWidth: true
                                            Label {
                                                objectName: "ssmStatusValue_" + _stRow.index
                                                text: _stRow.modelData.value || ""
                                                color: _stRow.modelData.tone === "ok" ? Style.okText
                                                     : _stRow.modelData.tone === "warn" ? Style.warn : Style.fg
                                            }
                                            Label {
                                                objectName: "ssmStatusDetail_" + _stRow.index
                                                visible: text.length > 0
                                                text: (_stRow.modelData.detail || "").length > 0
                                                      ? " · " + _stRow.modelData.detail : ""
                                                color: Style.fgMuted
                                                font.pixelSize: Style.dp(12)
                                            }
                                        }
                                        Button {
                                            objectName: "ssmDevicesRetry"
                                            visible: _stRow.index === 8 && !!(_ssm && _ssm.devicesBackRetry)
                                            text: "Try again"
                                            onClicked: _ssm.retryDevices()
                                        }
                                    }
                                }
                            }
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
                                         + "Screen Saver Mode ignores them, and switches off the ones "
                                         + "marked Switch off while the displays are off."
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
                                Label { objectName: "ssmDevicesSwitchOffHeader"; text: "Switch off"; color: Style.fgMuted }
                            }
                            ListView {
                                objectName: "ssmDeviceList"
                                Layout.fillWidth: true
                                Layout.preferredHeight: contentHeight
                                interactive: false
                                model: _ssm.devices
                                delegate: RowLayout {
                                    id: _devRow
                                    required property var modelData
                                    width: ListView.view.width
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Label {
                                            objectName: "ssmDeviceName"
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                            text: _devRow.modelData.name
                                            color: Style.fg
                                        }
                                        Label {
                                            objectName: "ssmDeviceVirtual"
                                            Layout.fillWidth: true
                                            visible: !!_devRow.modelData.virtual
                                            wrapMode: Text.Wrap
                                            text: "(virtual: never switched off)"
                                            color: Style.fgMuted
                                            font.pixelSize: Style.dp(12)
                                        }
                                    }
                                    Label {
                                        text: Math.round(_devRow.modelData.rate)
                                        color: Style.fg
                                    }
                                    Switch {
                                        id: _switchOff
                                        objectName: "ssmSwitchOffSwitch"
                                        enabled: !_devRow.modelData.virtual
                                        // The saved choice, read again from the
                                        // model so a toggle keeps the binding.
                                        function reread() {
                                            checked = !_devRow.modelData.virtual
                                                      && _devRow.modelData.switchOff !== false
                                        }
                                        Component.onCompleted: reread()
                                        onToggled: _ssm.setSwitchOff(_devRow.modelData.instanceId, checked)
                                        Connections {
                                            target: _devRow
                                            function onModelDataChanged() { _switchOff.reread() }
                                        }
                                        Connections {
                                            target: _ssm
                                            function onDevicesChanged() { _switchOff.reread() }
                                        }
                                        Accessible.name: "Switch off " + _devRow.modelData.name
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
                            // S26: the helper should run and doesn't.
                            RowLayout {
                                Layout.fillWidth: true
                                visible: _ssm.helperMessage.length > 0
                                Label {
                                    objectName: "ssmHelperMessage"
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                    text: _ssm.helperMessage
                                    color: Style.dangerText
                                }
                                Button {
                                    objectName: "ssmHelperTryAgain"
                                    text: "Try again"
                                    onClicked: _ssm.tryAgain()
                                }
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

            // Wake PC (S28-S30): one row per physical keyboard or mouse, with a
            // tick; the note says how it was ticked; an unplugged ticked one stays.
            ScrollView {
                id: _wakeScroll
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    width: _wakeScroll.availableWidth
                    spacing: Style.dp(8)

                    Item { Layout.preferredHeight: Style.dp(6) }

                    SectionHeading {
                        objectName: "ssmWakeHeading"
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(16)
                        Layout.rightMargin: Style.dp(16)
                        text: "Allow this device to wake the PC"
                    }
                    Label {
                        objectName: "ssmWakeProgramsNote"
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(16)
                        Layout.rightMargin: Style.dp(16)
                        wrapMode: Text.Wrap
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                        text: "Input sent by programs (RustDesk, remote desktop) always counts."
                    }
                    ListView {
                        objectName: "ssmWakeList"
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(16)
                        Layout.rightMargin: Style.dp(16)
                        Layout.preferredHeight: contentHeight
                        interactive: false
                        model: _ssm.wakeRows
                        delegate: Item {
                            id: _wakeRow
                            objectName: "ssmWakeRow"
                            required property var modelData
                            width: ListView.view.width
                            implicitHeight: _wakeLine.implicitHeight
                            // S33: lit while the device sends input (about 2 s
                            // after its last), never a change to the tick.
                            Rectangle {
                                objectName: "ssmWakeRowHighlight"
                                anchors.fill: parent
                                visible: !!_wakeRow.modelData.inUse
                                color: Style.bgSelected
                                radius: Style.dp(3)
                            }
                            RowLayout {
                                id: _wakeLine
                                anchors.left: parent.left
                                anchors.right: parent.right
                                spacing: Style.dp(8)
                                CheckBox {
                                    id: _wakeTick
                                    objectName: "ssmWakeTick"
                                    // What is saved, read again after every change.
                                    property bool shown: !!_wakeRow.modelData.ticked
                                    onShownChanged: if (!pressed) checked = shown
                                    Component.onCompleted: checked = shown
                                    onToggled: _ssm.setWakeTicked(_wakeRow.modelData.id, checked)
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Style.dp(6)
                                        Label {
                                            objectName: "ssmWakeName"
                                            Layout.maximumWidth: parent.width - _wakeKinds.implicitWidth - Style.dp(6)
                                            elide: Text.ElideMiddle
                                            text: _wakeRow.modelData.name
                                            color: _wakeRow.modelData.connected ? Style.fg : Style.fgMuted
                                        }
                                        Label {
                                            id: _wakeKinds
                                            objectName: "ssmWakeKinds"
                                            text: [_wakeRow.modelData.kinds,
                                                   _wakeRow.modelData.connected ? "" : "not connected"]
                                                  .filter(function(t) { return t.length > 0 }).join(" · ")
                                            color: Style.fgMuted
                                        }
                                        Item { Layout.fillWidth: true }
                                    }
                                    Label {
                                        objectName: "ssmWakeNote"
                                        Layout.fillWidth: true
                                        visible: text.length > 0
                                        wrapMode: Text.Wrap
                                        // S33: "in use now" after the note while
                                        // the device sends input.
                                        text: _wakeRow.modelData.inUse
                                              ? [_wakeRow.modelData.note, "in use now"]
                                                .filter(function(t) { return t.length > 0 }).join(" · ")
                                              : _wakeRow.modelData.note
                                        color: Style.fgMuted
                                        font.pixelSize: Style.dp(12)
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.preferredHeight: Style.dp(10) }
                }
            }
        }
    }
}

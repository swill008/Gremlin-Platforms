// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Gremlin Input Tester (D-02-INPUT-TESTER): what this process sees, with
// a verdict against Gremlin's expected.json when opened from Gremlin. Bound
// to the InputTesterModel context property `tester`; reads only.

import QtQuick
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

Window {
    id: _win
    objectName: "inputTester"

    width: Style.dp(1180)
    height: Style.dp(760)
    minimumWidth: Style.dp(900)
    minimumHeight: Style.dp(520)
    visible: true
    title: "Gremlin Input Tester"
    color: Style.bgPage

    // "All devices" compact view instead of one device.
    property bool showAll: false
    // The compact view's copy of tester.allDevices, refreshed ~20 a second.
    property var compactDevices: []

    readonly property var rows: tester.rows
    readonly property var sel: tester.selected
    readonly property int buttonCount: tester.buttons.length

    Component.onCompleted: Style.isDarkMode = true

    Timer {
        interval: 50
        repeat: true
        running: _win.showAll
        triggeredOnStart: true
        onTriggered: _win.compactDevices = tester.allDevices
    }

    function selectRow(key) {
        _win.showAll = false
        tester.select(key)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Verdict line: compare mode only.
        Rectangle {
            objectName: "verdictLine"
            Layout.fillWidth: true
            Layout.preferredHeight: _verdictRow.implicitHeight + Style.dp(24)
            visible: tester.compareMode
            color: tester.verdict === "fail" ? Style.alpha(Style.dangerFill, 0.5)
                : Style.alpha(Style.okFill, 0.5)

            RowLayout {
                id: _verdictRow
                anchors.fill: parent
                anchors.leftMargin: Style.dp(14)
                anchors.rightMargin: Style.dp(14)
                spacing: Style.dp(14)

                Text {
                    objectName: "verdictText"
                    text: tester.verdictText
                    font.family: Style.uiFont
                    font.pixelSize: Style.dp(17)
                    font.bold: true
                    color: tester.verdict === "fail" ? Style.dangerText : Style.okText
                }
                Text {
                    objectName: "verdictSummary"
                    Layout.fillWidth: true
                    text: tester.summary
                    wrapMode: Text.Wrap
                    font.family: Style.uiFont
                    font.pixelSize: Style.dp(13)
                    color: Style.fg
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: tester.verdict === "fail" ? Style.dangerFill : Style.okFill
            }
        }

        // Context line: what it was compared with, this exe, the actions.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: _ctxFlow.implicitHeight + Style.dp(16)
            color: Style.infoFillDeep

            RowLayout {
                id: _ctxFlow
                anchors.fill: parent
                anchors.leftMargin: Style.dp(14)
                anchors.rightMargin: Style.dp(14)
                spacing: Style.dp(12)

                Text {
                    objectName: "contextLine"
                    Layout.fillWidth: true
                    text: tester.contextLine
                    wrapMode: Text.Wrap
                    font.family: Style.uiFont
                    font.pixelSize: Style.dp(12.5)
                    color: Style.fgStrong
                }
                Rectangle {
                    Layout.maximumWidth: Style.dp(380)
                    Layout.preferredWidth: _path.implicitWidth + Style.dp(12)
                    Layout.preferredHeight: _path.implicitHeight + Style.dp(4)
                    color: Style.bgWell
                    border.color: Style.infoFill
                    radius: Style.dp(4)
                    Text {
                        id: _path
                        anchors.fill: parent
                        anchors.leftMargin: Style.dp(6)
                        anchors.rightMargin: Style.dp(6)
                        verticalAlignment: Text.AlignVCenter
                        text: tester.exePath
                        elide: Text.ElideMiddle
                        font.family: Style.monoFont
                        font.pixelSize: Style.dp(11.5)
                        color: Style.infoText
                    }
                }
                TesterButton {
                    objectName: "copyPathButton"
                    text: "Copy path"
                    onClicked: tester.copyPath()
                }
                TesterButton {
                    objectName: "refreshButton"
                    text: "Refresh"
                    onClicked: tester.refresh()
                }
                TesterButton {
                    objectName: "copyResultButton"
                    text: "Copy result"
                    onClicked: tester.copyResult()
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Style.infoFill
            }
        }

        // Steam line (amber, not a fail).
        Rectangle {
            objectName: "steamLine"
            Layout.fillWidth: true
            Layout.preferredHeight: _steam.implicitHeight + Style.dp(14)
            visible: tester.steamWarning !== ""
            color: Style.alpha(Style.warn, 0.15)
            Text {
                id: _steam
                anchors.fill: parent
                anchors.leftMargin: Style.dp(14)
                anchors.rightMargin: Style.dp(14)
                verticalAlignment: Text.AlignVCenter
                text: "⚠ " + tester.steamWarning
                wrapMode: Text.Wrap
                font.family: Style.uiFont
                font.pixelSize: Style.dp(12.5)
                color: Style.warn
            }
        }

        // Body: device list | device view.
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.preferredWidth: Style.dp(470)
                Layout.fillHeight: true
                color: Style.bgCard

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Flickable {
                        id: _list
                        objectName: "deviceList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentHeight: _listCol.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: _listCol
                            width: _list.width
                            topPadding: Style.dp(8)

                            DeviceRow {
                                objectName: "allDevicesRow"
                                width: parent.width
                                row: ({
                                    name: "All devices",
                                    sub: "Every device this program sees, live, at a glance",
                                    icon: "▦", iconStyle: "", live: false
                                })
                                selected: _win.showAll
                                onClicked: {
                                    _win.showAll = true
                                    tester.select("")
                                }
                            }

                            Repeater {
                                model: _win.rows
                                delegate: Column {
                                    id: _entry
                                    required property var modelData
                                    required property int index
                                    width: _listCol.width

                                    readonly property bool firstOfSection: index === 0
                                        || _win.rows[index - 1].section !== modelData.section

                                    Text {
                                        visible: _entry.firstOfSection
                                        width: parent.width
                                        leftPadding: Style.dp(14)
                                        topPadding: Style.dp(10)
                                        bottomPadding: Style.dp(4)
                                        text: (_entry.modelData.section || "").toUpperCase()
                                        font.family: Style.uiFont
                                        font.pixelSize: Style.dp(11)
                                        font.letterSpacing: Style.dp(0.8)
                                        color: Style.fgMuted
                                    }
                                    DeviceRow {
                                        objectName: "deviceRow_" + _entry.modelData.key
                                        width: parent.width
                                        row: _entry.modelData
                                        selected: !_win.showAll
                                            && tester.selectedKey === _entry.modelData.key
                                        active: !!tester.activity[_entry.modelData.key]
                                        onClicked: _win.selectRow(_entry.modelData.key)
                                    }
                                }
                            }

                            // HID game devices: a list only (path and ids).
                            Text {
                                visible: tester.hidDevices.length > 0
                                width: parent.width
                                leftPadding: Style.dp(14)
                                topPadding: Style.dp(10)
                                bottomPadding: Style.dp(4)
                                text: "HID GAME DEVICES (LIST ONLY)"
                                font.family: Style.uiFont
                                font.pixelSize: Style.dp(11)
                                font.letterSpacing: Style.dp(0.8)
                                color: Style.fgMuted
                            }
                            Repeater {
                                model: tester.hidDevices
                                delegate: Column {
                                    required property var modelData
                                    width: _listCol.width
                                    leftPadding: Style.dp(40)
                                    rightPadding: Style.dp(14)
                                    topPadding: Style.dp(4)
                                    bottomPadding: Style.dp(4)
                                    Text {
                                        width: parent.width - parent.leftPadding - parent.rightPadding
                                        text: (modelData.name || "HID device")
                                            + "  ·  VID " + modelData.vid + " · PID " + modelData.pid
                                        elide: Text.ElideRight
                                        font.family: Style.uiFont
                                        font.pixelSize: Style.dp(12.5)
                                        color: Style.fg
                                    }
                                    Text {
                                        width: parent.width - parent.leftPadding - parent.rightPadding
                                        text: modelData.path || ""
                                        elide: Text.ElideMiddle
                                        font.family: Style.monoFont
                                        font.pixelSize: Style.dp(10.5)
                                        color: Style.fgMuted
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Style.line
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.margins: Style.dp(8)
                        Layout.leftMargin: Style.dp(14)
                        text: "Reads only: never writes vJoy, ViGEm, HidHide or settings."
                            + (tester.compareMode ? ""
                               : " Opened on its own (without Gremlin), it lists what it sees with no ✓/✗.")
                        wrapMode: Text.Wrap
                        font.family: Style.uiFont
                        font.pixelSize: Style.dp(11.5)
                        color: Style.fgMuted
                    }
                }
            }
            Rectangle {
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: Style.line
            }

            // Right: one device, or every device in compact form.
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Text {
                    anchors.centerIn: parent
                    visible: !_win.showAll && tester.selectedKey === ""
                    text: "Pick a device on the left to see its axes, buttons and hats live."
                    font.family: Style.uiFont
                    font.pixelSize: Style.dp(13)
                    color: Style.fgMuted
                }

                // All devices.
                Flickable {
                    objectName: "compactView"
                    anchors.fill: parent
                    anchors.margins: Style.dp(14)
                    visible: _win.showAll
                    clip: true
                    contentHeight: _cards.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds

                    GridLayout {
                        id: _cards
                        width: parent.width
                        columns: Math.max(1, Math.floor(width / Style.dp(250)))
                        columnSpacing: Style.dp(10)
                        rowSpacing: Style.dp(10)

                        Repeater {
                            model: _win.compactDevices
                            delegate: CompactCard {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                device: modelData
                                onClicked: _win.selectRow(modelData.key)
                            }
                        }
                    }
                    Text {
                        visible: _win.compactDevices.length === 0
                        text: "This program sees no game devices."
                        font.family: Style.uiFont
                        font.pixelSize: Style.dp(13)
                        color: Style.fgMuted
                    }
                }

                // One device.
                Flickable {
                    id: _detail
                    objectName: "deviceView"
                    anchors.fill: parent
                    visible: !_win.showAll && tester.selectedKey !== ""
                    clip: true
                    contentHeight: _detailCol.implicitHeight + Style.dp(28)
                    boundsBehavior: Flickable.StopAtBounds

                    ColumnLayout {
                        id: _detailCol
                        x: Style.dp(16)
                        y: Style.dp(14)
                        width: _detail.width - Style.dp(32)
                        spacing: Style.dp(13)

                        RowLayout {
                            spacing: Style.dp(10)
                            Text {
                                objectName: "detailName"
                                text: _win.sel.name || ""
                                font.family: Style.uiFont
                                font.pixelSize: Style.dp(18)
                                font.bold: true
                                color: Style.fgStrong
                            }
                            TesterTag {
                                text: _win.sel.tag || ""
                                kind: _win.sel.tagStyle || ""
                            }
                        }

                        // The "In Gremlin" box.
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: _link.implicitHeight + Style.dp(20)
                            color: Style.bgCard
                            border.color: Style.line
                            radius: Style.dp(6)

                            GridLayout {
                                id: _link
                                anchors.fill: parent
                                anchors.margins: Style.dp(10)
                                anchors.leftMargin: Style.dp(12)
                                columns: 2
                                columnSpacing: Style.dp(12)
                                rowSpacing: Style.dp(4)

                                Text { text: "In Gremlin"; visible: !!_win.sel.inGremlin; Layout.preferredWidth: Style.dp(150); font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fgMuted }
                                Text { text: _win.sel.inGremlin || ""; visible: !!_win.sel.inGremlin; Layout.fillWidth: true; wrapMode: Text.Wrap; font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fg }
                                Text { text: "Windows name"; visible: !!_win.sel.windowsName; Layout.preferredWidth: Style.dp(150); font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fgMuted }
                                Text { text: _win.sel.windowsName || ""; visible: !!_win.sel.windowsName; Layout.fillWidth: true; wrapMode: Text.Wrap; font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fg }
                                Text { text: "Ids"; visible: !!_win.sel.ids; Layout.preferredWidth: Style.dp(150); font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fgMuted }
                                Text { text: _win.sel.ids || ""; visible: !!_win.sel.ids; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; font.family: Style.monoFont; font.pixelSize: Style.dp(11.5); color: Style.fg }
                                Text { text: "Expected"; visible: !!_win.sel.expected; Layout.preferredWidth: Style.dp(150); font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fgMuted }
                                Text { text: _win.sel.expected || ""; visible: !!_win.sel.expected; Layout.fillWidth: true; wrapMode: Text.Wrap; font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fg }
                            }
                        }

                        Text {
                            visible: _win.sel.seen === false
                            Layout.fillWidth: true
                            text: "Not seen by this program, so there are no live values."
                            wrapMode: Text.Wrap
                            font.family: Style.uiFont
                            font.pixelSize: Style.dp(13)
                            color: Style.fgMuted
                        }

                        // Axes.
                        Text {
                            visible: tester.axes.length > 0
                            text: "AXES"
                            font.family: Style.uiFont
                            font.pixelSize: Style.dp(11)
                            font.letterSpacing: Style.dp(0.8)
                            color: Style.fgMuted
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            visible: tester.axes.length > 0
                            columns: 2
                            columnSpacing: Style.dp(22)
                            rowSpacing: Style.dp(8)
                            Repeater {
                                model: tester.axes
                                delegate: AxisBar {
                                    required property var modelData
                                    objectName: "axisBar"
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 1
                                    name: modelData.label
                                    value: modelData.value
                                }
                            }
                        }

                        // Buttons: 16 a row, two rows shown, scroll for more.
                        Text {
                            id: _buttonsLabel
                            visible: _win.buttonCount > 0
                            readonly property int firstShown: Math.floor(_btnFlick.contentY / _btnFlick.rowH) * 16 + 1
                            readonly property int lastShown: Math.min(_win.buttonCount, firstShown + 31)
                            text: _win.buttonCount > 32
                                ? "BUTTONS (" + firstShown + "–" + lastShown + " OF " + _win.buttonCount + ")"
                                : "BUTTONS (" + _win.buttonCount + ")"
                            font.family: Style.uiFont
                            font.pixelSize: Style.dp(11)
                            font.letterSpacing: Style.dp(0.8)
                            color: Style.fgMuted
                        }
                        Flickable {
                            id: _btnFlick
                            objectName: "buttonsView"
                            readonly property real rowH: Style.dp(29)
                            readonly property int rowCount: Math.ceil(_win.buttonCount / 16)
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(rowCount, 2) * rowH
                            visible: _win.buttonCount > 0
                            clip: true
                            contentHeight: rowCount * rowH
                            boundsBehavior: Flickable.StopAtBounds
                            interactive: rowCount > 2

                            Grid {
                                id: _btnGrid
                                width: _btnFlick.width - (_btnFlick.interactive ? Style.dp(10) : 0)
                                columns: 16
                                spacing: Style.dp(5)
                                Repeater {
                                    model: tester.buttons
                                    delegate: Rectangle {
                                        required property var modelData
                                        required property int index
                                        objectName: "buttonCell_" + (index + 1)
                                        property bool pressed: !!modelData
                                        width: (_btnGrid.width - 15 * _btnGrid.spacing) / 16
                                        height: Style.dp(24)
                                        radius: Style.dp(4)
                                        color: pressed ? Style.ok : Style.bgWell
                                        border.color: pressed ? Style.ok : Style.line
                                        Text {
                                            anchors.centerIn: parent
                                            text: index + 1
                                            font.family: Style.uiFont
                                            font.pixelSize: Style.dp(11)
                                            font.bold: parent.pressed
                                            color: parent.pressed ? Style.okFillDeep : Style.fgDisabled
                                        }
                                    }
                                }
                            }
                            // Scroll bar, when there are more than two rows.
                            Rectangle {
                                visible: _btnFlick.interactive
                                x: _btnFlick.width - Style.dp(6)
                                y: _btnFlick.contentY + _btnFlick.visibleArea.yPosition * _btnFlick.height
                                width: Style.dp(5)
                                height: _btnFlick.visibleArea.heightRatio * _btnFlick.height
                                radius: width / 2
                                color: Style.lineStrong
                            }
                        }

                        // Hats.
                        Text {
                            visible: tester.hats.length > 0
                            text: "HATS"
                            font.family: Style.uiFont
                            font.pixelSize: Style.dp(11)
                            font.letterSpacing: Style.dp(0.8)
                            color: Style.fgMuted
                        }
                        Row {
                            visible: tester.hats.length > 0
                            spacing: Style.dp(22)
                            bottomPadding: Style.dp(16)
                            Repeater {
                                model: tester.hats
                                delegate: HatCompass {
                                    required property var modelData
                                    required property int index
                                    objectName: "hat_" + (index + 1)
                                    value: modelData
                                    label: "Hat " + (index + 1)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Status bar.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: _status.implicitHeight + Style.dp(14)
            color: Style.bgCard
            Rectangle { width: parent.width; height: 1; color: Style.line }
            Text {
                id: _status
                objectName: "statusLine"
                anchors.fill: parent
                anchors.leftMargin: Style.dp(14)
                verticalAlignment: Text.AlignVCenter
                text: tester.statusLine
                font.family: Style.uiFont
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
        }
    }
}

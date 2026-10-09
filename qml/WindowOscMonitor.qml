// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

// Tools › OSC Monitor, and the OSC page's Monitor button (D-09-OSC-MONITOR):
// the last 200 OSC messages in and out. While it is open OSC's port stays
// open, even with no Run (OscMonitorModel.active).
ApplicationWindow {
    id: _win
    font.pixelSize: Style.fontSize
    width: 1000
    height: 600
    minimumWidth: Style.fitWidth(Style.dp(700), Screen)
    minimumHeight: Style.fitHeight(Style.dp(400), Screen)
    title: qsTr("OSC Monitor")
    color: Style.background
    U.Universal.theme: Style.theme

    readonly property alias monitor: _model
    readonly property alias addWindow: _addDialog
    readonly property bool editorLocked: typeof backend !== "undefined" && backend
        && backend.gremlinActive

    ToolWindowMemory {
        host: _win
        name: "oscMonitor"
        defaultWidth: Style.dp(1000)
        defaultHeight: Style.dp(600)
    }

    OscMonitorModel {
        id: _model
    }

    Component.onCompleted: _model.active = true
    onClosing: _model.active = false
    Component.onDestruction: _model.active = false

    // Add as input…: the OSC page's Add window, filled in from the message.
    function addAsInput(row) {
        if (editorLocked)
            return false
        var s = _model.addSettings(row)
        if (!s || !s.address)
            return false
        _addDialog.openForEdit("", s)
        _addDialog.lastParameters = s.values || ""
        return true
    }

    OscAddDialog {
        id: _addDialog
        objectName: "oscMonitorAdd"

        deviceModel: OscDeviceManagementModel {}

        onAccepted: (settings) => {
            if (!_win.editorLocked)
                deviceModel.createConfiguredInput(settings)
        }
    }

    readonly property var _widths: [Style.dp(100), Style.dp(40), Style.dp(220),
                                    Style.dp(160), Style.dp(150)]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(8)

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(10)

            SearchBox {
                id: _filter
                objectName: "oscMonitorFilter"
                Layout.fillWidth: true
                placeholder: qsTr("Filter: address, value, from / to or input")
                count: _model.count
                onTextChanged: _model.filterText = text
            }

            Button {
                objectName: "oscMonitorPause"
                text: _model.paused ? qsTr("Resume") : qsTr("Pause")
                onClicked: _model.paused = !_model.paused
                ToolTip.visible: hovered
                ToolTip.text: _model.paused ? qsTr("Show new messages again")
                                            : qsTr("Stop adding new messages to the list")
            }

            Switch {
                objectName: "oscMonitorOutgoing"
                text: qsTr("Show outgoing")
                checked: _model.showOutgoing
                onToggled: _model.showOutgoing = checked
            }

            Button {
                objectName: "oscMonitorClear"
                text: qsTr("Clear")
                onClicked: _model.clear()
            }
        }

        // Column heads.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)

            Repeater {
                model: [qsTr("Time"), qsTr("In / Out"), qsTr("Address"), qsTr("Values"),
                        qsTr("From / To")]
                Label {
                    required property int index
                    required property string modelData
                    Layout.preferredWidth: _win._widths[index]
                    text: modelData
                    color: Style.fgMuted
                    font.bold: true
                }
            }
            Label {
                Layout.fillWidth: true
                text: qsTr("Input")
                color: Style.fgMuted
                font.bold: true
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Style.bgWell
            border.color: Style.line
            border.width: Style.dp(1)

            ListView {
                id: _list
                objectName: "oscMonitorList"
                anchors.fill: parent
                anchors.margins: Style.dp(4)
                clip: true
                model: _model
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                // Keep to the newest unless scrolled up.
                property bool _atEnd: true
                onMovementEnded: _atEnd = atYEnd
                onCountChanged: if (_atEnd) Qt.callLater(positionViewAtEnd)

                delegate: RowLayout {
                    id: _row
                    required property int index
                    required property string time
                    required property string direction
                    required property string address
                    required property string values
                    required property string peer
                    required property string matched
                    required property bool noInput

                    width: ListView.view.width
                    spacing: Style.dp(8)

                    Label {
                        Layout.preferredWidth: _win._widths[0]
                        text: _row.time
                        color: Style.fgMuted
                    }
                    Label {
                        Layout.preferredWidth: _win._widths[1]
                        text: _row.direction === "out" ? qsTr("Out") : qsTr("In")
                        color: _row.direction === "out" ? Style.infoText : Style.fg
                    }
                    Label {
                        Layout.preferredWidth: _win._widths[2]
                        text: _row.address
                        elide: Text.ElideRight
                        color: Style.fgStrong
                    }
                    Label {
                        Layout.preferredWidth: _win._widths[3]
                        text: _row.values
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.preferredWidth: _win._widths[4]
                        text: _row.peer
                        elide: Text.ElideRight
                        color: Style.fgMuted
                    }
                    Label {
                        Layout.fillWidth: true
                        text: _row.matched
                        elide: Text.ElideRight
                        color: _row.noInput ? Style.fgMuted : Style.fg
                        font.italic: _row.noInput
                    }
                    Button {
                        objectName: "oscMonitorAddRow" + _row.index
                        visible: _row.noInput
                        enabled: !_win.editorLocked
                        text: qsTr("Add as Input…")
                        onClicked: _win.addAsInput(_row.index)
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: _list.count === 0
                text: _model.paused ? qsTr("Paused") : qsTr("No OSC messages yet")
                color: Style.fgMuted
            }
        }
    }
}

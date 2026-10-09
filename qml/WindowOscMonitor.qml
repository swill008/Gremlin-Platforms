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

    // Columns (D-09-OSC-LOOK, the Button Map's table look): Time and In / Out
    // fit their widest text, Address takes the spare room, the rest are
    // fixed; the last column always keeps room for Add as Input… so rows
    // line up with the heads. Every cell elides; the row's hover shows it all.
    readonly property int _headPx: Style.dp(11)
    readonly property int _rowPx: Style.dp(13)
    readonly property int _gap: Style.dp(8)
    readonly property int _pad: Style.dp(6)
    readonly property var _widths: [
        Math.ceil(Math.max(_tmTimeHead.advanceWidth, _tmTime.advanceWidth)) + _pad,
        Math.ceil(Math.max(_tmDirHead.advanceWidth, _tmOut.advanceWidth)) + _pad,
        -1,
        Style.dp(160),
        Style.dp(150),
        Style.dp(150),
    ]
    readonly property int _addWidth: _addMetric.implicitWidth + Style.dp(10)
    readonly property int _addressMin: Style.dp(220)

    TextMetrics { id: _tmTimeHead; font.family: _win.font.family; font.pixelSize: _win._headPx; text: qsTr("Time") }
    TextMetrics { id: _tmTime; font.family: _win.font.family; font.pixelSize: _win._rowPx; text: "00:00:00.000" }
    TextMetrics { id: _tmDirHead; font.family: _win.font.family; font.pixelSize: _win._headPx; text: qsTr("In / Out") }
    TextMetrics { id: _tmOut; font.family: _win.font.family; font.pixelSize: _win._rowPx; text: qsTr("Out") }
    TextMetrics { id: _addMetric; font.family: _win.font.family; font.pixelSize: Style.dp(12); text: qsTr("Add as Input…") }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(8)

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(6)

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
                implicitHeight: Style.dp(28)
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

            DangerButton {
                objectName: "oscMonitorClear"
                implicitHeight: Style.dp(28)
                text: qsTr("Clear")
                onClicked: _model.clear()
            }
        }

        // The table: a recessed well with its column heads on a raised strip.
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Style.bgWell
            border.color: Style.line
            border.width: 1
            radius: Style.dp(4)
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 1
                spacing: 0

                // Column heads: each in its own width, cut with "…" rather
                // than running into the next.
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: Style.dp(22)
                    color: Style.bgRaised

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Style.line
                    }

                    RowLayout {
                        objectName: "oscMonitorHeads"
                        anchors.fill: parent
                        anchors.leftMargin: Style.dp(6)
                        anchors.rightMargin: Style.dp(4) + _bar.width
                        spacing: _win._gap

                        Repeater {
                            model: [qsTr("Time"), qsTr("In / Out"), qsTr("Address"),
                                    qsTr("Values"), qsTr("From / To"), qsTr("Input")]
                            Label {
                                required property int index
                                required property string modelData
                                objectName: "oscMonitorHead" + index
                                readonly property bool stretch: _win._widths[index] < 0
                                Layout.fillWidth: stretch
                                Layout.minimumWidth: stretch ? _win._addressMin : _win._widths[index]
                                Layout.preferredWidth: stretch ? _win._addressMin : _win._widths[index]
                                Layout.maximumWidth: stretch ? Number.POSITIVE_INFINITY
                                                             : _win._widths[index]
                                text: modelData
                                elide: Text.ElideRight
                                font.pixelSize: _win._headPx
                                color: Style.fgMuted
                            }
                        }
                        Item {
                            Layout.preferredWidth: _win._addWidth
                        }
                    }
                }

                ListView {
                    id: _list
                    objectName: "oscMonitorList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: _model
                    ScrollBar.vertical: ScrollBar {
                        id: _bar
                        policy: _list.contentHeight > _list.height ? ScrollBar.AsNeeded
                                                                   : ScrollBar.AlwaysOff
                    }

                    // Keep to the newest unless scrolled up.
                    property bool _atEnd: true
                    onMovementEnded: _atEnd = atYEnd
                    onCountChanged: if (_atEnd) Qt.callLater(positionViewAtEnd)

                    delegate: Rectangle {
                        id: _row
                        required property int index
                        required property string time
                        required property string direction
                        required property string address
                        required property string values
                        required property string peer
                        required property string matched
                        required property bool noInput
                        required property string hoverText

                        width: ListView.view.width
                        height: Style.dp(26)
                        color: _hover.hovered ? Style.bgRaised : Style.clear

                        HoverHandler {
                            id: _hover
                        }

                        // The full row (address, values, from / to, input) on hover.
                        PointerTip {
                            objectName: "oscMonitorRowTip" + _row.index
                            text: _row.hoverText
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Style.dp(6)
                            anchors.rightMargin: Style.dp(4) + _bar.width
                            spacing: _win._gap

                            Label {
                                Layout.preferredWidth: _win._widths[0]
                                Layout.maximumWidth: _win._widths[0]
                                text: _row.time
                                elide: Text.ElideRight
                                font.pixelSize: _win._rowPx
                                color: Style.fgMuted
                            }
                            Label {
                                Layout.preferredWidth: _win._widths[1]
                                Layout.maximumWidth: _win._widths[1]
                                text: _row.direction === "out" ? qsTr("Out") : qsTr("In")
                                font.pixelSize: _win._rowPx
                                color: _row.direction === "out" ? Style.infoText : Style.fg
                            }
                            Label {
                                objectName: "oscMonitorAddress" + _row.index
                                Layout.fillWidth: true
                                Layout.minimumWidth: _win._addressMin
                                Layout.preferredWidth: _win._addressMin
                                text: _row.address
                                elide: Text.ElideMiddle
                                font.family: Style.monoFont
                                font.pixelSize: Style.dp(12)
                                color: Style.fgStrong
                            }
                            Label {
                                Layout.preferredWidth: _win._widths[3]
                                Layout.maximumWidth: _win._widths[3]
                                text: _row.values
                                elide: Text.ElideRight
                                font.family: Style.monoFont
                                font.pixelSize: Style.dp(12)
                                color: Style.fg
                            }
                            Label {
                                Layout.preferredWidth: _win._widths[4]
                                Layout.maximumWidth: _win._widths[4]
                                text: _row.peer
                                elide: Text.ElideRight
                                font.pixelSize: _win._rowPx
                                color: Style.fgMuted
                            }
                            Label {
                                Layout.preferredWidth: _win._widths[5]
                                Layout.maximumWidth: _win._widths[5]
                                text: _row.matched
                                elide: Text.ElideRight
                                font.pixelSize: _win._rowPx
                                color: _row.noInput ? Style.fgMuted : Style.fg
                                font.italic: _row.noInput
                            }
                            Item {
                                Layout.preferredWidth: _win._addWidth
                                Layout.fillHeight: true

                                // Small outline button (the Button Map's panel buttons).
                                Rectangle {
                                    objectName: "oscMonitorAddRow" + _row.index
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: _row.noInput
                                    enabled: !_win.editorLocked
                                    implicitWidth: _addText.implicitWidth + Style.dp(10)
                                    implicitHeight: Style.dp(22)
                                    radius: Style.dp(4)
                                    color: _addArea.containsMouse ? Style.bgSelected : Style.clear
                                    border.color: Style.line

                                    Label {
                                        id: _addText
                                        anchors.centerIn: parent
                                        text: qsTr("Add as Input…")
                                        font.pixelSize: Style.dp(12)
                                        color: parent.enabled ? Style.fg : Style.fgDisabled
                                    }
                                    MouseArea {
                                        id: _addArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: _win.addAsInput(_row.index)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            EmptyState {
                anchors.centerIn: parent
                visible: _list.count === 0
                text: _model.paused ? qsTr("Paused") : qsTr("No OSC messages yet")
            }
        }
    }
}

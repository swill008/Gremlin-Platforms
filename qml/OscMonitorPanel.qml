// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style

// The OSC Monitor (D-09-OSC-MONITOR): the last 200 OSC messages in and out.
// Docked at the bottom of the OSC page (folded by default) and the body of
// the Pop out window (WindowOscMonitor.qml). It holds OSC's port open only
// while it is shown, unfolded and its page (or window) is open (holdsPort);
// folding it or leaving the page releases the port.
Rectangle {
    id: _root
    objectName: "oscMonitorPanel"
    color: Style.background

    // Folded: only the title row shows.
    property bool folded: true
    // The page (or window) this panel sits on is the one showing.
    property bool pageOpen: true
    // On the page: fold caret, Pop out and ×. In the Pop out window: none.
    property bool docked: true

    signal popOutRequested()
    signal closeRequested()
    // Add as Input… on a "no input" row: the Add window's settings
    // (OscMonitorModel.addSettings). Never sent while a profile runs.
    signal addAsInputRequested(var settings)

    readonly property bool holdsPort: visible && pageOpen && !folded
    readonly property alias monitor: _model
    readonly property bool editorLocked: typeof backend !== "undefined" && backend
        ? !!backend.gremlinActive : false
    readonly property int foldedHeight: _head.implicitHeight + Style.dp(12)
    property alias font: _fontRef.font

    implicitHeight: folded ? foldedHeight : Style.dp(300)

    Label { id: _fontRef; visible: false }

    OscMonitorModel {
        id: _model
        active: _root.holdsPort
    }

    Component.onDestruction: _model.active = false

    // Add as Input…: hands the message's settings to the page's Add window.
    function addAsInput(row) {
        if (editorLocked)
            return false
        var s = _model.addSettings(row)
        if (!s || !s.address)
            return false
        addAsInputRequested(s)
        return true
    }

    // Allow this sender (09 S160): the blocked row's host goes on the
    // allow-list; a refusal shows on the note line.
    property string note: ""
    property string _menuHost: ""
    property int _menuRow: -1
    property bool _menuBlocked: false
    property bool _menuNoInput: false
    readonly property alias rowMenu: _rowMenu

    function allowSender(host) {
        var res = String(_model.allowSender(String(host || "")) || "")
        note = res.length ? res : qsTr("Allowed: ") + host
        return res.length === 0
    }

    function openRowMenu(item, x, y, row, host, blocked, noInput) {
        _menuRow = row
        _menuHost = host
        _menuBlocked = blocked
        _menuNoInput = noInput
        if (!blocked && !(noInput && !editorLocked))
            return false
        _rowMenu.openAt(item, x, y)
        return true
    }

    ContextMenu {
        id: _rowMenu
        menuWidth: Style.dp(220)
        build: function() {
            var items = []
            if (_root._menuBlocked)
                items.push(MenuModel.action(qsTr("Allow this sender"), function() {
                    _root.allowSender(_root._menuHost)
                }, _root._menuHost.length > 0))
            if (_root._menuNoInput && !_root.editorLocked)
                items.push(MenuModel.action(qsTr("Add as Input…"), function() {
                    _root.addAsInput(_root._menuRow)
                }))
            return MenuModel.menu("osc-monitor-row", _root._menuHost || qsTr("OSC message"), items)
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

    TextMetrics { id: _tmTimeHead; font.family: _root.font.family; font.pixelSize: _root._headPx; text: qsTr("Time") }
    TextMetrics { id: _tmTime; font.family: _root.font.family; font.pixelSize: _root._rowPx; text: "00:00:00.000" }
    TextMetrics { id: _tmDirHead; font.family: _root.font.family; font.pixelSize: _root._headPx; text: qsTr("In / Out") }
    TextMetrics { id: _tmOut; font.family: _root.font.family; font.pixelSize: _root._rowPx; text: qsTr("Out") }
    TextMetrics { id: _addMetric; font.family: _root.font.family; font.pixelSize: Style.dp(12); text: qsTr("Add as Input…") }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Style.dp(12)
        anchors.rightMargin: Style.dp(12)
        anchors.topMargin: Style.dp(6)
        anchors.bottomMargin: _root.folded ? Style.dp(6) : Style.dp(12)
        spacing: Style.dp(8)

        // Title row: caret + "OSC Monitor" fold the panel; the controls
        // follow on the same row (folded: only Pop out and ×).
        RowLayout {
            id: _head
            Layout.fillWidth: true
            spacing: Style.dp(6)

            Item {
                objectName: "oscMonitorTitle"
                implicitWidth: _titleRow.implicitWidth
                implicitHeight: Style.dp(28)

                Row {
                    id: _titleRow
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Style.dp(6)

                    Label {
                        visible: _root.docked
                        anchors.verticalCenter: parent.verticalCenter
                        text: _root.folded ? "▸" : "▾"
                        color: Style.fgMuted
                    }
                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("OSC Monitor")
                        font.bold: true
                        color: Style.fgStrong
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: _root.docked
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: _root.folded = !_root.folded
                }
            }

            SearchBox {
                id: _filter
                objectName: "oscMonitorFilter"
                visible: !_root.folded
                Layout.fillWidth: true
                placeholder: qsTr("Filter: address, value, from / to or input")
                count: _model.count
                onTextChanged: _model.filterText = text
            }

            Item {
                visible: _root.folded
                Layout.fillWidth: true
            }

            Label {
                objectName: "oscMonitorNote"
                visible: !_root.folded && _root.note.length > 0
                text: _root.note
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
                elide: Text.ElideRight
                Layout.maximumWidth: Style.dp(320)
            }

            Button {
                objectName: "oscMonitorPause"
                visible: !_root.folded
                implicitHeight: Style.dp(28)
                text: _model.paused ? qsTr("Resume") : qsTr("Pause")
                onClicked: _model.paused = !_model.paused
                ToolTip.visible: hovered
                ToolTip.text: _model.paused ? qsTr("Show new messages again")
                                            : qsTr("Stop adding new messages to the list")
            }

            Switch {
                objectName: "oscMonitorOutgoing"
                visible: !_root.folded
                text: qsTr("Show outgoing")
                checked: _model.showOutgoing
                onToggled: _model.showOutgoing = checked
            }

            DangerButton {
                objectName: "oscMonitorClear"
                visible: !_root.folded
                implicitHeight: Style.dp(28)
                text: qsTr("Clear")
                onClicked: _model.clear()
            }

            Button {
                objectName: "oscMonitorPopOut"
                visible: _root.docked
                implicitHeight: Style.dp(28)
                text: qsTr("Pop out")
                onClicked: _root.popOutRequested()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Show the OSC Monitor in its own window")
            }

            Button {
                objectName: "oscMonitorClose"
                visible: _root.docked
                implicitWidth: Style.dp(28)
                implicitHeight: Style.dp(28)
                text: "×"
                onClicked: _root.closeRequested()
            }
        }

        // The table: a recessed well with its column heads on a raised strip.
        Rectangle {
            visible: !_root.folded
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
                        spacing: _root._gap

                        Repeater {
                            model: [qsTr("Time"), qsTr("In / Out"), qsTr("Address"),
                                    qsTr("Values"), qsTr("From / To"), qsTr("Input")]
                            Label {
                                required property int index
                                required property string modelData
                                objectName: "oscMonitorHead" + index
                                readonly property bool stretch: _root._widths[index] < 0
                                Layout.fillWidth: stretch
                                Layout.minimumWidth: stretch ? _root._addressMin : _root._widths[index]
                                Layout.preferredWidth: stretch ? _root._addressMin : _root._widths[index]
                                Layout.maximumWidth: stretch ? Number.POSITIVE_INFINITY
                                                             : _root._widths[index]
                                text: modelData
                                elide: Text.ElideRight
                                font.pixelSize: _root._headPx
                                color: Style.fgMuted
                            }
                        }
                        Item {
                            Layout.preferredWidth: _root._addWidth
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
                        required property bool blocked
                        required property string senderHost

                        width: ListView.view.width
                        height: Style.dp(26)
                        color: _hover.hovered ? Style.bgRaised : Style.clear

                        HoverHandler {
                            id: _hover
                        }

                        // Right-click: Allow this sender on a blocked row (S160),
                        // Add as Input… on a row with no input.
                        TapHandler {
                            acceptedButtons: Qt.RightButton
                            onTapped: (point) => _root.openRowMenu(
                                _row, point.position.x, point.position.y,
                                _row.index, _row.senderHost, _row.blocked, _row.noInput)
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
                            spacing: _root._gap

                            Label {
                                Layout.preferredWidth: _root._widths[0]
                                Layout.maximumWidth: _root._widths[0]
                                text: _row.time
                                elide: Text.ElideRight
                                font.pixelSize: _root._rowPx
                                color: Style.fgMuted
                            }
                            Label {
                                Layout.preferredWidth: _root._widths[1]
                                Layout.maximumWidth: _root._widths[1]
                                text: _row.direction === "out" ? qsTr("Out") : qsTr("In")
                                font.pixelSize: _root._rowPx
                                color: _row.direction === "out" ? Style.infoText : Style.fg
                            }
                            Label {
                                objectName: "oscMonitorAddress" + _row.index
                                Layout.fillWidth: true
                                Layout.minimumWidth: _root._addressMin
                                Layout.preferredWidth: _root._addressMin
                                text: _row.address
                                elide: Text.ElideMiddle
                                font.family: Style.monoFont
                                font.pixelSize: Style.dp(12)
                                color: Style.fgStrong
                            }
                            Label {
                                Layout.preferredWidth: _root._widths[3]
                                Layout.maximumWidth: _root._widths[3]
                                text: _row.values
                                elide: Text.ElideRight
                                font.family: Style.monoFont
                                font.pixelSize: Style.dp(12)
                                color: Style.fg
                            }
                            Label {
                                Layout.preferredWidth: _root._widths[4]
                                Layout.maximumWidth: _root._widths[4]
                                text: _row.peer
                                elide: Text.ElideRight
                                font.pixelSize: _root._rowPx
                                color: Style.fgMuted
                            }
                            Label {
                                objectName: "oscMonitorInput" + _row.index
                                Layout.preferredWidth: _root._widths[5]
                                Layout.maximumWidth: _root._widths[5]
                                // "blocked": the sender isn't on the allow-list (S160).
                                text: _row.matched
                                elide: Text.ElideRight
                                font.pixelSize: _root._rowPx
                                color: _row.blocked ? Style.dangerText
                                       : (_row.noInput ? Style.fgMuted : Style.fg)
                                font.italic: _row.noInput || _row.blocked
                            }
                            Item {
                                Layout.preferredWidth: _root._addWidth
                                Layout.fillHeight: true

                                // Small outline button (the Button Map's panel buttons).
                                Rectangle {
                                    objectName: "oscMonitorAddRow" + _row.index
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: _row.noInput && !_root.editorLocked
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
                                        onClicked: _root.addAsInput(_row.index)
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

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Menus
import Gremlin.Style
import Gremlin.UI

// Live Log Reader › Trace (D-01-TRACE): tick the controls to follow, turn
// Tracing on, and each ticked control's RAW, WIRING and OUTPUT lines show
// here (and in trace.log). Tracing keeps running when the window closes;
// the red debug mode shows it is on.
ColumnLayout {
    id: _root

    // The tab's TraceView (DialogLiveLog.qml keeps it for the tab's dot).
    required property TraceView view
    // Keeps to the newest line while scrolled to the end.
    property bool follow: true

    spacing: Style.dp(8)

    // Polled only while the tab shows.
    Timer {
        interval: 250
        running: _root.visible
        repeat: true
        triggeredOnStart: true
        onTriggered: _root.view.refresh()
    }
    onVisibleChanged: if (visible) view.reloadTree()

    Connections {
        target: _root.view
        function onLinesAdded() {
            if (_root.follow)
                Qt.callLater(_lines.positionViewAtEnd)
        }
    }

    // A tick box: 0 off, 1 partly (some of a device's controls), 2 on.
    component Tick: Rectangle {
        id: _tick

        property int tickState: 0
        signal clicked()

        implicitWidth: Style.dp(15)
        implicitHeight: Style.dp(15)
        radius: Style.dp(3)
        color: tickState > 0 ? Style.accent : Style.bgWell
        border.color: tickState > 0 ? Style.accent : Style.lineStrong
        Label {
            anchors.centerIn: parent
            text: _tick.tickState === 2 ? "✓" : _tick.tickState === 1 ? "–" : ""
            color: Style.onColor
            font.pixelSize: Style.dp(11)
            font.bold: true
        }
        MouseArea {
            anchors.fill: parent
            anchors.margins: -Style.dp(3)
            cursorShape: Qt.PointingHandCursor
            onClicked: _tick.clicked()
        }
    }

    // A point's tag, coloured per point.
    component PointTag: Rectangle {
        id: _tag

        property string point: ""

        implicitWidth: Math.max(Style.dp(64), _tagText.implicitWidth + Style.dp(12))
        implicitHeight: _tagText.implicitHeight + Style.dp(2)
        radius: Style.dp(3)
        color: point === "RAW" ? Style.infoFill
            : point === "WIRING" ? Style.bgSelected
            : point === "OUTPUT" ? Style.okFill
            : point === "BLOCKED" ? Style.dangerFill
            : point === "EVENT" ? Style.bgRaised
            : Style.noteFill
        Label {
            id: _tagText
            anchors.centerIn: parent
            text: _tag.point
            font.pixelSize: Style.dp(11)
            font.bold: true
            color: _tag.point === "RAW" ? Style.infoText
                : _tag.point === "WIRING" ? Style.fgStrong
                : _tag.point === "OUTPUT" ? Style.okText
                : _tag.point === "BLOCKED" ? Style.dangerTextSoft
                : _tag.point === "EVENT" ? Style.fg
                : Style.noteText
        }
    }

    // The switch, the filters and the buttons.
    RowLayout {
        Layout.fillWidth: true
        spacing: Style.dp(8)

        Switch {
            id: _switch
            objectName: "traceSwitch"
            text: _root.view.tracing ? "Tracing on" : "Tracing off"
            font.bold: true
            checked: _root.view.tracing
            onToggled: _root.view.tracing = checked
            ToolTip.visible: hovered
            ToolTip.text: _root.view.tracing
                ? "Stop tracing (it also stops from Debug › Tracing)"
                : "Follow the ticked controls from the device to vJoy; "
                    + "keeps running when this window closes"
        }
        Label {
            objectName: "traceSince"
            text: _root.view.sinceText
            color: Style.okText
            visible: text.length > 0
        }

        SearchBox {
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(8)
            Layout.alignment: Qt.AlignTop
            placeholder: "Find"
            count: _root.view.shownCount
            onTextChanged: _root.view.find = text
        }

        Label { text: "Show" }
        ComboBox {
            implicitContentWidthPolicy: ComboBox.WidestText
            model: ["All", "Warnings"]
            currentIndex: _root.view.warningsOnly ? 1 : 0
            onActivated: _root.view.warningsOnly = currentIndex === 1
        }

        Button {
            id: _pointsButton
            text: "Points: " + _root.view.pointsText + " ▾"
            onClicked: _pointsMenu.open()
            ThemedMenu {
                id: _pointsMenu
                y: _pointsButton.height
                Repeater {
                    model: _root.view.pointNames
                    delegate: ThemedMenuItem {
                        required property string modelData
                        text: modelData
                        checkable: true
                        checked: _root.view.points.indexOf(modelData) >= 0
                        onTriggered: _root.view.setPoint(modelData, checked)
                    }
                }
            }
        }

        Button {
            text: qsTr("Clear View")
            ToolTip.visible: hovered
            ToolTip.text: "Empty this view (trace.log keeps every line)"
            onClicked: {
                _root.follow = true
                _root.view.clearView()
            }
        }
        Button {
            text: qsTr("Show Trace File")
            onClicked: _root.view.showFile()
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Style.dp(8)

        // Left: the controls to trace.
        Rectangle {
            Layout.preferredWidth: Style.dp(320)
            Layout.fillHeight: true
            color: Style.bgCard
            border.color: Style.line
            radius: Style.dp(3)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Style.dp(1)
                spacing: 0

                Label {
                    Layout.margins: Style.dp(8)
                    text: "CONTROLS TO TRACE"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(11)
                }

                ListView {
                    id: _tree
                    objectName: "traceTree"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: _root.view.tree
                    ScrollBar.vertical: ScrollBar {}

                    delegate: Item {
                        id: _row

                        required property int index
                        required property string rowKind
                        required property string rowText
                        required property string target
                        required property int check
                        required property string countText
                        required property bool expanded
                        required property string device
                        required property string controlKind
                        required property int controlIndex

                        width: ListView.view.width
                        implicitHeight: rowKind === "sep" ? Style.dp(9)
                            : rowKind === "header" ? Style.dp(24)
                            : Style.dp(26)
                        objectName: "traceRow_" + rowKind + "_" + rowText

                        Rectangle {
                            visible: _row.rowKind === "sep"
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            height: 1
                            color: Style.line
                        }

                        Label {
                            visible: _row.rowKind === "header"
                            anchors.left: parent.left
                            anchors.leftMargin: Style.dp(46)
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: Style.dp(3)
                            text: _row.rowText.toUpperCase()
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(11)
                        }

                        RowLayout {
                            visible: _row.rowKind !== "sep" && _row.rowKind !== "header"
                            anchors.fill: parent
                            anchors.leftMargin: _row.rowKind === "control" ? Style.dp(46)
                                : _row.rowKind === "oos" ? Style.dp(30) : Style.dp(8)
                            anchors.rightMargin: Style.dp(10)
                            spacing: Style.dp(7)

                            // A device opens to its controls.
                            Label {
                                visible: _row.rowKind === "device"
                                Layout.preferredWidth: Style.dp(12)
                                text: _row.countText === "" ? "" : (_row.expanded ? "▾" : "▸")
                                color: Style.fgMuted
                                MouseArea {
                                    anchors.fill: parent
                                    anchors.margins: -Style.dp(4)
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: _root.view.toggleOpen(_row.device)
                                }
                            }
                            Tick {
                                objectName: "traceTick_" + _row.rowKind + "_" + _row.rowText
                                tickState: _row.check
                                onClicked: {
                                    var on = _row.check !== 2
                                    if (_row.rowKind === "device")
                                        _root.view.setDevice(_row.device, on)
                                    else if (_row.rowKind === "oos")
                                        _root.view.setOutOfStep(_row.device, on)
                                    else if (_row.rowKind === "hidhide")
                                        _root.view.setHidhide(on)
                                    else
                                        _root.view.setTick(_row.device, _row.controlKind,
                                                           _row.controlIndex, on)
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: _row.rowText
                                elide: Text.ElideRight
                                font.bold: _row.rowKind === "device"
                                font.pixelSize: _row.rowKind === "oos" ? Style.dp(12) : Style.fontSize
                                color: _row.rowKind === "device" ? Style.fgStrong : Style.fg
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: _row.rowKind === "device" && _row.countText !== ""
                                    onClicked: _root.view.toggleOpen(_row.device)
                                }
                            }
                            Label {
                                visible: text.length > 0
                                text: _row.rowKind === "control" ? _row.target : _row.countText
                                color: _row.rowKind === "control" ? Style.fgDisabled : Style.fgMuted
                                font.family: _row.rowKind === "control" ? Style.monoFont : Style.uiFont
                                font.pixelSize: Style.dp(11)
                            }
                        }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    Layout.margins: Style.dp(8)
                    wrapMode: Text.WordWrap
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(11)
                    text: "Ticks are kept. Tracing always starts off when the program "
                        + "starts. Every trace also writes device plug/unplug, "
                        + "Start/Stop and HidHide changes."
                }
            }
        }

        // Right: the notice, the lines and the status bar.
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.dp(8)

            Rectangle {
                objectName: "traceNotice"
                visible: _root.view.notice.length > 0
                Layout.fillWidth: true
                implicitHeight: _noticeRow.implicitHeight + Style.dp(14)
                radius: Style.dp(3)
                color: Style.noteFill
                border.color: Style.warn

                RowLayout {
                    id: _noticeRow
                    anchors.fill: parent
                    anchors.margins: Style.dp(7)
                    spacing: Style.dp(10)
                    Label {
                        Layout.fillWidth: true
                        text: "⚠ " + _root.view.notice
                        color: Style.noteText
                        wrapMode: Text.WordWrap
                    }
                    Button {
                        text: qsTr("Go to line")
                        onClicked: {
                            var at = _root.view.noticeLine()
                            if (at < 0)
                                return
                            _root.follow = false
                            _lines.currentIndex = at
                            _lines.positionViewAtIndex(at, ListView.Center)
                        }
                    }
                    Button {
                        text: "✕"
                        flat: true
                        ToolTip.visible: hovered
                        ToolTip.text: "Hide this notice (the line stays)"
                        onClicked: _root.view.dismissNotice()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Style.bgWell
                border.color: Style.line
                radius: Style.dp(3)
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Style.dp(1)
                    spacing: 0

                    // Column heads.
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: Style.dp(26)
                        color: Style.bgCard
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Style.dp(10)
                            spacing: Style.dp(10)
                            Repeater {
                                model: [["TIME", 96], ["CONTROL", 150], ["POINT", 84], ["DETAIL", -1]]
                                delegate: Label {
                                    required property var modelData
                                    text: modelData[0]
                                    Layout.preferredWidth: modelData[1] > 0 ? Style.dp(modelData[1]) : -1
                                    Layout.fillWidth: modelData[1] < 0
                                    color: Style.fgMuted
                                    font.pixelSize: Style.dp(11)
                                    font.bold: true
                                }
                            }
                        }
                    }

                    ListView {
                        id: _lines
                        objectName: "traceLines"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: _root.view.lines
                        currentIndex: -1
                        ScrollBar.vertical: ScrollBar {}
                        onMovementEnded: _root.follow = atYEnd

                        delegate: Rectangle {
                            id: _line

                            required property int index
                            required property string time
                            required property string control
                            required property string point
                            required property string detail
                            required property bool warning

                            width: ListView.view.width
                            implicitHeight: Math.max(_detail.implicitHeight, Style.dp(20)) + Style.dp(6)
                            color: ListView.isCurrentItem ? Style.bgSelected
                                : warning ? Style.noteFill : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Style.dp(10)
                                anchors.rightMargin: Style.dp(10)
                                spacing: Style.dp(10)
                                Label {
                                    Layout.preferredWidth: Style.dp(96)
                                    Layout.alignment: Qt.AlignTop
                                    Layout.topMargin: Style.dp(3)
                                    text: _line.time
                                    color: Style.fgMuted
                                    font.family: Style.monoFont
                                    font.pixelSize: Style.dp(12)
                                }
                                Label {
                                    Layout.preferredWidth: Style.dp(150)
                                    Layout.alignment: Qt.AlignTop
                                    Layout.topMargin: Style.dp(3)
                                    text: _line.control || "—"
                                    elide: Text.ElideRight
                                    color: Style.fg
                                    font.family: Style.monoFont
                                    font.pixelSize: Style.dp(12)
                                }
                                Item {
                                    Layout.preferredWidth: Style.dp(84)
                                    Layout.preferredHeight: _pt.implicitHeight
                                    Layout.alignment: Qt.AlignTop
                                    Layout.topMargin: Style.dp(3)
                                    PointTag {
                                        id: _pt
                                        point: _line.point
                                    }
                                }
                                Label {
                                    id: _detail
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignTop
                                    Layout.topMargin: Style.dp(3)
                                    text: _line.detail
                                    wrapMode: Text.Wrap
                                    color: Style.fg
                                    font.family: Style.monoFont
                                    font.pixelSize: Style.dp(12)
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: _lines.count === 0
                            width: parent.width - Style.dp(40)
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            color: Style.fgMuted
                            text: _root.view.tracing
                                ? "Tracing. Use a ticked control: its lines show here."
                                : "Tick the controls to follow, then turn Tracing on."
                        }
                    }
                }
            }

            // Status bar.
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: _status.implicitHeight + Style.dp(12)
                color: Style.bgCard
                border.color: Style.line
                radius: Style.dp(3)
                RowLayout {
                    id: _status
                    anchors.fill: parent
                    anchors.leftMargin: Style.dp(10)
                    anchors.rightMargin: Style.dp(10)
                    spacing: Style.dp(18)
                    Label {
                        objectName: "traceStatusTicked"
                        textFormat: Text.StyledText
                        color: Style.fgMuted
                        text: "<b>" + _root.view.deviceCount + "</b> "
                            + (_root.view.deviceCount === 1 ? "device" : "devices")
                            + " · <b>" + _root.view.controlCount + "</b> controls ticked"
                    }
                    Label {
                        objectName: "traceStatusLines"
                        textFormat: Text.StyledText
                        color: Style.fgMuted
                        text: _root.view.shownCount === _root.view.lineCount
                            ? "<b>" + _root.view.lineCount + "</b> lines"
                            : "<b>" + _root.view.shownCount + "</b> of "
                                + _root.view.lineCount + " lines"
                    }
                    Label {
                        objectName: "traceStatusFile"
                        color: Style.fgMuted
                        text: _root.view.fileText
                    }
                    Label {
                        color: Style.fgMuted
                        text: "In Save Diagnostics"
                    }
                    Item { Layout.fillWidth: true }
                }
            }
        }
    }
}

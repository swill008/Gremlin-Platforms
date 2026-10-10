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
    // The ALL GAME DEVICES IN WINDOWS list is open (S3; closed at start,
    // kept in memory only).
    property bool showDetails: false
    // Tab shown: "devices" or "logs".
    property string tab: "devices"
    // The compact view's copy of tester.allDevices, refreshed ~20 a second.
    property var compactDevices: []

    readonly property var rows: tester.rows
    readonly property var sel: tester.selected
    readonly property int buttonCount: tester.buttons.length

    Component.onCompleted: {
        Style.isDarkMode = true
        tester.allDevicesShown = _win.showAll
    }
    // Follow input never switches away from the All devices view.
    onShowAllChanged: tester.allDevicesShown = _win.showAll

    // Follow input picked a row: bring it into view in the list.
    Connections {
        target: tester
        function onInputFollowed(key) {
            const row = _win.findRow(key)
            if (!row)
                return
            const top = row.mapToItem(_listCol, 0, 0).y
            if (top < _list.contentY)
                _list.contentY = top
            else if (top + row.height > _list.contentY + _list.height)
                _list.contentY = Math.min(top + row.height - _list.height,
                    Math.max(0, _list.contentHeight - _list.height))
        }
    }

    function findRow(key) {
        for (let i = 0; i < _rowRepeater.count; ++i) {
            const entry = _rowRepeater.itemAt(i)
            if (entry && entry.modelData.key === key)
                return entry
        }
        return null
    }

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

        // HidHide changed after this tester started: restart it.
        Rectangle {
            objectName: "staleBanner"
            Layout.fillWidth: true
            Layout.preferredHeight: _staleRow.implicitHeight + Style.dp(20)
            visible: tester.staleBanner !== ""
            color: Style.alpha(Style.warn, 0.18)

            RowLayout {
                id: _staleRow
                anchors.fill: parent
                anchors.leftMargin: Style.dp(14)
                anchors.rightMargin: Style.dp(14)
                spacing: Style.dp(12)

                Text {
                    objectName: "staleText"
                    Layout.fillWidth: true
                    text: "⚠ " + tester.staleBanner
                    wrapMode: Text.Wrap
                    font.family: Style.uiFont
                    font.pixelSize: Style.dp(13)
                    color: Style.warn
                }
                TesterButton {
                    objectName: "restartTesterButton"
                    text: "Restart tester"
                    checked: true
                    onClicked: tester.restartTester()
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Style.warn
            }
        }

        // Tabs: Devices | Logs.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: _tabRow.implicitHeight + Style.dp(8)
            color: Style.bgCard

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Style.line
            }
            Row {
                id: _tabRow
                x: Style.dp(12)
                anchors.bottom: parent.bottom
                spacing: Style.dp(2)
                Repeater {
                    model: [{id: "devices", label: "Devices"}, {id: "logs", label: "Logs"}]
                    delegate: Rectangle {
                        id: _tab
                        required property var modelData
                        readonly property bool on: _win.tab === modelData.id
                        objectName: "tab_" + modelData.id
                        width: _tabText.implicitWidth + Style.dp(32)
                        height: _tabText.implicitHeight + Style.dp(12)
                        radius: Style.dp(6)
                        color: on ? Style.bgPage
                            : _tabArea.containsMouse ? Style.alpha(Style.bgHover, 0.5) : Style.clear
                        border.color: on ? Style.line : Style.clear
                        Accessible.role: Accessible.PageTab
                        Accessible.name: modelData.label
                        // Square off the bottom so the tab joins the page below.
                        Rectangle {
                            visible: _tab.on
                            x: 1
                            width: parent.width - 2
                            y: parent.height - Style.dp(6)
                            height: Style.dp(7)
                            color: Style.bgPage
                        }
                        Text {
                            id: _tabText
                            anchors.centerIn: parent
                            text: _tab.modelData.label
                            font.family: Style.uiFont
                            font.pixelSize: Style.dp(13)
                            font.bold: _tab.on
                            color: _tab.on ? Style.fgStrong : Style.fgMuted
                        }
                        MouseArea {
                            id: _tabArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: _win.tab = _tab.modelData.id
                        }
                    }
                }
            }
            TesterSwitch {
                objectName: "followInputSwitch"
                anchors.right: parent.right
                anchors.rightMargin: Style.dp(14)
                anchors.verticalCenter: parent.verticalCenter
                visible: _win.tab === "devices"
                text: "Follow input"
                checked: tester.followInput
                onToggled: on => tester.followInput = on
            }
        }

        LogsView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: _win.tab === "logs"
        }

        // Body: device list | device view.
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: _win.tab === "devices"
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
                                id: _rowRepeater
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
                                        text: _entry.modelData.section || ""
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

                            // Every game device in Windows: a list only (path and
                            // ids), folded under Show details (S3).
                            Text {
                                objectName: "hidHeading"
                                visible: _detailsToggle.visible
                                width: parent.width
                                leftPadding: Style.dp(14)
                                topPadding: Style.dp(10)
                                text: "ALL GAME DEVICES IN WINDOWS (list only)"
                                font.family: Style.uiFont
                                font.pixelSize: Style.dp(11)
                                font.letterSpacing: Style.dp(0.8)
                                color: Style.fgMuted
                            }
                            Rectangle {
                                id: _detailsToggle
                                objectName: "showDetailsToggle"
                                visible: tester.hidDevices.length > 0 || tester.hidSkipped.length > 0
                                width: parent.width
                                height: _detailsText.implicitHeight + Style.dp(14)
                                color: _detailsArea.containsMouse ? Style.alpha(Style.bgHover, 0.4) : Style.clear
                                Accessible.role: Accessible.Button
                                Accessible.name: "Show details"
                                Text {
                                    id: _detailsText
                                    x: Style.dp(14)
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: (_win.showDetails ? "▾ " : "▸ ") + "Show details"
                                    font.family: Style.uiFont
                                    font.pixelSize: Style.dp(12.5)
                                    color: Style.accent
                                }
                                MouseArea {
                                    id: _detailsArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: _win.showDetails = !_win.showDetails
                                }
                            }
                            Column {
                                objectName: "detailsSection"
                                width: parent.width
                                visible: _win.showDetails && _detailsToggle.visible
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
                                // HID paths left out, dimmed, with the reason.
                                Repeater {
                                    model: tester.hidSkipped
                                    delegate: Column {
                                        required property var modelData
                                        objectName: "hidSkipped"
                                        width: _listCol.width
                                        opacity: 0.65
                                        leftPadding: Style.dp(40)
                                        rightPadding: Style.dp(14)
                                        topPadding: Style.dp(4)
                                        bottomPadding: Style.dp(4)
                                        Text {
                                            width: parent.width - parent.leftPadding - parent.rightPadding
                                            text: (modelData.name || "HID device")
                                                + (modelData.vid ? "  ·  VID " + modelData.vid
                                                   + " · PID " + modelData.pid : "")
                                            elide: Text.ElideRight
                                            font.family: Style.uiFont
                                            font.pixelSize: Style.dp(12.5)
                                            color: Style.fgMuted
                                        }
                                        Text {
                                            objectName: "hidSkippedLabel"
                                            width: parent.width - parent.leftPadding - parent.rightPadding
                                            text: modelData.label || ("left out: " + (modelData.reason || ""))
                                            elide: Text.ElideRight
                                            font.family: Style.uiFont
                                            font.pixelSize: Style.dp(11.5)
                                            font.italic: true
                                            color: modelData.denied ? Style.dangerTextSoft : Style.fgMuted
                                        }
                                        Text {
                                            width: parent.width - parent.leftPadding - parent.rightPadding
                                            text: modelData.path || ""
                                            elide: Text.ElideMiddle
                                            font.family: Style.monoFont
                                            font.pixelSize: Style.dp(10.5)
                                            color: Style.fgDisabled
                                        }
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
                                Text { objectName: "shouldBe"; text: _win.sel.expected || ""; visible: !!_win.sel.expected; Layout.columnSpan: 2; Layout.fillWidth: true; wrapMode: Text.Wrap; font.family: Style.uiFont; font.pixelSize: Style.dp(12.5); color: Style.fg }
                            }
                        }

                        Text {
                            objectName: "notSeenDetail"
                            visible: _win.sel.seen === false
                            Layout.fillWidth: true
                            text: _win.sel.detail || ""
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

                        // Buttons: 16 a row; every row that fits in the pane's free
                        // height is shown, scroll for more (02 S147).
                        Text {
                            id: _buttonsLabel
                            visible: _win.buttonCount > 0
                            readonly property int firstShown: Math.floor(_btnFlick.contentY / _btnFlick.rowH) * 16 + 1
                            readonly property int lastShown: Math.min(_win.buttonCount, firstShown + _btnFlick.shownRows * 16 - 1)
                            text: _btnFlick.interactive
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
                            // Height left for buttons: the pane less what is above
                            // them, the hats below them and the margins.
                            readonly property real freeHeight: _detail.height - _detailCol.y - y
                                - (_hatsLabel.visible ? 2 * _detailCol.spacing + _hatsLabel.implicitHeight + _hatsRow.implicitHeight : 0)
                                - Style.dp(14)
                            readonly property int shownRows: Math.min(rowCount,
                                Math.max(2, Math.floor(freeHeight / rowH)))
                            Layout.fillWidth: true
                            Layout.preferredHeight: shownRows * rowH
                            visible: _win.buttonCount > 0
                            clip: true
                            contentHeight: rowCount * rowH
                            boundsBehavior: Flickable.StopAtBounds
                            interactive: rowCount > shownRows

                            // Brings button `index` (0-based) into view.
                            function showButton(index) {
                                const top = Math.floor(index / 16) * rowH
                                if (top < contentY)
                                    contentY = top
                                else if (top + rowH > contentY + height)
                                    contentY = Math.min(top + rowH - height,
                                        Math.max(0, contentHeight - height))
                            }

                            // Follow input on: a newly pressed button outside the
                            // shown rows scrolls into view; off, the view stays (02 S148).
                            property var lastButtons: []
                            Connections {
                                target: tester
                                function onLiveChanged() {
                                    const now = tester.buttons
                                    const before = _btnFlick.lastButtons
                                    _btnFlick.lastButtons = now
                                    if (!tester.followInput || !_btnFlick.interactive)
                                        return
                                    for (let i = 0; i < now.length; ++i) {
                                        if (now[i] && !before[i]) {
                                            _btnFlick.showButton(i)
                                            return
                                        }
                                    }
                                }
                            }

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
                            // Scroll bar, when there are more rows than fit.
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
                            id: _hatsLabel
                            visible: tester.hats.length > 0
                            text: "HATS"
                            font.family: Style.uiFont
                            font.pixelSize: Style.dp(11)
                            font.letterSpacing: Style.dp(0.8)
                            color: Style.fgMuted
                        }
                        Row {
                            id: _hatsRow
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
            visible: _win.tab === "devices"
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

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only
// View-only dest monitor: feeder live, no wiring.

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Dialogs

import Gremlin.Device
import Gremlin.Style

Item {
    id: _root

    property var moduleModel: null
    property string guid: ""
    property string deviceName: ""
    property bool showPanel: false
    signal closePanel()
    readonly property bool runtimeActive: !!(backend && backend.gremlinActive)
    readonly property bool showLive: runtimeActive && !!( _live.driven)
    property int liveStamp: _live.stamp

    property string layout: "pads_meters_grid"
    property int padAX: 1
    property int padAY: 2
    property int padBX: 4
    property int padBY: 5
    property bool showPads: true
    property bool showHats: true
    property bool showMeters: true
    property string meterStyle: "vertical"
    property int meterWidth: 22
    property var meters: []
    property string buttonStyle: "tile"
    property string buttonSize: "medium"
    property int buttonColumns: 12
    property int buttonWidth: 64
    property string colorLive: "#22C55E"
    property string colorMeter: "#3B82F6"
    property string colorPress: "#22C55E"
    property string colorScreen: "#00000000"
    property string screenImage: ""
    property string _colorTarget: "live"
    property string toastText: "Display Options Saved"

    component TrackSpin: SpinBox {
        property int source: 0
        signal userSet(int value)
        editable: true
        Component.onCompleted: value = source
        onSourceChanged: if (value !== source) value = source
        onValueModified: userSet(value)
    }

    component FlagBox: CheckBox {
        property bool source: false
        signal userSet(bool value)
        Component.onCompleted: checked = source
        onSourceChanged: if (!pressed) checked = source
        onClicked: userSet(checked)
    }

    component FoldSection: ColumnLayout {
        id: fold
        property string title: ""
        property bool open: false
        signal toggled(bool value)
        default property alias body: _body.data
        Layout.fillWidth: true
        spacing: 4

        Rectangle {
            Layout.fillWidth: true
            height: 26
            color: "#27272A"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6
                Label {
                    text: fold.open ? "\u25BC" : "\u25B6"
                    color: "#E4E4E7"
                    font.pixelSize: 10
                }
                Label {
                    text: fold.title
                    color: "#E4E4E7"
                    font.pixelSize: 11
                    font.bold: true
                    Layout.fillWidth: true
                }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: fold.toggled(!fold.open)
            }
        }
        ColumnLayout {
            id: _body
            visible: fold.open
            Layout.fillWidth: true
            spacing: 4
        }
    }

    component ChoiceMenu: ComboBox {
        property var choices: []
        property string current: ""
        signal userSet(string value)
        Layout.fillWidth: true
        function pick(value) {
            for (var i = 0; i < choices.length; ++i)
                if (choices[i].value === value)
                    return i
            return 0
        }
        model: {
            var labels = []
            for (var i = 0; i < choices.length; ++i)
                labels.push(choices[i].label)
            return labels
        }
        Component.onCompleted: currentIndex = pick(current)
        onCurrentChanged: currentIndex = pick(current)
        onActivated: if (choices[currentIndex]) userSet(choices[currentIndex].value)
    }

    component AxisMenu: ComboBox {
        property int hw: 0
        signal userSet(int value)
        Layout.fillWidth: true
        property int options: (_root.axisPick || []).length
        function pick(value) {
            var rows = _root.axisPick || []
            for (var i = 0; i < rows.length; ++i)
                if (rows[i].hw === value)
                    return i
            return 0
        }
        model: {
            var labels = []
            var rows = _root.axisPick || []
            for (var i = 0; i < rows.length; ++i)
                labels.push(rows[i].label)
            return labels
        }
        Component.onCompleted: currentIndex = pick(hw)
        onHwChanged: currentIndex = pick(hw)
        onOptionsChanged: currentIndex = pick(hw)
        onActivated: {
            var rows = _root.axisPick || []
            if (rows[currentIndex])
                userSet(rows[currentIndex].hw)
        }
    }

    readonly property bool padsOn: showPads
    readonly property bool padAOn: padsOn && (padAX > 0 || padAY > 0)
    readonly property bool padBOn: padsOn && (padBX > 0 || padBY > 0)
    readonly property bool metersOn: showMeters
    readonly property int btnCellW: buttonSize === "small" ? 52 : (buttonSize === "large" ? 88 : 64)
    readonly property int btnCellH: buttonSize === "small" ? 48 : (buttonSize === "large" ? 68 : 56)

    ModuleClaimedInputModel {
        id: _claimed
        guid: _root.guid
        deviceName: _root.deviceName
        onCountChanged: _root.rebuild()
    }

    ColorDialog {
        id: _colorDlg
        title: "Choose color"
        onAccepted: {
            var c = selectedColor.toString()
            if (_colorTarget === "meter")
                colorMeter = c
            else if (_colorTarget === "press")
                colorPress = c
            else if (_colorTarget === "screen")
                colorScreen = c
            else
                colorLive = c
        }
    }

    FileDialog {
        id: _screenImageDlg
        title: "Screen background"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.bmp *.webp)"]
        fileMode: FileDialog.OpenFile
        onAccepted: screenImage = selectedFile.toString()
    }

    ListModel { id: _copySources }

    DeviceLiveState {
        id: _live
        guid: _root.guid
        deviceName: _root.deviceName
        liveWhileActive: true
    }

    Connections {
        target: moduleModel
        function onClaimsChanged() { _claimed.reload(); _root.rebuild() }
        function onViewChanged() { _root.loadView() }
    }

    ListModel { id: axisModel }
    ListModel { id: buttonModel }
    ListModel { id: hatModel }
    property var axisPick

    function axisShort(hw, name) {
        var map = { 1: "X", 2: "Y", 3: "Z", 4: "Rx", 5: "Ry", 6: "Rz", 7: "S1", 8: "S2" }
        if (map[hw])
            return map[hw]
        return name || ("A" + hw)
    }

    function axisLabel(hw, name) {
        return axisShort(hw, name) + " — Axis " + hw
    }

    function fillAxisPick() {
        var pick = [{ "hw": 0, "label": "Off" }]
        for (var i = 0; i < axisModel.count; ++i) {
            var row = axisModel.get(i)
            pick.push({ "hw": row.hw, "label": axisLabel(row.hw, row.name) })
        }
        axisPick = pick
    }

    function liveVal(idx) {
        liveStamp
        if (!showLive || idx < 0)
            return 0
        return _live.valueAt(idx)
    }

    function findAxis(hw) {
        for (var i = 0; i < axisModel.count; ++i) {
            var row = axisModel.get(i)
            if (row.hw === hw)
                return row
        }
        return null
    }

    function allAxisHw() {
        var out = []
        for (var i = 0; i < axisModel.count; ++i)
            out.push(axisModel.get(i).hw)
        return out
    }

    function meterOn(hw) {
        if (!meters || meters.length === 0)
            return true
        if (meters.length === 1 && Number(meters[0]) === 0)
            return false
        return meters.indexOf(hw) >= 0 || meters.indexOf(Number(hw)) >= 0
    }

    function toggleMeter(hw, on) {
        var list = (meters || []).slice()
        if (list.length === 1 && Number(list[0]) === 0)
            list = []
        else if (list.length === 0)
            list = allAxisHw()
        var i = list.indexOf(hw)
        if (i < 0)
            i = list.indexOf(Number(hw))
        if (on && i < 0)
            list.push(hw)
        if (!on && i >= 0)
            list.splice(i, 1)
        if (list.length === 0)
            list = [0]
        meters = list
    }

    property string savedView: ""

    function rememberView() {
        savedView = JSON.stringify(viewPayload())
    }

    function hasUnsaved() {
        return savedView.length > 0 && JSON.stringify(viewPayload()) !== savedView
    }

    function viewPayload() {
        return {
            "layout": (showPads && showMeters) ? "pads_meters_grid" : (showMeters ? "meters_grid" : "grid_only"),
            "padAX": padAX,
            "padAY": padAY,
            "padBX": padBX,
            "padBY": padBY,
            "showPads": showPads,
            "showHats": showHats,
            "showMeters": showMeters,
            "meterStyle": meterStyle,
            "meterWidth": meterWidth,
            "meters": meters,
            "buttonStyle": buttonStyle,
            "buttonSize": buttonSize,
            "buttonColumns": buttonColumns,
            "buttonWidth": buttonWidth,
            "colorLive": colorLive,
            "colorMeter": colorMeter,
            "colorPress": colorPress,
            "colorScreen": colorScreen,
            "screenImage": screenImage,
            "sections": sectionState()
        }
    }

    property bool openScreen: false
    property bool openLayout: false
    property bool openPads: false
    property bool openMeters: false
    property bool openButtons: false
    property bool openColors: false

    function sectionState() {
        return {
            "screen": openScreen,
            "layout": openLayout,
            "pads": openPads,
            "meters": openMeters,
            "buttons": openButtons,
            "colors": openColors
        }
    }

    function applySections(raw) {
        var s = raw || {}
        openScreen = !!s.screen
        openLayout = !!s.layout
        openPads = !!s.pads
        openMeters = !!s.meters
        openButtons = !!s.buttons
        openColors = !!s.colors
    }

    function setAllSections(open) {
        openScreen = open
        openLayout = open
        openPads = open
        openMeters = open
        openButtons = open
        openColors = open
    }

    function applyViewValues(v) {
        layout = v.layout || "pads_meters_grid"
        padAX = (v.padAX === undefined || v.padAX === null) ? 1 : v.padAX
        padAY = (v.padAY === undefined || v.padAY === null) ? 2 : v.padAY
        padBX = (v.padBX === undefined || v.padBX === null) ? 4 : v.padBX
        padBY = (v.padBY === undefined || v.padBY === null) ? 5 : v.padBY
        if (v.showPads === undefined)
            showPads = !(layout === "meters_grid" || layout === "grid_only")
        else
            showPads = v.showPads !== false
        showHats = v.showHats !== false
        if (v.showMeters === undefined)
            showMeters = layout !== "grid_only"
        else
            showMeters = v.showMeters !== false
        meterStyle = v.meterStyle || "vertical"
        meterWidth = v.meterWidth || 22
        meters = (v.meters === undefined || v.meters === null) ? [] : v.meters
        buttonStyle = v.buttonStyle || "tile"
        buttonSize = v.buttonSize || "medium"
        buttonColumns = v.buttonColumns || 12
        buttonWidth = v.buttonWidth || 64
        colorLive = v.colorLive || "#22C55E"
        colorMeter = v.colorMeter || "#3B82F6"
        colorPress = v.colorPress || "#22C55E"
        colorScreen = v.colorScreen || "#00000000"
        screenImage = v.screenImage || ""
        applySections(v.sections)
    }

    function loadView() {
        if (!moduleModel || !deviceName)
            return
        refreshCopySources()
        try {
            var v = JSON.parse(moduleModel.viewConfigJson(deviceName, guid))
        } catch (e) {
            return
        }
        applyViewValues(v)
        rememberView()
    }

    function refreshCopySources() {
        _copySources.clear()
        if (!moduleModel || !moduleModel.otherDestViews)
            return
        var rows = []
        try {
            rows = JSON.parse(moduleModel.otherDestViews(deviceName) || "[]")
        } catch (e) {
            return
        }
        for (var i = 0; i < rows.length; ++i)
            _copySources.append({
                "label": rows[i].name,
                "name": rows[i].name,
                "guid": rows[i].guid || ""
            })
    }

    function copyViewFrom(name, guid) {
        if (!moduleModel || !name)
            return
        try {
            var v = JSON.parse(moduleModel.viewConfigJson(name, guid || ""))
        } catch (e) {
            return
        }
        applyViewValues(v)
    }

    function saveView() {
        var ok = false
        if (moduleModel && deviceName)
            ok = moduleModel.saveViewConfig(deviceName, guid, JSON.stringify(viewPayload()))
        if (ok) {
            rememberView()
            _saveGate.announce(true, "Saved to the module file.")
        } else {
            _saveGate.announce(false, "Not written. It is still only on this screen.")
        }
    }

    function requestLeave() {
        if (!hasUnsaved()) {
            leaveResolved()
            return
        }
        _leaveOnly = true
        _saveGate.detail = "Display options are not saved. Leave this device and they will be lost."
        _saveGate.ask()
    }

    property bool _leaveOnly: false
    signal leaveResolved()
    signal leaveCancelled()

    function requestClose() {
        _leaveOnly = false
        if (hasUnsaved()) {
            _saveGate.detail = "Display options are not saved. Close this panel and they will be lost."
            _saveGate.ask()
            return
        }
        closePanel()
    }

    function resetView() {
        layout = "pads_meters_grid"
        padAX = 1; padAY = 2; padBX = 4; padBY = 5
        showPads = true
        showHats = true
        showMeters = true
        meterStyle = "vertical"
        meterWidth = 22
        meters = []
        buttonStyle = "tile"
        buttonSize = "medium"
        buttonColumns = 12
        buttonWidth = 64
        colorLive = "#22C55E"
        colorMeter = "#3B82F6"
        colorPress = "#22C55E"
        colorScreen = "#00000000"
        screenImage = ""
        setAllSections(false)
        toastText = "Options have been reset"
        _savedToast.open()
    }

    function rebuild() {
        axisModel.clear()
        buttonModel.clear()
        hatModel.clear()
        var n = _claimed.count
        if (n > 0) {
            for (var i = 0; i < n; ++i) {
                var kind = _claimed.kindAt(i)
                var rec = {
                    "idx": _claimed.deviceIndexAt(i),
                    "hw": _claimed.hwIdAt(i),
                    "name": _claimed.nameAt(i)
                }
                if (kind === "axis")
                    axisModel.append(rec)
                else if (kind === "button")
                    buttonModel.append(rec)
                else if (kind === "hat")
                    hatModel.append(rec)
            }
            fillAxisPick()
            return
        }
        for (var j = 0; j < 128; ++j) {
            var k = _live.kindAt(j)
            if (!k)
                break
            var hw = j + 1
            if (k === "axis")
                axisModel.append({ "idx": j, "hw": hw, "name": axisShort(hw, "") })
            else if (k === "button")
                buttonModel.append({ "idx": j, "hw": hw, "name": "" + hw })
            else if (k === "hat")
                hatModel.append({ "idx": j, "hw": hw, "name": "Hat " + hw })
        }
        fillAxisPick()
    }

    Component.onCompleted: { loadView(); rebuild() }
    onGuidChanged: Qt.callLater(function() { loadView(); rebuild() })
    onDeviceNameChanged: Qt.callLater(function() { loadView(); rebuild() })

    component CrossPad: Rectangle {
        id: pad
        property real xVal: 0
        property real yVal: 0
        property string label: ""
        color: Style.background
        border.color: Style.lowColor
        border.width: 1
        implicitWidth: 220
        implicitHeight: 220

        Rectangle {
            width: parent.width - 24
            height: 1
            color: Style.lowColor
            anchors.centerIn: parent
        }
        Rectangle {
            width: 1
            height: parent.height - 24
            color: Style.lowColor
            anchors.centerIn: parent
        }
        Rectangle {
            width: 12
            height: 12
            radius: 6
            color: _root.colorLive
            visible: _root.showLive
            x: parent.width / 2 + (pad.xVal * (parent.width / 2 - 16)) - width / 2
            y: parent.height / 2 - (pad.yVal * (parent.height / 2 - 16)) - height / 2
        }
        Label {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: 6
            text: pad.label
            color: "#A1A1AA"
            font.pixelSize: 12
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: _root.colorScreen !== "#00000000"
        color: _root.colorScreen
    }
    Image {
        anchors.fill: parent
        visible: _root.screenImage.length > 0
        source: _root.screenImage
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 16

        ColumnLayout {
            visible: _root.padAOn || _root.padBOn || (_root.showHats && hatModel.count > 0)
            Layout.preferredWidth: 228
            Layout.maximumWidth: 228
            Layout.fillWidth: false
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            spacing: 12

            CrossPad {
                Layout.preferredWidth: 220
                Layout.preferredHeight: 220
                visible: _root.padAOn
                label: "X / Y"
                xVal: { var row = findAxis(padAX); return row ? liveVal(row.idx) : 0 }
                yVal: { var row = findAxis(padAY); return row ? liveVal(row.idx) : 0 }
            }
            CrossPad {
                Layout.preferredWidth: 220
                Layout.preferredHeight: 220
                visible: _root.padBOn
                label: "Rx / Ry"
                xVal: { var row = findAxis(padBX); return row ? liveVal(row.idx) : 0 }
                yVal: { var row = findAxis(padBY); return row ? liveVal(row.idx) : 0 }
            }
            Repeater {
                model: hatModel
                delegate: HatView {
                    required property int idx
                    required property int hw
                    required property string name
                    visible: _root.showHats
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 160
                    Layout.alignment: Qt.AlignHCenter
                    text: name.length ? name : ("Hat " + hw)
                    currentValue: {
                        liveStamp
                        if (!_root.showLive)
                            return Qt.point(0, 0)
                        return Qt.point(_live.hatXAt(idx), _live.hatYAt(idx))
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }

        Row {
            visible: _root.metersOn
            Layout.fillWidth: false
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            spacing: 10

            Repeater {
                model: axisModel
                delegate: Column {
                    required property int idx
                    required property int hw
                    required property string name
                    visible: meterOn(hw)
                    width: Math.max(48, _root.meterWidth + 26)
                    height: parent.height
                    spacing: 6

                    BetterProgressBar {
                        width: _root.meterWidth
                        height: parent.height - 44
                        anchors.horizontalCenter: parent.horizontalCenter
                        orientation: _root.meterStyle === "horizontal" ? BetterProgressBar.Orientation.Horizontal : BetterProgressBar.Orientation.Vertical
                        barSize: _root.meterWidth
                        fillColor: _root.colorMeter
                        from: -1
                        to: 1
                        value: liveVal(idx)
                    }
                    Label {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: axisShort(hw, name)
                        color: "#E4E4E7"
                        font.pixelSize: 12
                    }
                    Label {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: (liveVal(idx) >= 0 ? "+" : "") + liveVal(idx).toFixed(2)
                        color: "#A1A1AA"
                        font.pixelSize: 10
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 200
            clip: true

            Flickable {
                id: _buttons
                anchors.fill: parent
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: Math.max(width, _btnGrid.implicitWidth)
                contentHeight: Math.max(height, _btnGrid.implicitHeight)
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                GridLayout {
                    id: _btnGrid
                    columns: Math.max(1, _root.buttonColumns)
                    columnSpacing: 6
                    rowSpacing: 6

                    Repeater {
                        model: buttonModel
                        delegate: Rectangle {
                    required property int idx
                    required property int hw
                    required property string name
                    Layout.preferredWidth: Math.max(40, _root.buttonWidth)
                    Layout.preferredHeight: _root.btnCellH
                    Layout.minimumWidth: Math.max(40, _root.buttonWidth)
                    Layout.maximumWidth: Math.max(40, _root.buttonWidth)
                    Layout.minimumHeight: _root.btnCellH
                    Layout.maximumHeight: _root.btnCellH
                    Layout.fillWidth: false
                    property bool on: liveVal(idx) > 0.5 && _root.showLive
                    color: {
                        if (!on)
                            return Style.background
                        if (_root.buttonStyle === "compact")
                            return _root.colorPress
                        return Qt.rgba(0.133, 0.773, 0.369, 0.45)
                    }
                    border.color: on ? _root.colorPress : Style.lowColor
                    border.width: 1
                    radius: 3

                    Row {
                        anchors.centerIn: parent
                        spacing: 6
                        Rectangle {
                            visible: _root.buttonStyle === "led"
                            width: 10
                            height: 10
                            radius: 5
                            color: on ? _root.colorPress : Style.lowColor
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Column {
                            spacing: 0
                            Label {
                                text: "Button"
                                color: on ? "#F4F4F5" : "#A1A1AA"
                                font.pixelSize: _root.buttonSize === "small" ? 9 : 11
                                horizontalAlignment: Text.AlignHCenter
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Label {
                                text: "" + hw
                                color: on ? "#F4F4F5" : "#E4E4E7"
                                font.pixelSize: _root.buttonSize === "small" ? 12 : 14
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: _root.showPanel
            Layout.preferredWidth: 360
            Layout.maximumWidth: 360
            Layout.fillHeight: true
            color: "#18181B"
            border.color: "#3F3F46"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                RowLayout {
                    Label {
                        text: "Output Module View — Display Editor"
                        color: "#E4E4E7"
                        font.bold: true
                        font.pixelSize: 13
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "×"
                        implicitWidth: 28
                        onClicked: _root.requestClose()
                    }
                }
                RowLayout {
                    spacing: 8
                    Button { text: "Open all"; onClicked: setAllSections(true) }
                    Button { text: "Close all"; onClicked: setAllSections(false) }
                    Item { Layout.fillWidth: true }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ColumnLayout {
                        width: 330
                        spacing: 12

                        FoldSection {
                            title: "Screen"
                            open: openScreen
                            onToggled: (v) => { openScreen = v }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Color"; color: "#E4E4E7"; Layout.preferredWidth: 110 }
                                Button {
                                    Layout.fillWidth: true
                                    text: colorScreen === "#00000000" ? "None" : "Choose…"
                                    onClicked: {
                                        _colorTarget = "screen"
                                        _colorDlg.selectedColor = colorScreen === "#00000000" ? "#111113" : colorScreen
                                        _colorDlg.open()
                                    }
                                    background: Rectangle {
                                        color: colorScreen === "#00000000" ? "#27272A" : colorScreen
                                        border.color: "#3F3F46"
                                        border.width: 1
                                        radius: 3
                                    }
                                    contentItem: Label {
                                        text: parent.text
                                        color: "#F4F4F5"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                Button {
                                    text: "Clear"
                                    enabled: colorScreen !== "#00000000"
                                    onClicked: colorScreen = "#00000000"
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Image"; color: "#E4E4E7"; Layout.preferredWidth: 110 }
                                Button {
                                    Layout.fillWidth: true
                                    text: screenImage.length ? "Change…" : "Choose…"
                                    onClicked: _screenImageDlg.open()
                                }
                                Button {
                                    text: "Clear"
                                    enabled: screenImage.length > 0
                                    onClicked: screenImage = ""
                                }
                            }
                            Label {
                                visible: screenImage.length > 0
                                text: "The image covers the color."
                                color: "#A1A1AA"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }

                        FoldSection {
                            title: "Layout"
                            open: openLayout
                            onToggled: (v) => { openLayout = v }
                            FlagBox { text: "Show pads"; source: showPads; onUserSet: (v) => { showPads = v } }
                            FlagBox { text: "Show hats"; source: showHats; onUserSet: (v) => { showHats = v } }
                            FlagBox { text: "Show meters"; source: showMeters; onUserSet: (v) => { showMeters = v } }
                        }

                        FoldSection {
                            title: "Pads"
                            open: openPads
                            onToggled: (v) => { openPads = v }
                            Label {
                                visible: !showPads
                                text: "Pads hidden"
                                color: "#71717A"
                                font.pixelSize: 11
                            }
                            ColumnLayout {
                                visible: showPads
                                spacing: 4
                                Layout.fillWidth: true
                                Label { text: "X / Y pad"; color: "#E4E4E7"; font.pixelSize: 11 }
                                RowLayout {
                                    Label { text: "Horizontal"; color: "#A1A1AA"; Layout.preferredWidth: 80 }
                                    AxisMenu { hw: padAX; onUserSet: (v) => { padAX = v } }
                                }
                                RowLayout {
                                    Label { text: "Vertical"; color: "#A1A1AA"; Layout.preferredWidth: 80 }
                                    AxisMenu { hw: padAY; onUserSet: (v) => { padAY = v } }
                                }
                                Label { text: "Rx / Ry pad"; color: "#E4E4E7"; font.pixelSize: 11 }
                                RowLayout {
                                    Label { text: "Horizontal"; color: "#A1A1AA"; Layout.preferredWidth: 80 }
                                    AxisMenu { hw: padBX; onUserSet: (v) => { padBX = v } }
                                }
                                RowLayout {
                                    Label { text: "Vertical"; color: "#A1A1AA"; Layout.preferredWidth: 80 }
                                    AxisMenu { hw: padBY; onUserSet: (v) => { padBY = v } }
                                }
                            }
                        }

                        FoldSection {
                            title: "Meters"
                            open: openMeters
                            onToggled: (v) => { openMeters = v }
                            ChoiceMenu {
                                enabled: showMeters
                                current: meterStyle
                                choices: [
                                    { "label": "Vertical bar", "value": "vertical" },
                                    { "label": "Horizontal bar", "value": "horizontal" }
                                ]
                                onUserSet: (v) => { meterStyle = v }
                            }
                            RowLayout {
                                enabled: showMeters
                                Label { text: "Width"; color: "#E4E4E7" }
                                TrackSpin { from: 12; to: 48; source: meterWidth; onUserSet: (v) => { meterWidth = v } }
                            }
                            Label {
                                text: "Axes on bars"
                                color: "#E4E4E7"
                                font.pixelSize: 11
                            }
                            Label {
                                text: "Uncheck an axis to hide its bar."
                                color: "#A1A1AA"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                            GridLayout {
                                enabled: showMeters
                                columns: 2
                                Layout.fillWidth: true
                                columnSpacing: 8
                                rowSpacing: 0
                                Repeater {
                                    model: axisModel
                                    delegate: FlagBox {
                                        required property int hw
                                        required property string name
                                        Layout.preferredWidth: 155
                                        text: axisLabel(hw, name)
                                        source: meterOn(hw)
                                        onUserSet: (v) => toggleMeter(hw, v)
                                    }
                                }
                            }
                        }

                        FoldSection {
                            title: "Buttons"
                            open: openButtons
                            onToggled: (v) => { openButtons = v }
                            ChoiceMenu {
                                current: buttonStyle
                                choices: [
                                    { "label": "Tile", "value": "tile" },
                                    { "label": "LED + number", "value": "led" },
                                    { "label": "Compact", "value": "compact" }
                                ]
                                onUserSet: (v) => { buttonStyle = v }
                            }
                            ChoiceMenu {
                                current: buttonSize
                                choices: [
                                    { "label": "Small", "value": "small" },
                                    { "label": "Medium", "value": "medium" },
                                    { "label": "Large", "value": "large" }
                                ]
                                onUserSet: (v) => { buttonSize = v }
                            }
                            RowLayout {
                                Label { text: "Columns"; color: "#E4E4E7" }
                                TrackSpin { from: 1; to: 16; source: buttonColumns; onUserSet: (v) => { buttonColumns = v } }
                                Label { text: "Width"; color: "#E4E4E7" }
                                TrackSpin { from: 40; to: 200; source: buttonWidth; onUserSet: (v) => { buttonWidth = v } }
                            }
                        }

                        FoldSection {
                            title: "Colors"
                            open: openColors
                            onToggled: (v) => { openColors = v }
                        RowLayout {
                            Label { text: "Live"; color: "#E4E4E7"; Layout.preferredWidth: 70 }
                            Button {
                                Layout.fillWidth: true
                                text: "Choose…"
                                onClicked: { _colorTarget = "live"; _colorDlg.selectedColor = colorLive; _colorDlg.open() }
                                background: Rectangle {
                                    color: colorLive
                                    border.color: "#3F3F46"
                                    border.width: 1
                                    radius: 3
                                }
                                contentItem: Label {
                                    text: parent.text
                                    color: "#111111"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                        RowLayout {
                            Label { text: "Meter"; color: "#E4E4E7"; Layout.preferredWidth: 70 }
                            Button {
                                Layout.fillWidth: true
                                text: "Choose…"
                                onClicked: { _colorTarget = "meter"; _colorDlg.selectedColor = colorMeter; _colorDlg.open() }
                                background: Rectangle {
                                    color: colorMeter
                                    border.color: "#3F3F46"
                                    border.width: 1
                                    radius: 3
                                }
                                contentItem: Label {
                                    text: parent.text
                                    color: "#111111"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                        RowLayout {
                            Label { text: "Press"; color: "#E4E4E7"; Layout.preferredWidth: 70 }
                            Button {
                                Layout.fillWidth: true
                                text: "Choose…"
                                onClicked: { _colorTarget = "press"; _colorDlg.selectedColor = colorPress; _colorDlg.open() }
                                background: Rectangle {
                                    color: colorPress
                                    border.color: "#3F3F46"
                                    border.width: 1
                                    radius: 3
                                }
                                contentItem: Label {
                                    text: parent.text
                                    color: "#111111"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                        }
                    }
                }

                RowLayout {
                    spacing: 6
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Reset View\nto Default"
                        onClicked: resetView()
                        contentItem: Text {
                            text: parent.text
                            color: "#FFFFFF"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            implicitHeight: 44
                            color: parent.down ? "#991B1B" : (parent.hovered ? "#EF4444" : "#DC2626")
                            border.width: 1
                            border.color: parent.hovered ? "#FCA5A5" : "#B91C1C"
                        }
                    }
                    Button {
                        id: _copyButton
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Copy View\nfrom…"
                        onClicked: {
                            refreshCopySources()
                            _copyMenu.popup(_copyButton, 0, _copyButton.height)
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#F4F4F5"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Save View\nSettings"
                        highlighted: true
                        onClicked: saveView()
                        contentItem: Text {
                            text: parent.text
                            color: "#FFFFFF"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
    }

    Menu {
        id: _copyMenu
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        width: 360
        Instantiator {
            model: _copySources
            delegate: MenuItem {
                required property string label
                required property string name
                required property string guid
                text: label
                width: 360
                onTriggered: _root.copyViewFrom(name, guid)
            }
            onObjectAdded: (index, object) => _copyMenu.insertItem(_copyMenu.count, object)
            onObjectRemoved: (index, object) => _copyMenu.removeItem(object)
        }
    }

    DismissibleDialog {
        id: _saveGate
        onSaveChosen: {
            saveView()
            if (hasUnsaved())
                return
            if (_leaveOnly) {
                _leaveOnly = false
                leaveResolved()
                return
            }
            closePanel()
        }
        onDiscardChosen: {
            loadView()
            if (_leaveOnly) {
                _leaveOnly = false
                leaveResolved()
                return
            }
            closePanel()
        }
        onCancelled: {
            if (_leaveOnly) {
                _leaveOnly = false
                leaveCancelled()
            }
        }
    }

    Popup {
        id: _savedToast
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        dim: true
        Overlay.modal: Rectangle { color: "#66000000" }
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        padding: 18
        background: Rectangle {
            color: "#27272A"
            border.color: "#52525B"
            radius: 6
        }
        contentItem: Label {
            text: toastText
            color: "#F4F4F5"
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
        }
        Timer {
            id: _savedTimer
            interval: 2000
            onTriggered: _savedToast.close()
        }
        onOpened: _savedTimer.restart()
        onClosed: _savedTimer.stop()
    }
}

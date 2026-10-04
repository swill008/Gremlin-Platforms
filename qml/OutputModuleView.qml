// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only
// View-only dest monitor: feeder live, no wiring.

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Dialogs

import Gremlin.Device
import Gremlin.Menus
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
    // Display colours: colorXSet is the user's choice ("" when never changed);
    // colorX is shown and follows Dark mode until a choice is made.
    property string colorLiveSet: ""
    property string colorMeterSet: ""
    property string colorPressSet: ""
    readonly property color colorLive: colorLiveSet.length ? colorLiveSet : Style.ok
    readonly property color colorMeter: colorMeterSet.length ? colorMeterSet : Style.info
    readonly property color colorPress: colorPressSet.length ? colorPressSet : Style.ok
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
        spacing: Style.dp(4)

        Rectangle {
            Layout.fillWidth: true
            height: Style.dp(26)
            color: Style.bgRaised
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.dp(8)
                anchors.rightMargin: Style.dp(8)
                spacing: Style.dp(6)
                Label {
                    text: fold.open ? "\u25BC" : "\u25B6"
                    color: Style.fg
                    font.pixelSize: Style.dp(10)
                }
                Label {
                    text: fold.title
                    color: Style.fg
                    font.pixelSize: Style.dp(11)
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
            spacing: Style.dp(4)
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
    readonly property int btnCellW: buttonSize === "small" ? Style.dp(52) : (buttonSize === "large" ? Style.dp(88) : Style.dp(64))
    readonly property int btnCellH: buttonSize === "small" ? Style.dp(48) : (buttonSize === "large" ? Style.dp(68) : Style.dp(56))

    ModuleClaimedInputModel {
        id: _claimed
        guid: _root.guid
        deviceName: _root.deviceName
        onCountChanged: _root.rebuild()
    }

    ColorDialog {
        id: _colorDlg
        title: "Choose Color"
        onAccepted: {
            var c = selectedColor.toString()
            if (_colorTarget === "meter")
                colorMeterSet = c
            else if (_colorTarget === "press")
                colorPressSet = c
            else if (_colorTarget === "screen")
                colorScreen = c
            else
                colorLiveSet = c
        }
    }

    FileDialog {
        id: _screenImageDlg
        title: "Screen Background"
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
            "colorLive": colorLiveSet,
            "colorMeter": colorMeterSet,
            "colorPress": colorPressSet,
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

    // A saved colour equal to the old fixed (dark) default was never changed by
    // the user, so it follows Dark mode like a colour that was never set.
    function userColour(saved, oldDefault) {
        var text = String(saved || "")
        return text.toLowerCase() === oldDefault.toLowerCase() ? "" : text
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
        colorLiveSet = userColour(v.colorLive, "#22C55E")
        colorMeterSet = userColour(v.colorMeter, "#3B82F6")
        colorPressSet = userColour(v.colorPress, "#22C55E")
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
            if (backend)
                backend.noteSave("Saved the Appearance to " + moduleModel.lastSavedPath())
        } else {
            _saveGate.announce(false, "Not written. It is still only on this screen.")
            if (backend)
                backend.noteSave("The Appearance was not written.")
        }
    }

    function requestLeave() {
        if (!hasUnsaved()) {
            leaveResolved()
            return
        }
        _leaveOnly = true
        _saveGate.detail = leaveMessage.length
            ? leaveMessage
            : "Appearance changes are not saved. Leave this device and they will be lost."
        _saveGate.ask()
    }

    property bool _leaveOnly: false
    // Set by Main while quitting, so the prompt does not talk about leaving a device.
    property string leaveMessage: ""
    signal leaveResolved()
    signal leaveCancelled()

    function requestClose() {
        _leaveOnly = false
        if (hasUnsaved()) {
            _saveGate.detail = "Appearance changes are not saved. Close this panel and they will be lost."
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
        colorLiveSet = ""
        colorMeterSet = ""
        colorPressSet = ""
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

    function reloadView() {
        loadView()
        rebuild()
    }

    Component.onCompleted: reloadView()
    onGuidChanged: reloadView()
    onDeviceNameChanged: reloadView()

    component CrossPad: Rectangle {
        id: pad
        property real xVal: 0
        property real yVal: 0
        property string label: ""
        color: Style.background
        border.color: Style.lowColor
        border.width: Style.dp(1)
        implicitWidth: Style.dp(220)
        implicitHeight: Style.dp(220)

        Rectangle {
            width: parent.width - Style.dp(24)
            height: Style.dp(1)
            color: Style.lowColor
            anchors.centerIn: parent
        }
        Rectangle {
            width: Style.dp(1)
            height: parent.height - Style.dp(24)
            color: Style.lowColor
            anchors.centerIn: parent
        }
        Rectangle {
            width: Style.dp(12)
            height: Style.dp(12)
            radius: Style.dp(6)
            color: _root.colorLive
            visible: _root.showLive
            x: parent.width / 2 + (pad.xVal * (parent.width / 2 - Style.dp(16))) - width / 2
            y: parent.height / 2 - (pad.yVal * (parent.height / 2 - Style.dp(16))) - height / 2
        }
        Label {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: Style.dp(6)
            text: pad.label
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
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
        anchors.margins: Style.dp(12)
        spacing: Style.dp(16)

        // Scrolls sideways when the page is too narrow (a large UI scale), so
        // the Appearance panel beside it always stays in view.
        Flickable {
            id: _viewScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            flickableDirection: Flickable.HorizontalFlick
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentWidth > width
            contentWidth: Math.max(width, _viewRow.implicitWidth)
            contentHeight: height
            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

            RowLayout {
                id: _viewRow
                width: _viewScroll.contentWidth
                height: _viewScroll.height
                spacing: Style.dp(16)

                ColumnLayout {
                    visible: _root.padAOn || _root.padBOn || (_root.showHats && hatModel.count > 0)
                    Layout.preferredWidth: Style.dp(228)
                    Layout.maximumWidth: Style.dp(228)
                    Layout.fillWidth: false
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignTop
                    spacing: Style.dp(12)

                    CrossPad {
                        Layout.preferredWidth: Style.dp(220)
                        Layout.preferredHeight: Style.dp(220)
                        visible: _root.padAOn
                        label: "X / Y"
                        xVal: { var row = findAxis(padAX); return row ? liveVal(row.idx) : 0 }
                        yVal: { var row = findAxis(padAY); return row ? liveVal(row.idx) : 0 }
                    }
                    CrossPad {
                        Layout.preferredWidth: Style.dp(220)
                        Layout.preferredHeight: Style.dp(220)
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
                            Layout.preferredWidth: Style.dp(160)
                            Layout.preferredHeight: Style.dp(160)
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
                    spacing: Style.dp(10)

                    Repeater {
                        model: axisModel
                        delegate: Column {
                            required property int idx
                            required property int hw
                            required property string name
                            visible: meterOn(hw)
                            width: Style.dp(Math.max(48, _root.meterWidth + 26))
                            height: parent.height
                            spacing: Style.dp(6)

                            BetterProgressBar {
                                width: Style.dp(_root.meterWidth)
                                height: parent.height - Style.dp(44)
                                anchors.horizontalCenter: parent.horizontalCenter
                                orientation: _root.meterStyle === "horizontal" ? BetterProgressBar.Orientation.Horizontal : BetterProgressBar.Orientation.Vertical
                                barSize: Style.dp(_root.meterWidth)
                                fillColor: _root.colorMeter
                                from: -1
                                to: 1
                                value: liveVal(idx)
                            }
                            Label {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: axisShort(hw, name)
                                color: Style.fg
                                font.pixelSize: Style.dp(12)
                            }
                            Label {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: (liveVal(idx) >= 0 ? "+" : "") + liveVal(idx).toFixed(2)
                                color: Style.fgMuted
                                font.pixelSize: Style.dp(10)
                            }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: Style.dp(200)
                    Layout.preferredWidth: Style.dp(200)
                    clip: true

                    Flickable {
                        id: _buttons
                        anchors.fill: parent
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        // Columns wrap to fit, so nothing sits off to the side.
                        flickableDirection: Flickable.VerticalFlick
                        contentWidth: Math.max(width, _btnGrid.implicitWidth)
                        contentHeight: Math.max(height, _btnGrid.implicitHeight)
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        GridLayout {
                            id: _btnGrid
                            // The Columns setting is a maximum: use fewer when the view is narrower.
                            readonly property real cellW: Style.dp(Math.max(40, _root.buttonWidth))
                            columns: Math.max(1, Math.min(_root.buttonColumns,
                                Math.floor((_buttons.width + columnSpacing) / (cellW + columnSpacing))))
                            columnSpacing: Style.dp(6)
                            rowSpacing: Style.dp(6)

                            Repeater {
                                model: buttonModel
                                delegate: Rectangle {
                            required property int idx
                            required property int hw
                            required property string name
                            Layout.preferredWidth: Style.dp(Math.max(40, _root.buttonWidth))
                            Layout.preferredHeight: _root.btnCellH
                            Layout.minimumWidth: Style.dp(Math.max(40, _root.buttonWidth))
                            Layout.maximumWidth: Style.dp(Math.max(40, _root.buttonWidth))
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
                            border.width: Style.dp(1)
                            radius: Style.dp(3)

                            Row {
                                anchors.centerIn: parent
                                spacing: Style.dp(6)
                                Rectangle {
                                    visible: _root.buttonStyle === "led"
                                    width: Style.dp(10)
                                    height: Style.dp(10)
                                    radius: Style.dp(5)
                                    color: on ? _root.colorPress : Style.lowColor
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Column {
                                    spacing: 0
                                    Label {
                                        text: "Button"
                                        color: on ? Style.fgStrong : Style.fgMuted
                                        font.pixelSize: _root.buttonSize === "small" ? Style.dp(9) : Style.dp(11)
                                        horizontalAlignment: Text.AlignHCenter
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Label {
                                        text: "" + hw
                                        color: on ? Style.fgStrong : Style.fg
                                        font.pixelSize: _root.buttonSize === "small" ? Style.dp(12) : Style.dp(14)
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
            }
        }

        Rectangle {
            visible: _root.showPanel
            Layout.preferredWidth: Style.dp(360)
            Layout.maximumWidth: Style.dp(360)
            Layout.fillHeight: true
            color: Style.bgCard
            border.color: Style.line
            border.width: Style.dp(1)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Style.dp(10)
                spacing: Style.dp(8)

                RowLayout {
                    Label {
                        text: "Output View — Appearance"
                        color: Style.fg
                        font.bold: true
                        font.pixelSize: Style.dp(13)
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "×"
                        implicitWidth: Style.dp(28)
                        onClicked: _root.requestClose()
                    }
                }
                RowLayout {
                    spacing: Style.dp(8)
                    Button { text: "Open All"; onClicked: setAllSections(true) }
                    Button { text: "Close All"; onClicked: setAllSections(false) }
                    Item { Layout.fillWidth: true }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ColumnLayout {
                        width: Style.dp(330)
                        spacing: Style.dp(12)

                        FoldSection {
                            title: "Screen"
                            open: openScreen
                            onToggled: (v) => { openScreen = v }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Color"; color: Style.fg; Layout.preferredWidth: Style.dp(110) }
                                Button {
                                    Layout.fillWidth: true
                                    text: colorScreen === "#00000000" ? "None" : "Choose…"
                                    onClicked: {
                                        _colorTarget = "screen"
                                        _colorDlg.selectedColor = colorScreen === "#00000000" ? Style.bgPage : colorScreen
                                        _colorDlg.open()
                                    }
                                    background: Rectangle {
                                        color: colorScreen === "#00000000" ? Style.bgRaised : colorScreen
                                        border.color: Style.line
                                        border.width: Style.dp(1)
                                        radius: Style.dp(3)
                                    }
                                    contentItem: Label {
                                        text: parent.text
                                        color: Style.fgStrong
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
                                Label { text: "Image"; color: Style.fg; Layout.preferredWidth: Style.dp(110) }
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
                                color: Style.fgMuted
                                font.pixelSize: Style.dp(11)
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
                                color: Style.fgDisabled
                                font.pixelSize: Style.dp(11)
                            }
                            ColumnLayout {
                                visible: showPads
                                spacing: Style.dp(4)
                                Layout.fillWidth: true
                                Label { text: "X / Y pad"; color: Style.fg; font.pixelSize: Style.dp(11) }
                                RowLayout {
                                    Label { text: "Horizontal"; color: Style.fgMuted; Layout.preferredWidth: Style.dp(80) }
                                    AxisMenu { hw: padAX; onUserSet: (v) => { padAX = v } }
                                }
                                RowLayout {
                                    Label { text: "Vertical"; color: Style.fgMuted; Layout.preferredWidth: Style.dp(80) }
                                    AxisMenu { hw: padAY; onUserSet: (v) => { padAY = v } }
                                }
                                Label { text: "Rx / Ry pad"; color: Style.fg; font.pixelSize: Style.dp(11) }
                                RowLayout {
                                    Label { text: "Horizontal"; color: Style.fgMuted; Layout.preferredWidth: Style.dp(80) }
                                    AxisMenu { hw: padBX; onUserSet: (v) => { padBX = v } }
                                }
                                RowLayout {
                                    Label { text: "Vertical"; color: Style.fgMuted; Layout.preferredWidth: Style.dp(80) }
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
                                Label { text: "Width"; color: Style.fg }
                                TrackSpin { from: 12; to: 48; source: meterWidth; onUserSet: (v) => { meterWidth = v } }
                            }
                            Label {
                                text: "Axes on bars"
                                color: Style.fg
                                font.pixelSize: Style.dp(11)
                            }
                            Label {
                                text: "Uncheck an axis to hide its bar."
                                color: Style.fgMuted
                                font.pixelSize: Style.dp(11)
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                            GridLayout {
                                enabled: showMeters
                                columns: 2
                                Layout.fillWidth: true
                                columnSpacing: Style.dp(8)
                                rowSpacing: 0
                                Repeater {
                                    model: axisModel
                                    delegate: FlagBox {
                                        required property int hw
                                        required property string name
                                        Layout.preferredWidth: Style.dp(155)
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
                                Label {
                                    text: "Columns"
                                    color: Style.fg
                                    PointerTip { text: "Maximum columns; fewer are used when the view is narrower." }
                                }
                                TrackSpin { from: 1; to: 16; source: buttonColumns; onUserSet: (v) => { buttonColumns = v } }
                                Label { text: "Width"; color: Style.fg }
                                TrackSpin { from: 40; to: 200; source: buttonWidth; onUserSet: (v) => { buttonWidth = v } }
                            }
                        }

                        FoldSection {
                            title: "Colors"
                            open: openColors
                            onToggled: (v) => { openColors = v }
                        RowLayout {
                            Label { text: "Live"; color: Style.fg; Layout.preferredWidth: Style.dp(70) }
                            Button {
                                Layout.fillWidth: true
                                text: "Choose…"
                                onClicked: { _colorTarget = "live"; _colorDlg.selectedColor = colorLive; _colorDlg.open() }
                                background: Rectangle {
                                    color: colorLive
                                    border.color: Style.line
                                    border.width: Style.dp(1)
                                    radius: Style.dp(3)
                                }
                                // Dark text on a light swatch, white on a dark one.
                                contentItem: Label {
                                    text: parent.text
                                    color: colorLive.hslLightness > 0.6 ? Style.onLight : Style.onColor
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            // Back to the colour that follows Dark mode.
                            Button {
                                text: "Default"
                                enabled: colorLiveSet.length > 0
                                onClicked: colorLiveSet = ""
                            }
                        }
                        RowLayout {
                            Label { text: "Meter"; color: Style.fg; Layout.preferredWidth: Style.dp(70) }
                            Button {
                                Layout.fillWidth: true
                                text: "Choose…"
                                onClicked: { _colorTarget = "meter"; _colorDlg.selectedColor = colorMeter; _colorDlg.open() }
                                background: Rectangle {
                                    color: colorMeter
                                    border.color: Style.line
                                    border.width: Style.dp(1)
                                    radius: Style.dp(3)
                                }
                                // Dark text on a light swatch, white on a dark one.
                                contentItem: Label {
                                    text: parent.text
                                    color: colorMeter.hslLightness > 0.6 ? Style.onLight : Style.onColor
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            // Back to the colour that follows Dark mode.
                            Button {
                                text: "Default"
                                enabled: colorMeterSet.length > 0
                                onClicked: colorMeterSet = ""
                            }
                        }
                        RowLayout {
                            Label { text: "Press"; color: Style.fg; Layout.preferredWidth: Style.dp(70) }
                            Button {
                                Layout.fillWidth: true
                                text: "Choose…"
                                onClicked: { _colorTarget = "press"; _colorDlg.selectedColor = colorPress; _colorDlg.open() }
                                background: Rectangle {
                                    color: colorPress
                                    border.color: Style.line
                                    border.width: Style.dp(1)
                                    radius: Style.dp(3)
                                }
                                // Dark text on a light swatch, white on a dark one.
                                contentItem: Label {
                                    text: parent.text
                                    color: colorPress.hslLightness > 0.6 ? Style.onLight : Style.onColor
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            // Back to the colour that follows Dark mode.
                            Button {
                                text: "Default"
                                enabled: colorPressSet.length > 0
                                onClicked: colorPressSet = ""
                            }
                        }
                        }
                    }
                }

                RowLayout {
                    spacing: Style.dp(6)
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(44)
                        text: "Reset\nAppearance"
                        onClicked: resetView()
                        contentItem: Text {
                            text: parent.text
                            color: Style.onColor
                            font.pixelSize: Style.dp(12)
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            implicitHeight: Style.dp(44)
                            color: parent.down ? Style.dangerPressed : (parent.hovered ? Style.dangerBright : Style.danger)
                            border.width: Style.dp(1)
                            border.color: parent.hovered ? Style.dangerTextSoft : Style.dangerHover
                        }
                    }
                    Button {
                        id: _copyButton
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(44)
                        text: "Copy Appearance\nfrom…"
                        onClicked: {
                            refreshCopySources()
                            _copyMenu.openBelow(_copyButton)
                        }
                        contentItem: Text {
                            text: parent.text
                            color: Style.fgStrong
                            font.pixelSize: Style.dp(12)
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Style.dp(44)
                        text: "Save\nAppearance"
                        highlighted: true
                        onClicked: saveView()
                        contentItem: Text {
                            text: parent.text
                            color: Style.onColor
                            font.pixelSize: Style.dp(12)
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
    }

    // Copy the display settings from another module (Gremlin.Menus).
    ContextMenu {
        id: _copyMenu
        menuWidth: Style.dp(360)
        build: function() {
            var rows = []
            for (var i = 0; i < _copySources.count; ++i) {
                (function(src) {
                    rows.push(MenuModel.action(src.label, function() { _root.copyViewFrom(src.name, src.guid) }))
                })(_copySources.get(i))
            }
            return MenuModel.menu("copy-view", rows.length ? "Replace this view with the settings from" : "No other output module", rows, [])
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
        Overlay.modal: Rectangle { color: Style.dim }
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        padding: Style.dp(18)
        background: Rectangle {
            color: Style.bgRaised
            border.color: Style.lineStrong
            radius: Style.dp(6)
        }
        contentItem: Label {
            text: toastText
            color: Style.fgStrong
            font.pixelSize: Style.dp(14)
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

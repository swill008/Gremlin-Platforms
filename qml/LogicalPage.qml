// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.UI

Item {
    id: _root

    property string mode: "Default"
    property bool editorOpen: false
    property string dock: "float"
    property int editorWidth: 420
    property int paneWidth: 560
    property bool actionOpen: false
    property string paneKey: ""
    property string paneTitle: ""
    property bool closeAfterOk: false
    property int parentHeight: 44
    property int childHeight: 32
    property bool showPanel: false
    property bool _ready: false
    property var _opened: ({})
    property var _collapsed: ({})
    property var _picked: ([])

    readonly property bool editorLocked: backend && backend.gremlinActive

    signal leaveResolved()
    signal leaveCancelled()

    function setMode(next) {
        mode = next || "Default"
        _layout.setMode(mode)
    }

    function hasUnsaved() { return false }
    function requestLeave() { leaveResolved() }

    function _saveDock() {
        if (!_ready)
            return
        _place.setLogicalDock(dock)
        _place.setLogicalOpen(editorOpen)
        _place.setLogicalWidth(editorWidth)
        _place.setLogicalValue("parentHeight", String(parentHeight))
        _place.setActionPaneWidth(paneWidth)
        _place.setClosePaneAfterOk(closeAfterOk)
    }

    function _toggleOpen(key) {
        var next = Object.assign({}, _opened)
        next[key] = !next[key]
        _opened = next
    }

    function _toggleGroup(key) {
        var next = Object.assign({}, _collapsed)
        next[key] = !next[key]
        _collapsed = next
    }

    function _rowVisible(kind, groupKey, parentKey) {
        if (kind !== "group" && _collapsed[groupKey])
            return false
        if (kind === "writer" || kind === "child")
            return !!_opened[parentKey]
        return true
    }

    function _select(key, shift) {
        var next = _picked.slice()
        if (!shift) {
            next = [key]
        } else {
            var at = next.indexOf(key)
            if (at < 0)
                next.push(key)
            else
                next.splice(at, 1)
        }
        _picked = next
        _layout.setSelection(next)
    }

    function _openPane(key, seq, title) {
        if (editorLocked)
            return
        _layout.beginPane(key, seq)
        paneKey = key
        paneTitle = title
        actionOpen = true
    }

    function _closePane() {
        if (_layout.paneDirty()) {
            _leave.ask("The action editor has changes that are not saved.")
            return
        }
        _finishClose()
    }

    function _finishClose() {
        _layout.endPane()
        actionOpen = false
        paneKey = ""
    }

    LogicalLayoutModel { id: _layout }
    WindowPlacement { id: _place }

    Component.onCompleted: {
        dock = _place.logicalDock()
        editorOpen = _place.logicalOpen()
        editorWidth = _place.logicalWidth()
        paneWidth = _place.actionPaneWidth()
        closeAfterOk = _place.closePaneAfterOk()
        var h = parseInt(_place.logicalValue("parentHeight"))
        if (!isNaN(h) && h >= 32)
            parentHeight = h
        _layout.setMode(mode)
        _ready = true
        _placeForm()
    }

    onDockChanged: _saveDock()
    onEditorOpenChanged: _saveDock()
    onEditorWidthChanged: _saveDock()
    onPaneWidthChanged: _saveDock()
    onCloseAfterOkChanged: _saveDock()
    onParentHeightChanged: _saveDock()
    onModeChanged: _layout.setMode(mode)

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            id: _leftHost
            visible: _root.editorOpen && _root.dock === "left"
            Layout.preferredWidth: visible ? _root.editorWidth : 0
            Layout.minimumWidth: visible ? 280 : 0
            Layout.fillHeight: true
        }
        Rectangle {
            visible: _leftHost.visible
            Layout.preferredWidth: 6
            Layout.fillHeight: true
            color: _leftGrip.containsMouse ? "#3B82F6" : "#3F3F46"
            MouseArea {
                id: _leftGrip
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SplitHCursor
                property int originW: 420
                property real originX: 0
                onPressed: (mouse) => {
                    originW = _root.editorWidth
                    originX = mapToItem(_root, mouse.x, mouse.y).x
                }
                onPositionChanged: (mouse) => {
                    if (!pressed)
                        return
                    var x = mapToItem(_root, mouse.x, mouse.y).x
                    _root.editorWidth = Math.max(280, Math.min(900, originW + (x - originX)))
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 360
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                Layout.margins: 8
                Button {
                    text: _root.editorOpen ? "Hide Organize" : "Organize"
                    onClicked: _root.editorOpen = !_root.editorOpen
                }
                Button {
                    text: _root.showPanel ? "Hide Editor" : "Show Editor"
                    onClicked: _root.showPanel = !_root.showPanel
                }
                ComboBox {
                    id: _dockBox
                    model: ["Float", "Left", "Right"]
                    currentIndex: _root.dock === "left" ? 1 : (_root.dock === "right" ? 2 : 0)
                    onActivated: {
                        var sides = ["float", "left", "right"]
                        _root.dock = sides[currentIndex]
                    }
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: _root.editorLocked ? "Running" : ""
                    color: "#A1A1AA"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    visible: _root.showPanel
                    Layout.preferredWidth: visible ? 240 : 0
                    Layout.fillHeight: true
                    color: "#18181B"
                    border.color: "#3F3F46"
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        Label { text: "Display Editor"; color: "#E4E4E7"; font.bold: true }
                        Label { text: "Saved for this page only."; color: "#A1A1AA"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        RowLayout {
                            Label { text: "Row height"; color: "#E4E4E7"; Layout.fillWidth: true }
                            SpinBox { from: 32; to: 80; value: _root.parentHeight; onValueModified: _root.parentHeight = value }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }

                ListView {
                    id: _list
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: _layout
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

                    MouseArea {
                        z: -1
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked: _pageMenu.popup()
                    }

                    delegate: Rectangle {
                        id: _row
                        required property int index
                        required property string rowKind
                        required property string key
                        required property string title
                        required property string subtitle
                        required property string parentKey
                        required property string groupKey
                        required property string groupName
                        required property string systemName
                        required property string userName
                        required property string writerId
                        required property string axisMode
                        required property double axisScale
                        required property bool inverted
                        required property int sequenceIndex
                        required property int indent

                        readonly property bool shown: _root._rowVisible(rowKind, groupKey, parentKey)
                        width: _list.width - 16
                        height: shown ? implicitHeight : 0
                        visible: shown
                        clip: true
                        implicitHeight: rowKind === "group" ? 40 : (rowKind === "parent" ? _root.parentHeight : _root.childHeight)
                        color: _root._picked.indexOf(key) >= 0 ? "#1E3A5F" : (rowKind === "group" ? "#27272A" : "#18181B")
                        border.color: "#3F3F46"
                        border.width: 1
                        radius: 3

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: (indent > 0 && rowKind === "parent" ? 24 : (indent > 0 ? 40 : 8))
                            anchors.rightMargin: 8
                            spacing: 6

                            Label {
                                visible: rowKind === "group" || rowKind === "parent"
                                text: (rowKind === "group" ? _root._collapsed[groupKey] : !_root._opened[key]) ? "▸" : "▾"
                                color: "#E4E4E7"
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        if (rowKind === "group")
                                            _root._toggleGroup(groupKey)
                                        else
                                            _root._toggleOpen(key)
                                    }
                                }
                            }
                            Rectangle {
                                visible: rowKind === "parent" || rowKind === "group"
                                width: 8
                                height: 18
                                radius: 2
                                color: "#52525B"
                                z: 2
                                MouseArea {
                                    anchors.fill: parent
                                    anchors.margins: -6
                                    cursorShape: Qt.SizeAllCursor
                                    preventStealing: true
                                    onPressed: _root._dragFrom = key
                                    onReleased: (mouse) => {
                                        var pos = mapToItem(_list, mouse.x, mouse.y)
                                        var hit = _list.indexAt(pos.x, pos.y + _list.contentY)
                                        if (hit >= 0)
                                            _layout.moveRow(_root._dragFrom, _layout.keyAt(hit))
                                        _root._dragFrom = ""
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Label {
                                    text: title
                                    color: "#E4E4E7"
                                    font.bold: rowKind !== "child"
                                    font.pixelSize: rowKind === "group" ? 15 : 13
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Label {
                                    visible: subtitle.length > 0 && rowKind !== "writer"
                                    text: subtitle
                                    color: "#A1A1AA"
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }
                            ComboBox {
                                visible: rowKind === "writer" && axisMode.length > 0
                                model: ["absolute", "relative"]
                                currentIndex: axisMode === "relative" ? 1 : 0
                                Layout.preferredWidth: 110
                                onActivated: _layout.setAxisMode(writerId, currentText)
                            }
                            SpinBox {
                                visible: rowKind === "writer" && axisMode.length > 0
                                from: -500
                                to: 500
                                stepSize: 10
                                value: Math.round(axisScale * 100)
                                editable: true
                                Layout.preferredWidth: 90
                                onValueModified: _layout.setAxisScale(writerId, value / 100.0)
                            }
                            CheckBox {
                                visible: rowKind === "writer" && systemName.indexOf("Button") === 0
                                text: "Invert"
                                checked: inverted
                                onClicked: _layout.setInverted(writerId, checked)
                            }
                        }

                        MouseArea {
                            z: 1
                            anchors.fill: parent
                            anchors.leftMargin: 52
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            propagateComposedEvents: true
                            onClicked: (mouse) => {
                                if (mouse.button === Qt.RightButton) {
                                    if (rowKind === "group" && groupName.length > 0) {
                                        _groupName = groupName
                                        _groupMenu.popup()
                                    } else if (rowKind === "parent") {
                                        _menuKey = key
                                        _menuTitle = title
                                        _parentMenu.popup()
                                    } else if (rowKind === "group") {
                                        _pageMenu.popup()
                                    }
                                    return
                                }
                                if (rowKind === "parent")
                                    _root._select(key, mouse.modifiers & Qt.ShiftModifier)
                                else if (rowKind === "child")
                                    _root._openPane(parentKey, sequenceIndex, title)
                                else if (rowKind === "group")
                                    _root._toggleGroup(groupKey)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: _root.actionOpen
            Layout.preferredWidth: 6
            Layout.fillHeight: true
            color: _actGrip.containsMouse ? "#3B82F6" : "#3F3F46"
            MouseArea {
                id: _actGrip
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SplitHCursor
                property int originW: 560
                property real originX: 0
                onPressed: (mouse) => {
                    originW = _root.paneWidth
                    originX = mapToItem(_root, mouse.x, mouse.y).x
                }
                onPositionChanged: (mouse) => {
                    if (!pressed)
                        return
                    var x = mapToItem(_root, mouse.x, mouse.y).x
                    _root.paneWidth = Math.max(420, Math.min(1600, originW - (x - originX)))
                }
            }
        }

        Rectangle {
            visible: _root.actionOpen
            Layout.preferredWidth: _root.paneWidth
            Layout.minimumWidth: visible ? 420 : 0
            Layout.fillHeight: true
            color: "#18181B"
            border.color: "#3F3F46"
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                RowLayout {
                    Label {
                        text: _root.paneTitle.length ? _root.paneTitle : "Action Editor"
                        color: "#E4E4E7"
                        font.bold: true
                        font.pixelSize: 16
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Button { text: "×"; implicitWidth: 28; onClicked: _root._closePane() }
                }
                InputConfiguration {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    holdModel: true
                    inputItemModel: _layout.paneModel
                }
                RowLayout {
                    CheckBox {
                        text: "Close pane after OK"
                        checked: _root.closeAfterOk
                        onClicked: _root.closeAfterOk = checked
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: "OK"
                        highlighted: true
                        onClicked: {
                            _layout.commitPane()
                            if (_root.closeAfterOk)
                                _root._finishClose()
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: _root.editorOpen && _root.dock === "right"
            Layout.preferredWidth: 6
            Layout.fillHeight: true
            color: _rightGrip.containsMouse ? "#3B82F6" : "#3F3F46"
            MouseArea {
                id: _rightGrip
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.SplitHCursor
                property int originW: 420
                property real originX: 0
                onPressed: (mouse) => {
                    originW = _root.editorWidth
                    originX = mapToItem(_root, mouse.x, mouse.y).x
                }
                onPositionChanged: (mouse) => {
                    if (!pressed)
                        return
                    var x = mapToItem(_root, mouse.x, mouse.y).x
                    _root.editorWidth = Math.max(280, Math.min(900, originW - (x - originX)))
                }
            }
        }

        Item {
            id: _rightHost
            visible: _root.editorOpen && _root.dock === "right"
            Layout.preferredWidth: visible ? _root.editorWidth : 0
            Layout.minimumWidth: visible ? 280 : 0
            Layout.fillHeight: true
        }
    }

    Item { id: _floatHost; visible: false }

    Window {
        id: _float
        width: 440
        height: 760
        title: "Logical layout"
        visible: _root.editorOpen && _root.dock === "float"
        Item { id: _floatBody; anchors.fill: parent }
        onClosing: (close) => {
            close.accepted = false
            _root.editorOpen = false
        }
    }

    LogicalLayoutForm {
        id: _form
        layout: _layout
        onCloseRequested: _root.editorOpen = false
    }

    property string _dragFrom: ""
    property string _menuKey: ""
    property string _menuTitle: ""
    property string _groupName: ""
    property string _hardwareKey: ""

    function _placeForm() {
        var host = _root.dock === "float" ? _floatBody : (_root.dock === "left" ? _leftHost : _rightHost)
        if (_form.parent !== host)
            _form.parent = host
        _form.anchors.fill = host
        _form.visible = _root.editorOpen
    }

    onDockChanged: _placeForm()
    onEditorOpenChanged: _placeForm()

    Menu {
        id: _pageMenu
        MenuItem { text: "Add Button"; enabled: !_root.editorLocked; onTriggered: _layout.addOne("button") }
        MenuItem { text: "Add Axis"; enabled: !_root.editorLocked; onTriggered: _layout.addOne("axis") }
        MenuItem { text: "Add Hat"; enabled: !_root.editorLocked; onTriggered: _layout.addOne("hat") }
    }
    Menu {
        id: _parentMenu
        MenuItem {
            text: "Add Action"
            enabled: !_root.editorLocked
            onTriggered: _root._openPane(_menuKey, -1, _menuTitle)
        }
        MenuItem {
            text: "Assign hardware"
            enabled: !_root.editorLocked
            onTriggered: {
                _hardwareKey = _menuKey
                _hardwareTitle.text = _menuTitle
                _search.text = ""
                _loadHardware()
                _hardware.open()
            }
        }
        MenuItem {
            text: "Rename"
            enabled: !_root.editorLocked
            onTriggered: {
                _nameField.text = ""
                _nameDialog.open()
            }
        }
        MenuItem {
            text: "Delete"
            enabled: !_root.editorLocked
            onTriggered: _layout.deleteParents([_menuKey])
        }
    }
    Menu {
        id: _groupMenu
        MenuItem {
            text: "Rename"
            enabled: !_root.editorLocked
            onTriggered: {
                _groupField.text = _groupName
                _groupDialog.open()
            }
        }
        MenuItem {
            text: "Delete group"
            enabled: !_root.editorLocked
            onTriggered: _layout.removeGroup(_groupName)
        }
    }

    Dialog {
        id: _nameDialog
        title: "Your name"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        TextField { id: _nameField; placeholderText: "Leave empty to use the system name"; width: 280 }
        onAccepted: _layout.setUserName(_menuKey, _nameField.text)
    }
    Dialog {
        id: _groupDialog
        title: "Rename group"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        TextField { id: _groupField; width: 280 }
        onAccepted: _layout.renameGroup(_groupName, _groupField.text)
    }

    Popup {
        id: _hardware
        parent: Overlay.overlay
        modal: true
        width: 520
        height: 640
        anchors.centerIn: parent
        padding: 12
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#18181B"; border.color: "#3F3F46" }
        property var devices: []
        ColumnLayout {
            anchors.fill: parent
            Label { id: _hardwareTitle; color: "#E4E4E7"; font.bold: true; font.pixelSize: 16 }
            TextField {
                id: _search
                Layout.fillWidth: true
                placeholderText: "Search"
                color: "#E4E4E7"
                onTextChanged: _loadHardware()
            }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: _hwCol.implicitHeight
                clip: true
                Column {
                    id: _hwCol
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: _hardware.devices
                        delegate: Column {
                            width: _hwCol.width
                            required property var modelData
                            spacing: 2
                            RowLayout {
                                width: parent.width
                                CheckBox {
                                    checkState: _deviceState(modelData.controls)
                                    tristate: true
                                    onClicked: {
                                        var on = 0
                                        var controls = modelData.controls
                                        for (var i = 0; i < controls.length; ++i)
                                            if (controls[i].on)
                                                on++
                                        _setDevice(controls, on !== controls.length)
                                    }
                                }
                                Label { text: modelData.name; color: "#E4E4E7"; font.bold: true; Layout.fillWidth: true }
                            }
                            Repeater {
                                model: modelData.controls
                                delegate: CheckBox {
                                    required property var modelData
                                    text: modelData.label
                                    checked: modelData.on
                                    leftPadding: 28
                                    onClicked: {
                                        _layout.setLinks(_hardwareKey, [modelData.key], checked)
                                        _loadHardware()
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Button { text: "Close"; onClicked: _hardware.close() }
        }
    }

    function _deviceState(controls) {
        var on = 0
        for (var i = 0; i < controls.length; ++i)
            if (controls[i].on)
                on++
        if (on === 0)
            return Qt.Unchecked
        if (on === controls.length)
            return Qt.Checked
        return Qt.PartiallyChecked
    }

    function _setDevice(controls, on) {
        var keys = []
        for (var i = 0; i < controls.length; ++i)
            keys.push(controls[i].key)
        _layout.setLinks(_hardwareKey, keys, on)
        _loadHardware()
    }

    function _loadHardware() {
        _hardware.devices = _layout.hardware(_hardwareKey, _search.text)
    }

    DismissibleDialog {
        id: _leave
        onSaveChosen: {
            _layout.commitPane()
            _finishClose()
        }
        onDiscardChosen: {
            _layout.discardPane()
            _finishClose()
        }
    }
}

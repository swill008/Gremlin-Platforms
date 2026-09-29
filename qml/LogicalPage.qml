// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

Item {
    id: _root

    property string mode: "Default"
    property int paneWidth: 560
    property bool actionOpen: false
    property string paneKey: ""
    property string paneTitle: ""
    property bool closeAfterOk: false
    property int parentHeight: 44
    property int childHeight: 32
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
        paneWidth = _place.actionPaneWidth()
        closeAfterOk = _place.closePaneAfterOk()
        var h = parseInt(_place.logicalValue("parentHeight"))
        if (!isNaN(h) && h >= 32)
            parentHeight = h
        _layout.setMode(mode)
        _ready = true
    }

    onPaneWidthChanged: _saveDock()
    onCloseAfterOkChanged: _saveDock()
    onParentHeightChanged: _saveDock()
    onModeChanged: _layout.setMode(mode)

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 360
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 8
                Layout.rightMargin: 8
                Layout.topMargin: 8
                spacing: 8
                Label { text: "Find"; color: "#A1A1AA" }
                TextField {
                    id: _findText
                    Layout.fillWidth: true
                    placeholderText: "System name, your name, or group"
                    color: "#E4E4E7"
                    onTextChanged: _root._applyFind()
                }
                ComboBox {
                    id: _findType
                    model: ["All types", "Buttons", "Axes", "Hats"]
                    onActivated: _root._applyFind()
                }
                CheckBox { id: _findUngrouped; text: "Ungrouped"; onClicked: _root._applyFind() }
                CheckBox { id: _findNoWriter; text: "No hardware writer"; onClicked: _root._applyFind() }
                CheckBox { id: _findNoAction; text: "No actions in this mode"; onClicked: _root._applyFind() }
                Button {
                    text: "Clear"
                    onClicked: {
                        _findText.text = ""
                        _findType.currentIndex = 0
                        _findUngrouped.checked = false
                        _findNoWriter.checked = false
                        _findNoAction.checked = false
                        _root._applyFind()
                    }
                }
                Label {
                    text: _root.editorLocked ? "Running" : ""
                    color: "#A1A1AA"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

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
                        onClicked: _root._openLayoutMenu(false, false)
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
                        required property bool canInvert

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
                            anchors.leftMargin: (indent > 0 && rowKind === "parent" ? 24 : (indent > 0 ? 56 : 8))
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
                                    id: _grip
                                    anchors.fill: parent
                                    anchors.margins: -6
                                    enabled: !_root.editorLocked
                                    cursorShape: rowKind === "parent" ? Qt.OpenHandCursor : Qt.SizeAllCursor
                                    preventStealing: true
                                    drag.target: rowKind === "parent" ? _payload : null
                                    drag.axis: Drag.XAndYAxis
                                    drag.threshold: 4
                                    onPressed: (mouse) => {
                                        if (rowKind !== "parent") {
                                            _root._dragFrom = key
                                            return
                                        }
                                        var pos = mapToItem(_row, mouse.x, mouse.y)
                                        _payload.x = pos.x
                                        _payload.y = pos.y
                                        _row.grabToImage(function(result) {
                                            _payload.Drag.imageSource = result.url
                                        })
                                    }
                                    onReleased: (mouse) => {
                                        if (rowKind === "parent")
                                            return
                                        var pos = mapToItem(_list.contentItem, mouse.x, mouse.y)
                                        var hit = _list.indexAt(pos.x, pos.y)
                                        if (hit >= 0)
                                            _layout.moveRow(_root._dragFrom, _layout.keyAt(hit))
                                        _root._dragFrom = ""
                                    }
                                }
                            }
                            Item {
                                visible: rowKind === "parent"
                                Layout.preferredWidth: visible ? 16 : 0
                                Layout.preferredHeight: 16
                                Layout.alignment: Qt.AlignVCenter

                                Rectangle {
                                    visible: key.indexOf(":button:") >= 0
                                    anchors.centerIn: parent
                                    width: 14
                                    height: 14
                                    radius: 7
                                    color: "transparent"
                                    border.color: "#E4E4E7"
                                    border.width: 2
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 6
                                        height: 6
                                        radius: 3
                                        color: "#E4E4E7"
                                    }
                                }
                                Item {
                                    visible: key.indexOf(":axis:") >= 0
                                    anchors.fill: parent
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 2
                                        height: 14
                                        color: "#E4E4E7"
                                    }
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 8
                                        height: 6
                                        radius: 2
                                        color: "#E4E4E7"
                                    }
                                }
                                Item {
                                    visible: key.indexOf(":hat:") >= 0
                                    anchors.fill: parent
                                    Rectangle { width: 4; height: 4; radius: 1; color: "#E4E4E7"; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top }
                                    Rectangle { width: 4; height: 4; radius: 1; color: "#E4E4E7"; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom }
                                    Rectangle { width: 4; height: 4; radius: 1; color: "#E4E4E7"; anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left }
                                    Rectangle { width: 4; height: 4; radius: 1; color: "#E4E4E7"; anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right }
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
                                    HoverHandler { id: _nameHover }
                                    ToolTip {
                                        visible: _nameHover.hovered && rowKind === "parent" && userName.length > 0
                                        delay: 400
                                        text: systemName
                                        x: _nameHover.point.position.x - width / 2
                                        y: _nameHover.point.position.y - height - 8
                                    }
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
                                visible: writerId.length > 0 && axisMode.length > 0
                                enabled: !_root.editorLocked
                                model: ["absolute", "relative"]
                                currentIndex: axisMode === "relative" ? 1 : 0
                                Layout.preferredWidth: 110
                                onActivated: _layout.setAxisMode(writerId, currentText)
                            }
                            SpinBox {
                                visible: writerId.length > 0 && axisMode.length > 0
                                enabled: !_root.editorLocked
                                from: -500
                                to: 500
                                stepSize: 10
                                value: Math.round(axisScale * 100)
                                editable: true
                                Layout.preferredWidth: 90
                                onValueModified: _layout.setAxisScale(writerId, value / 100.0)
                            }
                            CheckBox {
                                visible: writerId.length > 0 && canInvert
                                enabled: !_root.editorLocked
                                text: "Invert"
                                checked: inverted
                                onClicked: _layout.setInverted(writerId, checked)
                            }
                        }

                        DropArea {
                            id: _drop
                            anchors.fill: parent
                            z: 4
                            enabled: !_root.editorLocked && (rowKind === "parent" || rowKind === "group")
                            keys: ["application/x-gremlin-logical"]
                            property bool placeBefore: true
                            onPositionChanged: (drag) => {
                                var source = drag.getDataAsString("application/x-gremlin-logical")
                                if (!source || source === key || source.indexOf("parent:") !== 0) {
                                    _insertLine.visible = false
                                    return
                                }
                                if (rowKind === "group") {
                                    placeBefore = false
                                    _insertLine.y = Math.max(0, height - 2)
                                } else {
                                    placeBefore = drag.y < height / 2
                                    _insertLine.y = placeBefore ? 0 : Math.max(0, height - 2)
                                }
                                _insertLine.visible = true
                            }
                            onExited: _insertLine.visible = false
                            onDropped: (drop) => {
                                _insertLine.visible = false
                                var source = drop.getDataAsString("application/x-gremlin-logical")
                                if (!source || source === key)
                                    return
                                if (rowKind === "group")
                                    _layout.moveParent(source, key, "into")
                                else
                                    _layout.moveParent(source, key, placeBefore ? "before" : "after")
                                drop.accept(Qt.MoveAction)
                            }
                            Rectangle {
                                id: _insertLine
                                visible: false
                                z: 6
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: 2
                                color: "#3B82F6"
                            }
                        }

                        Item {
                            id: _payload
                            width: 1
                            height: 1
                            Drag.active: _grip.drag.active && rowKind === "parent" && !_root.editorLocked
                            Drag.dragType: Drag.Automatic
                            Drag.supportedActions: Qt.MoveAction
                            Drag.proposedAction: Qt.MoveAction
                            Drag.hotSpot.x: 12
                            Drag.hotSpot.y: 12
                            Drag.mimeData: { "application/x-gremlin-logical": key }
                        }

                        MouseArea {
                            z: 1
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            propagateComposedEvents: true
                            onPressed: (mouse) => {
                                if (mouse.button === Qt.LeftButton && mouse.x < 52) {
                                    mouse.accepted = false
                                }
                            }
                            onClicked: (mouse) => {
                                if (mouse.button === Qt.RightButton) {
                                    if (rowKind === "parent") {
                                        _root._menuKey = key
                                        _root._menuTitle = title
                                        _root._menuUser = userName
                                        _root._menuGroup = groupName
                                        if (_root._picked.indexOf(key) < 0)
                                            _root._select(key, false)
                                        _root._openLayoutMenu(true, false)
                                    } else if (rowKind === "group" && groupName.length > 0) {
                                        _root._groupName = groupName
                                        _root._openLayoutMenu(false, true)
                                    } else {
                                        _root._openLayoutMenu(false, false)
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

    }


    property string _dragFrom: ""
    property string _menuKey: ""
    property string _menuTitle: ""
    property string _menuUser: ""
    property string _menuGroup: ""
    property string _pendingGroup: ""
    property string _groupName: ""
    property string _hardwareKey: ""
    property bool _menuOnRow: false
    property bool _menuOnGroup: false

    function _applyFind() {
        var types = ["all", "button", "axis", "hat"]
        _layout.setFilter(
            _findText.text,
            types[_findType.currentIndex],
            _findUngrouped.checked,
            _findNoWriter.checked,
            _findNoAction.checked
        )
    }

    function _openLayoutMenu(onRow, onGroup) {
        _menuOnRow = onRow
        _menuOnGroup = onGroup
        _pageMenu.popup()
    }

    function _groupAs(name) {
        if (_picked.length === 1 && _menuGroup.length > 0 && _menuGroup !== name) {
            _pendingGroup = name
            _moveWarn.confirm(
                "Already in a group",
                _menuTitle + " is already in " + _menuGroup + ". Move it to " + name + "?",
                "Move"
            )
            return
        }
        _layout.moveSelected(name)
    }

    component MenuCountRow: Item {
        id: row
        required property string label
        required property string kind
        property int count: 1
        property bool rowHover: false
        implicitWidth: 300
        implicitHeight: 34

        function parsed() {
            var n = parseInt(_field.text)
            if (isNaN(n))
                n = row.count
            return Math.max(1, Math.min(180, n))
        }

        function setCount(n) {
            count = n
            _field.text = String(n)
        }

        Rectangle {
            anchors.fill: parent
            color: !row.enabled ? "transparent" : (row.rowHover ? Universal.listLowColor : "transparent")
        }

        HoverHandler { onHoveredChanged: row.rowHover = hovered }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 4

            Label {
                text: row.label
                color: row.enabled ? Universal.baseHighColor : Universal.baseLowColor
                Layout.fillWidth: true
                verticalAlignment: Text.AlignVCenter
                MouseArea {
                    anchors.fill: parent
                    enabled: row.enabled
                    onClicked: _pageMenu.addCounted(row.kind, row)
                }
            }
            Label {
                text: "‹"
                color: row.enabled && row.parsed() > 1 ? Universal.baseHighColor : Universal.baseLowColor
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: row.enabled && row.parsed() > 1
                    onClicked: row.setCount(row.parsed() - 1)
                }
            }
            TextField {
                id: _field
                implicitWidth: 44
                padding: 0
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: row.enabled ? Universal.baseHighColor : Universal.baseLowColor
                enabled: row.enabled
                selectByMouse: true
                validator: IntValidator { bottom: 1; top: 180 }
                background: Item {}
                Component.onCompleted: text = "1"
                onAccepted: _pageMenu.addCounted(row.kind, row)
            }
            Label {
                text: "›"
                color: row.enabled && row.parsed() < 180 ? Universal.baseHighColor : Universal.baseLowColor
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: row.enabled && row.parsed() < 180
                    onClicked: row.setCount(row.parsed() + 1)
                }
            }
        }
    }

    component MenuNameRow: Item {
        id: nameRow
        required property string label
        property bool closeWhenNamed: false
        property bool rowHover: false
        signal named(string value)
        implicitWidth: 300
        implicitHeight: 34

        Rectangle {
            anchors.fill: parent
            color: !nameRow.enabled ? "transparent" : (nameRow.rowHover ? Universal.listLowColor : "transparent")
        }
        HoverHandler { onHoveredChanged: nameRow.rowHover = hovered }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8
            Label {
                text: nameRow.label
                color: nameRow.enabled ? Universal.baseHighColor : Universal.baseLowColor
            }
            TextField {
                Layout.fillWidth: true
                padding: 2
                placeholderText: "Name, then Enter"
                color: nameRow.enabled ? Universal.baseHighColor : Universal.baseLowColor
                enabled: nameRow.enabled
                selectByMouse: true
                background: Item {}
                onAccepted: {
                    var name = text.trim()
                    if (!name.length || !nameRow.enabled)
                        return
                    text = ""
                    nameRow.named(name)
                    if (nameRow.closeWhenNamed)
                        _pageMenu.close()
                }
            }
        }
    }

    component MenuHeightRow: Item {
        id: heightRow
        property bool rowHover: false
        implicitWidth: 300
        implicitHeight: 34

        function parsed() {
            var n = parseInt(_field.text)
            if (isNaN(n))
                n = _root.parentHeight
            return Math.max(32, Math.min(80, n))
        }

        function showHeight(n) {
            _field.text = String(n)
        }

        function applyHeight() {
            var n = parsed()
            _root.parentHeight = n
            showHeight(n)
        }

        Rectangle {
            anchors.fill: parent
            color: heightRow.rowHover ? Universal.listLowColor : "transparent"
        }
        HoverHandler { onHoveredChanged: heightRow.rowHover = hovered }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 4
            Label {
                text: "Row height"
                color: Universal.baseHighColor
                Layout.fillWidth: true
            }
            Label {
                text: "‹"
                color: heightRow.parsed() > 32 ? Universal.baseHighColor : Universal.baseLowColor
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: heightRow.parsed() > 32
                    onClicked: {
                        _root.parentHeight = heightRow.parsed() - 1
                        heightRow.showHeight(_root.parentHeight)
                    }
                }
            }
            TextField {
                id: _field
                implicitWidth: 44
                padding: 0
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: Universal.baseHighColor
                selectByMouse: true
                validator: IntValidator { bottom: 32; top: 80 }
                background: Item {}
                Component.onCompleted: text = String(_root.parentHeight)
                onAccepted: heightRow.applyHeight()
            }
            Label {
                text: "›"
                color: heightRow.parsed() < 80 ? Universal.baseHighColor : Universal.baseLowColor
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: heightRow.parsed() < 80
                    onClicked: {
                        _root.parentHeight = heightRow.parsed() + 1
                        heightRow.showHeight(_root.parentHeight)
                    }
                }
            }
        }
    }

    Menu {
        id: _pageMenu
        width: 300
        popupType: Popup.Item
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        function addCounted(kind, row) {
            if (_root.editorLocked || !row)
                return
            _layout.addMany(kind, row.parsed(), "", "")
            row.setCount(1)
        }

        function resetCounts() {
            _addButtonRow.setCount(1)
            _addAxisRow.setCount(1)
            _addHatRow.setCount(1)
        }

        onOpened: {
            resetCounts()
            _rowHeightRow.showHeight(_root.parentHeight)
        }

        MenuCountRow { id: _addButtonRow; label: "Add Button"; kind: "button"; enabled: !_root.editorLocked }
        MenuCountRow { id: _addAxisRow; label: "Add Axis"; kind: "axis"; enabled: !_root.editorLocked }
        MenuCountRow { id: _addHatRow; label: "Add Hat"; kind: "hat"; enabled: !_root.editorLocked }

        MenuSeparator {}

        MenuItem {
            text: "Add Action"
            enabled: _root._menuOnRow && !_root.editorLocked
            onTriggered: {
                var seq = _layout.addAction(_root._menuKey)
                if (seq >= 0)
                    _root._openPane(_root._menuKey, seq, _root._menuTitle)
            }
        }
        MenuItem {
            text: "Assign hardware"
            enabled: _root._menuOnRow && !_root.editorLocked
            onTriggered: {
                _hardwareKey = _root._menuKey
                _hardwareTitle.text = _root._menuTitle
                _search.text = ""
                _hardware.moduleOpen = ({})
                _loadHardware()
                _hardware.open()
            }
        }
        MenuItem {
            text: "Rename"
            enabled: _root._menuOnRow && !_root.editorLocked
            onTriggered: {
                _nameDialog.lastAccepted = _root._menuUser
                _nameDialog.text = _root._menuUser
                _nameDialog.showOption = true
                _nameDialog.optionText = "Hide system name"
                _nameDialog.optionChecked = _layout.hidesSystem(_root._menuKey)
                _nameDialog.visible = true
            }
        }
        MenuItem {
            text: "Clear name"
            enabled: _root._menuOnRow && !_root.editorLocked
            onTriggered: _layout.setUserName(_root._menuKey, "")
        }
        MenuNameRow {
            label: "Group as"
            enabled: _root._menuOnRow && !_root.editorLocked
            closeWhenNamed: true
            onNamed: (name) => _root._groupAs(name)
        }
        Menu {
            id: _moveMenu
            title: "Move to group"
            enabled: _root._menuOnRow && !_root.editorLocked
            Instantiator {
                model: _layout.groups
                delegate: MenuItem {
                    required property var modelData
                    text: modelData.title
                    onTriggered: _layout.moveSelected(modelData.name)
                }
                onObjectAdded: (index, object) => _moveMenu.insertItem(index, object)
                onObjectRemoved: (index, object) => _moveMenu.removeItem(object)
            }
        }
        MenuItem {
            text: "Delete"
            enabled: _root._menuOnRow && !_root.editorLocked
            onTriggered: _layout.deleteParents([_root._menuKey])
        }

        MenuSeparator {}

        MenuNameRow {
            label: "New group"
            enabled: !_root.editorLocked
            onNamed: (name) => _layout.addGroup(name)
        }
        MenuItem {
            text: "Move group up"
            enabled: _root._menuOnGroup && !_root.editorLocked
            onTriggered: _layout.moveGroupUp(_root._groupName)
        }
        MenuItem {
            text: "Move group down"
            enabled: _root._menuOnGroup && !_root.editorLocked
            onTriggered: _layout.moveGroupDown(_root._groupName)
        }
        MenuItem {
            text: "Rename group"
            enabled: _root._menuOnGroup && !_root.editorLocked
            onTriggered: {
                _groupDialog.text = _root._groupName
                _groupDialog.visible = true
            }
        }
        MenuItem {
            text: "Delete group"
            enabled: _root._menuOnGroup && !_root.editorLocked
            onTriggered: _layout.removeGroup(_root._groupName)
        }

        MenuSeparator {}

        MenuItem {
            text: "Order by system name"
            enabled: !_root.editorLocked
            onTriggered: _layout.sortBySystem()
        }
        MenuItem {
            text: "Order by your name"
            enabled: !_root.editorLocked
            onTriggered: _layout.sortByName()
        }
        MenuItem {
            text: "Order group names A to Z"
            enabled: !_root.editorLocked
            onTriggered: _layout.sortGroupNames()
        }

        MenuSeparator {}

        MenuItem {
            text: "Undo"
            enabled: !_root.editorLocked && _layout.canUndo
            onTriggered: _layout.undo()
        }
        MenuItem {
            text: "Redo"
            enabled: !_root.editorLocked && _layout.canRedo
            onTriggered: _layout.redo()
        }

        MenuSeparator {}

        MenuHeightRow { id: _rowHeightRow }
    }

    TextInputDialog {
        id: _nameDialog
        visible: false
        width: 320
        clearOnClick: false
        heading: "Your name"
        onAccepted: (value) => {
            _layout.setRowLabel(_root._menuKey, value, optionChecked)
            visible = false
        }
    }
    TextInputDialog {
        id: _groupDialog
        visible: false
        width: 320
        clearOnClick: false
        heading: "Rename group"
        validator: function(value) { return value.trim().length > 0 }
        onAccepted: (value) => {
            _layout.renameGroup(_root._groupName, value.trim())
            visible = false
        }
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
        property var moduleOpen: ({})
        function deviceOpen(name) {
            if (_search.text.length)
                return true
            return moduleOpen[name] === true
        }
        function toggleDevice(name) {
            var next = Object.assign({}, moduleOpen)
            next[name] = moduleOpen[name] !== true
            moduleOpen = next
        }
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
                contentHeight: _hwCol.childrenRect.height
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
                                Label {
                                    text: _hardware.deviceOpen(modelData.name) ? "▾" : "▸"
                                    color: "#A1A1AA"
                                    font.pixelSize: 14
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: _hardware.toggleDevice(modelData.name)
                                    }
                                }
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
                                Label {
                                    text: modelData.name
                                    color: "#E4E4E7"
                                    font.bold: true
                                    Layout.fillWidth: true
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: _hardware.toggleDevice(modelData.name)
                                    }
                                }
                            }
                            Repeater {
                                model: _hardware.deviceOpen(modelData.name) ? modelData.controls : []
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
        id: _moveWarn
        onConfirmed: {
            if (_root._pendingGroup.length)
                _layout.moveSelected(_root._pendingGroup)
            _root._pendingGroup = ""
        }
        onCancelled: _root._pendingGroup = ""
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

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs

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
    property bool displayOpen: false
    property int rowSpacing: 4
    property int groupInside: 0
    property string listPadShape: "sides"
    property int listPad: 0
    property int listPadTop: 0
    property int listPadRight: 0
    property int listPadBottom: 0
    property int listPadLeft: 0
    property string groupPadShape: "sides"
    property int groupPad: 0
    property int groupPadTop: 0
    property int groupPadRight: 8
    property int groupPadBottom: 0
    property int groupPadLeft: 8
    property int groupRadius: 3
    property string colorGroup: "#27272A"
    property string parentPadShape: "sides"
    property int parentPad: 0
    property int parentPadTop: 0
    property int parentPadRight: 8
    property int parentPadBottom: 0
    property int parentPadLeft: 24
    property int parentRadius: 3
    property string colorParent: "#18181B"
    property int childIndent: 32
    property string childPadShape: "sides"
    property int childPad: 0
    property int childPadTop: 0
    property int childPadRight: 8
    property int childPadBottom: 0
    property int childPadLeft: 0
    property int childRadius: 3
    property string colorChild: "#18181B"
    property bool showChildren: true
    property bool showSummary: true
    property int summaryFont: 11
    property int parentFont: 13
    property int groupFont: 15
    property int childFont: 13
    property bool parentBold: true
    property string colorText: "#E4E4E7"
    property string colorMuted: "#A1A1AA"
    property string colorSelected: "#1E3A5F"
    property string colorSelectBorder: "#3F3F46"
    property string colorBorder: "#3F3F46"
    property int caretSize: 18
    property int gripWidth: 8
    property int gripHeight: 18
    property string colorGrip: "#52525B"
    property string _colorTarget: "parent"
    property string toastText: "Display Options Saved"
    property string savedDisplay: ""
    property bool openShown: false
    property bool openHandles: false
    property bool openList: false
    property bool openGroup: false
    property bool openParent: false
    property bool openChild: false
    property bool openText: false
    property bool openSelection: false
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
        _place.setActionPaneWidth(paneWidth)
        _place.setClosePaneAfterOk(closeAfterOk)
    }

    function _saveDisplayOpen() {
        if (!_ready)
            return
        _place.setDisplayPanelOpen("logical", "page", displayOpen)
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

    function _hasList(kind, childCount, extraWriters) {
        if (kind === "group")
            return childCount > 0
        if (kind !== "parent" || !showChildren)
            return false
        if (childCount > 0)
            return true
        return showSummary && extraWriters > 0
    }

    function _rowVisible(kind, groupKey, parentKey) {
        if (kind !== "group" && _collapsed[groupKey])
            return false
        if (kind === "writer" && !showSummary)
            return false
        if (kind === "writer" || kind === "child")
            return showChildren && !!_opened[parentKey]
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
        reloadDisplay()
        displayOpen = _place.displayPanelOpen("logical", "page")
        _layout.setMode(mode)
        _ready = true
    }

    onPaneWidthChanged: _saveDock()
    onCloseAfterOkChanged: _saveDock()
    onDisplayOpenChanged: _saveDisplayOpen()
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
                Button {
                    text: _root.displayOpen ? "Hide Editor" : "Show Editor"
                    onClicked: _root.displayOpen = !_root.displayOpen
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
                    Layout.leftMargin: _root.padEdge(_root.listPadShape, _root.listPad, _root.listPadLeft)
                    Layout.rightMargin: _root.padEdge(_root.listPadShape, _root.listPad, _root.listPadRight)
                    Layout.topMargin: _root.padEdge(_root.listPadShape, _root.listPad, _root.listPadTop)
                    Layout.bottomMargin: _root.padEdge(_root.listPadShape, _root.listPad, _root.listPadBottom)
                    clip: true
                    spacing: _root.rowSpacing
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
                        required property int childCount
                        required property int extraWriters

                        readonly property bool shown: _root._rowVisible(rowKind, groupKey, parentKey)
                        width: _list.width - 16
                        readonly property int rowGap: rowKind === "group" ? 0 : _root.groupInside
                        readonly property int rowBody: rowKind === "group" ? 40 : (rowKind === "parent" ? _root.parentHeight : _root.childHeight)
                        height: shown ? implicitHeight : 0
                        visible: shown
                        clip: true
                        implicitHeight: rowBody + rowGap
                        color: "transparent"
                        border.width: 0

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: _row.rowBody
                            color: _root._picked.indexOf(key) >= 0 ? _root.colorSelected : (rowKind === "group" ? _root.colorGroup : (rowKind === "parent" ? _root.colorParent : _root.colorChild))
                            border.color: _root._picked.indexOf(key) >= 0 ? _root.colorSelectBorder : _root.colorBorder
                            border.width: 1
                            radius: rowKind === "group" ? _root.groupRadius : (rowKind === "parent" ? _root.parentRadius : _root.childRadius)
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: _root.rowLeft(rowKind)
                            anchors.rightMargin: _root.rowRight(rowKind)
                            anchors.topMargin: _root.rowTop(rowKind)
                            anchors.bottomMargin: _root.rowBottom(rowKind) + _row.rowGap
                            spacing: 6

                            Label {
                                visible: _root._hasList(rowKind, childCount, extraWriters)
                                text: (rowKind === "group" ? _root._collapsed[groupKey] : !_root._opened[key]) ? "▸" : "▾"
                                color: _root.colorText
                                font.pixelSize: _root.caretSize
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
                                width: _root.gripWidth
                                height: _root.gripHeight
                                radius: 2
                                color: _root.colorGrip
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
                                    border.color: _root.colorText
                                    border.width: 2
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 6
                                        height: 6
                                        radius: 3
                                        color: _root.colorText
                                    }
                                }
                                Item {
                                    visible: key.indexOf(":axis:") >= 0
                                    anchors.fill: parent
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 2
                                        height: 14
                                        color: _root.colorText
                                    }
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 8
                                        height: 6
                                        radius: 2
                                        color: _root.colorText
                                    }
                                }
                                Item {
                                    visible: key.indexOf(":hat:") >= 0
                                    anchors.fill: parent
                                    Rectangle { width: 4; height: 4; radius: 1; color: _root.colorText; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top }
                                    Rectangle { width: 4; height: 4; radius: 1; color: _root.colorText; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom }
                                    Rectangle { width: 4; height: 4; radius: 1; color: _root.colorText; anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left }
                                    Rectangle { width: 4; height: 4; radius: 1; color: _root.colorText; anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Label {
                                    text: title
                                    color: _root.colorText
                                    font.bold: rowKind === "child" ? false : _root.parentBold
                                    font.pixelSize: rowKind === "group" ? _root.groupFont : (rowKind === "parent" ? _root.parentFont : _root.childFont)
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
                                    visible: _root.showSummary && subtitle.length > 0 && rowKind !== "writer"
                                    text: subtitle
                                    color: _root.colorMuted
                                    font.pixelSize: _root.summaryFont
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
                            anchors.bottomMargin: _row.rowGap
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
                            anchors.bottomMargin: _row.rowGap
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

        Rectangle {
            visible: _root.displayOpen
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
                        text: "Logical Device — Display Editor"
                        color: "#E4E4E7"
                        font.bold: true
                        font.pixelSize: 13
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "×"
                        implicitWidth: 28
                        onClicked: _root.requestCloseDisplay()
                    }
                }
                RowLayout {
                    spacing: 8
                    Button { text: "Open all"; onClicked: _root.setAllSections(true) }
                    Button { text: "Close all"; onClicked: _root.setAllSections(false) }
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
                            title: "Shown"
                            open: _root.openShown
                            onToggled: (v) => { _root.openShown = v }
                            FlagBox { text: "Show child rows"; source: _root.showChildren; onUserSet: (v) => { _root.showChildren = v } }
                            FlagBox { text: "Show written by"; source: _root.showSummary; onUserSet: (v) => { _root.showSummary = v } }
                            RowLayout {
                                Label { text: "Written-by size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 9; to: 20; source: _root.summaryFont; onUserSet: (v) => { _root.summaryFont = v } }
                            }
                        }
                        FoldSection {
                            title: "Handles"
                            open: _root.openHandles
                            onToggled: (v) => { _root.openHandles = v }
                            RowLayout {
                                Label { text: "Caret size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 12; to: 24; source: _root.caretSize; onUserSet: (v) => { _root.caretSize = v } }
                            }
                            RowLayout {
                                Label { text: "Pad width"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 4; to: 24; source: _root.gripWidth; onUserSet: (v) => { _root.gripWidth = v } }
                            }
                            RowLayout {
                                Label { text: "Pad height"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 8; to: 28; source: _root.gripHeight; onUserSet: (v) => { _root.gripHeight = v } }
                            }
                            ColorPick { label: "Pad color"; swatch: _root.colorGrip; target: "grip" }
                        }
                        FoldSection {
                            title: "List"
                            open: _root.openList
                            onToggled: (v) => { _root.openList = v }
                            RowLayout {
                                Label { text: "Space between rows"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 48; source: _root.rowSpacing; onUserSet: (v) => { _root.rowSpacing = v } }
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: _root.listPadShape
                                size: _root.listPad
                                padTop: _root.listPadTop
                                padRight: _root.listPadRight
                                padBottom: _root.listPadBottom
                                padLeft: _root.listPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.listPadShape = shape
                                    _root.listPad = size
                                    _root.listPadTop = padTop
                                    _root.listPadRight = padRight
                                    _root.listPadBottom = padBottom
                                    _root.listPadLeft = padLeft
                                }
                            }
                        }
                        FoldSection {
                            title: "Group"
                            open: _root.openGroup
                            onToggled: (v) => { _root.openGroup = v }
                            RowLayout {
                                Label { text: "Space inside the group"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 48; source: _root.groupInside; onUserSet: (v) => { _root.groupInside = v } }
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: _root.groupPadShape
                                size: _root.groupPad
                                padTop: _root.groupPadTop
                                padRight: _root.groupPadRight
                                padBottom: _root.groupPadBottom
                                padLeft: _root.groupPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.groupPadShape = shape
                                    _root.groupPad = size
                                    _root.groupPadTop = padTop
                                    _root.groupPadRight = padRight
                                    _root.groupPadBottom = padBottom
                                    _root.groupPadLeft = padLeft
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: _root.groupRadius; onUserSet: (v) => { _root.groupRadius = v } }
                            }
                            ColorPick { label: "Color"; swatch: _root.colorGroup; target: "group" }
                        }
                        FoldSection {
                            title: "Parent row"
                            open: _root.openParent
                            onToggled: (v) => { _root.openParent = v }
                            RowLayout {
                                Label { text: "Height"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 32; to: 80; source: _root.parentHeight; onUserSet: (v) => { _root.parentHeight = v } }
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: _root.parentPadShape
                                size: _root.parentPad
                                padTop: _root.parentPadTop
                                padRight: _root.parentPadRight
                                padBottom: _root.parentPadBottom
                                padLeft: _root.parentPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.parentPadShape = shape
                                    _root.parentPad = size
                                    _root.parentPadTop = padTop
                                    _root.parentPadRight = padRight
                                    _root.parentPadBottom = padBottom
                                    _root.parentPadLeft = padLeft
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: _root.parentRadius; onUserSet: (v) => { _root.parentRadius = v } }
                            }
                            ColorPick { label: "Row color"; swatch: _root.colorParent; target: "parent" }
                        }
                        FoldSection {
                            title: "Child row"
                            open: _root.openChild
                            onToggled: (v) => { _root.openChild = v }
                            RowLayout {
                                Label { text: "Height"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 24; to: 80; source: _root.childHeight; onUserSet: (v) => { _root.childHeight = v } }
                            }
                            RowLayout {
                                Label { text: "Indent past parent"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 160; source: _root.childIndent; onUserSet: (v) => { _root.childIndent = v } }
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: _root.childPadShape
                                size: _root.childPad
                                padTop: _root.childPadTop
                                padRight: _root.childPadRight
                                padBottom: _root.childPadBottom
                                padLeft: _root.childPadLeft
                                onEdited: (shape, size, padTop, padRight, padBottom, padLeft) => {
                                    _root.childPadShape = shape
                                    _root.childPad = size
                                    _root.childPadTop = padTop
                                    _root.childPadRight = padRight
                                    _root.childPadBottom = padBottom
                                    _root.childPadLeft = padLeft
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: _root.childRadius; onUserSet: (v) => { _root.childRadius = v } }
                            }
                            ColorPick { label: "Row color"; swatch: _root.colorChild; target: "child" }
                        }
                        FoldSection {
                            title: "Text"
                            open: _root.openText
                            onToggled: (v) => { _root.openText = v }
                            RowLayout {
                                Label { text: "Parent text size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 10; to: 22; source: _root.parentFont; onUserSet: (v) => { _root.parentFont = v } }
                            }
                            RowLayout {
                                Label { text: "Group text size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 10; to: 22; source: _root.groupFont; onUserSet: (v) => { _root.groupFont = v } }
                            }
                            FlagBox { text: "Bold names"; source: _root.parentBold; onUserSet: (v) => { _root.parentBold = v } }
                            RowLayout {
                                Label { text: "Child text size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 9; to: 20; source: _root.childFont; onUserSet: (v) => { _root.childFont = v } }
                            }
                            ColorPick { label: "Text color"; swatch: _root.colorText; target: "text" }
                            ColorPick { label: "Muted text"; swatch: _root.colorMuted; target: "muted" }
                        }
                        FoldSection {
                            title: "Selection"
                            open: _root.openSelection
                            onToggled: (v) => { _root.openSelection = v }
                            ColorPick { label: "Fill of a selected row"; swatch: _root.colorSelected; target: "selected" }
                            ColorPick { label: "Line around a selected row"; swatch: _root.colorSelectBorder; target: "selectBorder" }
                        }
                    }
                }

                RowLayout {
                    spacing: 6
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Reset View\nto Default"
                        onClicked: _root.resetDisplay()
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
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Save View\nSettings"
                        highlighted: true
                        onClicked: _root.saveDisplay()
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
        implicitHeight: visible ? 34 : 0
        height: implicitHeight

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
        implicitHeight: visible ? 34 : 0
        height: implicitHeight

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

        onOpened: resetCounts()

        MenuCountRow { id: _addButtonRow; label: "Add Button"; kind: "button"; visible: !_root.editorLocked }
        MenuCountRow { id: _addAxisRow; label: "Add Axis"; kind: "axis"; visible: !_root.editorLocked }
        MenuCountRow { id: _addHatRow; label: "Add Hat"; kind: "hat"; visible: !_root.editorLocked }

        MenuSeparator { visible: _root._menuOnRow && !_root.editorLocked; height: visible ? implicitHeight : 0 }

        MenuItem {
            text: "Add Action"
            visible: _root._menuOnRow && !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: {
                var seq = _layout.addAction(_root._menuKey)
                if (seq >= 0)
                    _root._openPane(_root._menuKey, seq, _root._menuTitle)
            }
        }
        MenuItem {
            text: "Assign hardware"
            visible: _root._menuOnRow && !_root.editorLocked
            height: visible ? implicitHeight : 0
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
            visible: _root._menuOnRow && !_root.editorLocked
            height: visible ? implicitHeight : 0
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
            visible: _root._menuOnRow && !_root.editorLocked && _root._menuUser.length > 0
            height: visible ? implicitHeight : 0
            onTriggered: _layout.setUserName(_root._menuKey, "")
        }
        MenuNameRow {
            label: "Group as"
            visible: _root._menuOnRow && !_root.editorLocked
            closeWhenNamed: true
            onNamed: (name) => _root._groupAs(name)
        }
        MenuItem {
            id: _moveItem
            text: "Move to group"
            visible: _root._menuOnRow && !_root.editorLocked
            height: visible ? implicitHeight : 0
            indicator: Label {
                text: "\u203A"
                color: "#E4E4E7"
                font.pixelSize: 16
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 12
            }
            onTriggered: _moveMenu.popup(_moveItem, _moveItem.width, 0)
        }
        MenuItem {
            text: "Delete"
            visible: _root._menuOnRow && !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: _layout.deleteParents([_root._menuKey])
        }

        MenuSeparator { visible: !_root.editorLocked; height: visible ? implicitHeight : 0 }

        MenuNameRow {
            label: "New group"
            visible: !_root.editorLocked
            onNamed: (name) => _layout.addGroup(name)
        }
        MenuItem {
            text: "Move group up"
            visible: _root._menuOnGroup && !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: _layout.moveGroupUp(_root._groupName)
        }
        MenuItem {
            text: "Move group down"
            visible: _root._menuOnGroup && !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: _layout.moveGroupDown(_root._groupName)
        }
        MenuItem {
            text: "Rename group"
            visible: _root._menuOnGroup && !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: {
                _groupDialog.text = _root._groupName
                _groupDialog.visible = true
            }
        }
        MenuItem {
            text: "Delete group"
            visible: _root._menuOnGroup && !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: _layout.removeGroup(_root._groupName)
        }

        MenuSeparator { visible: !_root.editorLocked; height: visible ? implicitHeight : 0 }

        MenuItem {
            text: "Order by system name"
            visible: !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: _layout.sortBySystem()
        }
        MenuItem {
            text: "Order by your name"
            visible: !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: _layout.sortByName()
        }
        MenuItem {
            text: "Order group names A to Z"
            visible: !_root.editorLocked
            height: visible ? implicitHeight : 0
            onTriggered: _layout.sortGroupNames()
        }

        MenuSeparator { visible: !_root.editorLocked && (_layout.canUndo || _layout.canRedo); height: visible ? implicitHeight : 0 }

        MenuItem {
            text: "Undo"
            visible: !_root.editorLocked && _layout.canUndo
            height: visible ? implicitHeight : 0
            onTriggered: _layout.undo()
        }
        MenuItem {
            text: "Redo"
            visible: !_root.editorLocked && _layout.canRedo
            height: visible ? implicitHeight : 0
            onTriggered: _layout.redo()
        }

        MenuSeparator { visible: !_root.editorLocked; height: visible ? implicitHeight : 0 }

        MenuItem {
            text: "Display"
            onTriggered: _root.displayOpen = true
        }
    }


    Menu {
        id: _moveMenu
        Instantiator {
            model: _layout.groups
            delegate: MenuItem {
                required property var modelData
                text: modelData.title
                onTriggered: {
                    _layout.moveSelected(modelData.name)
                    _pageMenu.close()
                }
            }
            onObjectAdded: (index, object) => _moveMenu.insertItem(index, object)
            onObjectRemoved: (index, object) => _moveMenu.removeItem(object)
        }
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

    component PadFields: ColumnLayout {
        property string shape: "box"
        property int size: 8
        property int padTop: 0
        property int padRight: 8
        property int padBottom: 0
        property int padLeft: 8
        signal edited(string shape, int size, int padTop, int padRight, int padBottom, int padLeft)
        onShapeChanged: if (_shapePick) _shapePick.currentIndex = _shapePick.pick(shape)
        Layout.fillWidth: true
        spacing: 4

        RowLayout {
            Label { text: "Shape"; color: "#E4E4E7"; Layout.preferredWidth: 70 }
            ComboBox {
                id: _shapePick
                Layout.fillWidth: true
                model: ["Same on all sides", "Each side"]
                function pick(value) { return value === "sides" ? 1 : 0 }
                Component.onCompleted: currentIndex = pick(shape)
                onActivated: {
                    if (currentIndex === 0)
                        edited("box", size, size, size, size, size)
                    else
                        edited("sides", size, padTop, padRight, padBottom, padLeft)
                }
            }
        }
        RowLayout {
            visible: shape !== "sides"
            Label { text: "Size"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: size; onUserSet: (v) => { edited("box", v, v, v, v, v) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Top"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padTop; onUserSet: (v) => { edited("sides", size, v, padRight, padBottom, padLeft) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Right"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padRight; onUserSet: (v) => { edited("sides", size, padTop, v, padBottom, padLeft) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Bottom"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padBottom; onUserSet: (v) => { edited("sides", size, padTop, padRight, v, padLeft) } }
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Left"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 48; source: padLeft; onUserSet: (v) => { edited("sides", size, padTop, padRight, padBottom, v) } }
        }
    }

    component ColorPick: RowLayout {
        property string label: ""
        property color swatch: "#18181B"
        property string target: ""
        Layout.fillWidth: true
        Label {
            text: label
            color: "#E4E4E7"
            wrapMode: Text.WordWrap
            Layout.preferredWidth: 150
            Layout.maximumWidth: 160
        }
        Button {
            Layout.fillWidth: true
            text: "Choose\u2026"
            onClicked: { _root._colorTarget = target; _colorDlg.selectedColor = swatch; _colorDlg.open() }
            background: Rectangle { color: swatch; border.color: "#3F3F46"; border.width: 1; radius: 3 }
            contentItem: Label { text: parent.text; color: "#F4F4F5"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
    }

    function padEdge(shape, size, side) {
        return shape === "box" ? size : side
    }

    function rowLeft(kind) {
        if (kind === "group")
            return padEdge(groupPadShape, groupPad, groupPadLeft)
        var parentLeft = padEdge(parentPadShape, parentPad, parentPadLeft)
        if (kind === "parent")
            return parentLeft
        return parentLeft + childIndent + padEdge(childPadShape, childPad, childPadLeft)
    }

    function rowRight(kind) {
        if (kind === "group")
            return padEdge(groupPadShape, groupPad, groupPadRight)
        if (kind === "parent")
            return padEdge(parentPadShape, parentPad, parentPadRight)
        return padEdge(childPadShape, childPad, childPadRight)
    }

    function rowTop(kind) {
        if (kind === "group")
            return padEdge(groupPadShape, groupPad, groupPadTop)
        if (kind === "parent")
            return padEdge(parentPadShape, parentPad, parentPadTop)
        return padEdge(childPadShape, childPad, childPadTop)
    }

    function rowBottom(kind) {
        if (kind === "group")
            return padEdge(groupPadShape, groupPad, groupPadBottom)
        if (kind === "parent")
            return padEdge(parentPadShape, parentPad, parentPadBottom)
        return padEdge(childPadShape, childPad, childPadBottom)
    }

    function numVal(v, d) {
        var n = Number(v)
        return (v === undefined || v === null || v === "" || isNaN(n)) ? d : n
    }

    function displayPayload() {
        return {
            "rowSpacing": rowSpacing,
            "groupInside": groupInside,
            "listPadShape": listPadShape,
            "listPad": listPad,
            "listPadTop": listPadTop,
            "listPadRight": listPadRight,
            "listPadBottom": listPadBottom,
            "listPadLeft": listPadLeft,
            "groupPadShape": groupPadShape,
            "groupPad": groupPad,
            "groupPadTop": groupPadTop,
            "groupPadRight": groupPadRight,
            "groupPadBottom": groupPadBottom,
            "groupPadLeft": groupPadLeft,
            "groupRadius": groupRadius,
            "colorGroup": colorGroup,
            "parentHeight": parentHeight,
            "parentPadShape": parentPadShape,
            "parentPad": parentPad,
            "parentPadTop": parentPadTop,
            "parentPadRight": parentPadRight,
            "parentPadBottom": parentPadBottom,
            "parentPadLeft": parentPadLeft,
            "parentRadius": parentRadius,
            "colorParent": colorParent,
            "childHeight": childHeight,
            "childIndent": childIndent,
            "childPadShape": childPadShape,
            "childPad": childPad,
            "childPadTop": childPadTop,
            "childPadRight": childPadRight,
            "childPadBottom": childPadBottom,
            "childPadLeft": childPadLeft,
            "childRadius": childRadius,
            "colorChild": colorChild,
            "showChildren": showChildren,
            "showSummary": showSummary,
            "summaryFont": summaryFont,
            "parentFont": parentFont,
            "groupFont": groupFont,
            "childFont": childFont,
            "parentBold": parentBold,
            "colorText": colorText,
            "colorMuted": colorMuted,
            "colorSelected": colorSelected,
            "colorSelectBorder": colorSelectBorder,
            "colorBorder": colorBorder,
            "caretSize": caretSize,
            "gripWidth": gripWidth,
            "gripHeight": gripHeight,
            "colorGrip": colorGrip
        }
    }

    function applyDisplay(v) {
        if (!v)
            return
        rowSpacing = numVal(v.rowSpacing, 4)
        groupInside = numVal(v.groupInside, 0)
        listPadShape = v.listPadShape || "sides"
        listPad = numVal(v.listPad, 0)
        listPadTop = numVal(v.listPadTop, 0)
        listPadRight = numVal(v.listPadRight, 0)
        listPadBottom = numVal(v.listPadBottom, 0)
        listPadLeft = numVal(v.listPadLeft, 0)
        groupPadShape = v.groupPadShape || "sides"
        groupPad = numVal(v.groupPad, 0)
        groupPadTop = numVal(v.groupPadTop, 0)
        groupPadRight = numVal(v.groupPadRight, 8)
        groupPadBottom = numVal(v.groupPadBottom, 0)
        groupPadLeft = numVal(v.groupPadLeft, 8)
        groupRadius = numVal(v.groupRadius, 3)
        colorGroup = v.colorGroup || "#27272A"
        parentHeight = numVal(v.parentHeight, 44)
        parentPadShape = v.parentPadShape || "sides"
        parentPad = numVal(v.parentPad, 0)
        parentPadTop = numVal(v.parentPadTop, 0)
        parentPadRight = numVal(v.parentPadRight, 8)
        parentPadBottom = numVal(v.parentPadBottom, 0)
        parentPadLeft = numVal(v.parentPadLeft, 24)
        parentRadius = numVal(v.parentRadius, 3)
        colorParent = v.colorParent || "#18181B"
        childHeight = numVal(v.childHeight, 32)
        childIndent = numVal(v.childIndent, 32)
        childPadShape = v.childPadShape || "sides"
        childPad = numVal(v.childPad, 0)
        childPadTop = numVal(v.childPadTop, 0)
        childPadRight = numVal(v.childPadRight, 8)
        childPadBottom = numVal(v.childPadBottom, 0)
        childPadLeft = numVal(v.childPadLeft, 0)
        childRadius = numVal(v.childRadius, 3)
        colorChild = v.colorChild || "#18181B"
        showChildren = v.showChildren !== false
        showSummary = v.showSummary !== false
        summaryFont = numVal(v.summaryFont, 11)
        parentFont = numVal(v.parentFont, 13)
        groupFont = numVal(v.groupFont, 15)
        childFont = numVal(v.childFont, 13)
        parentBold = v.parentBold !== false
        colorText = v.colorText || "#E4E4E7"
        colorMuted = v.colorMuted || "#A1A1AA"
        colorSelected = v.colorSelected || "#1E3A5F"
        colorSelectBorder = v.colorSelectBorder || "#3F3F46"
        colorBorder = v.colorBorder || "#3F3F46"
        caretSize = numVal(v.caretSize, 18)
        gripWidth = numVal(v.gripWidth, 8)
        gripHeight = numVal(v.gripHeight, 18)
        colorGrip = v.colorGrip || "#52525B"
    }

    function applyDisplayDefaults() {
        rowSpacing = 4
        groupInside = 0
        listPadShape = "sides"
        listPad = 0
        listPadTop = 0
        listPadRight = 0
        listPadBottom = 0
        listPadLeft = 0
        groupPadShape = "sides"
        groupPad = 0
        groupPadTop = 0
        groupPadRight = 8
        groupPadBottom = 0
        groupPadLeft = 8
        groupRadius = 3
        colorGroup = "#27272A"
        parentHeight = 44
        parentPadShape = "sides"
        parentPad = 0
        parentPadTop = 0
        parentPadRight = 8
        parentPadBottom = 0
        parentPadLeft = 24
        parentRadius = 3
        colorParent = "#18181B"
        childHeight = 32
        childIndent = 32
        childPadShape = "sides"
        childPad = 0
        childPadTop = 0
        childPadRight = 8
        childPadBottom = 0
        childPadLeft = 0
        childRadius = 3
        colorChild = "#18181B"
        showChildren = true
        showSummary = true
        summaryFont = 11
        parentFont = 13
        groupFont = 15
        childFont = 13
        parentBold = true
        colorText = "#E4E4E7"
        colorMuted = "#A1A1AA"
        colorSelected = "#1E3A5F"
        colorSelectBorder = "#3F3F46"
        colorBorder = "#3F3F46"
        caretSize = 18
        gripWidth = 8
        gripHeight = 18
        colorGrip = "#52525B"
        setAllSections(false)
    }

    function setAllSections(v) {
        openShown = v
        openHandles = v
        openList = v
        openGroup = v
        openParent = v
        openChild = v
        openText = v
        openSelection = v
    }

    function rememberDisplay() {
        savedDisplay = JSON.stringify(displayPayload())
    }

    function displayDirty() {
        return savedDisplay.length > 0 && JSON.stringify(displayPayload()) !== savedDisplay
    }

    function reloadDisplay() {
        var raw = _place.logicalValue("display")
        if (!raw.length) {
            applyDisplayDefaults()
            var h = parseInt(_place.logicalValue("parentHeight"))
            if (!isNaN(h) && h >= 32 && h <= 80)
                parentHeight = h
        } else {
            try {
                applyDisplay(JSON.parse(raw))
            } catch (e) {
                applyDisplayDefaults()
            }
        }
        rememberDisplay()
    }

    function saveDisplay() {
        _place.setLogicalValue("display", JSON.stringify(displayPayload()))
        rememberDisplay()
        toastText = "Saved for this page."
        _savedToast.open()
    }

    function resetDisplay() {
        applyDisplayDefaults()
        toastText = "Options have been reset"
        _savedToast.open()
    }

    function requestCloseDisplay() {
        if (!displayDirty()) {
            displayOpen = false
            return
        }
        _displayGate.ask("Display options are not saved. Close this panel and they will be lost.")
    }

    ColorDialog {
        id: _colorDlg
        title: "Choose color"
        onAccepted: {
            var c = selectedColor.toString()
            if (_colorTarget === "child") colorChild = c
            else if (_colorTarget === "selected") colorSelected = c
            else if (_colorTarget === "text") colorText = c
            else if (_colorTarget === "muted") colorMuted = c
            else if (_colorTarget === "selectBorder") colorSelectBorder = c
            else if (_colorTarget === "border") colorBorder = c
            else if (_colorTarget === "group") colorGroup = c
            else if (_colorTarget === "grip") colorGrip = c
            else colorParent = c
        }
    }

    DismissibleDialog {
        id: _displayGate
        onSaveChosen: {
            saveDisplay()
            displayOpen = false
        }
        onDiscardChosen: {
            reloadDisplay()
            displayOpen = false
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
            interval: 1400
            onTriggered: _savedToast.close()
        }
        onOpened: _savedTimer.restart()
        onClosed: _savedTimer.stop()
    }

}

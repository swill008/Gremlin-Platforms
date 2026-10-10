// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The control list shared by the control pages (Logical Device, OSC):
// group, parent and action rows from the page's layout model, carets,
// multi-select, drag order. Menus stay with the page: the rows only say
// where the right-click was.
Item {
    id: _tree

    property var layout: null
    property bool locked: false
    property string namePrefix: "control"
    property string emptyText: ""
    property bool filtering: false
    property string dragMime: "application/x-gremlin-control"
    // The drag ghost is drawn here so the list never clips it.
    property Item dragLayer: _tree
    // Page-only widgets at the right end of a row. The loaded item's parent
    // has rowModel (the row's model data) and locked; the item says whether
    // it takes room with "property bool wanted".
    property Component rowExtras: null

    // Appearance; the defaults are the Logical Device page's.
    property int parentHeight: 44
    property int childHeight: 32
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
    property color colorGroup: Style.bgRaised
    property string parentPadShape: "sides"
    property int parentPad: 0
    property int parentPadTop: 0
    property int parentPadRight: 8
    property int parentPadBottom: 0
    property int parentPadLeft: 24
    property int parentRadius: 3
    property color colorParent: Style.bgCard
    property int parentIndent: 16
    property int childIndent: 32
    property string childPadShape: "sides"
    property int childPad: 0
    property int childPadTop: 0
    property int childPadRight: 8
    property int childPadBottom: 0
    property int childPadLeft: 0
    property int childRadius: 3
    property color colorChild: Style.bgCard
    property bool showChildren: true
    property bool showSummary: true
    property int summaryFont: 11
    property int parentFont: 13
    property int groupFont: 15
    property int childFont: 13
    property int targetFont: 11
    property color colorActionTarget: Style.fgMuted
    property bool parentBold: true
    property color colorText: Style.fg
    property color colorMuted: Style.fgMuted
    property color colorSelected: Style.infoFill
    property color colorSelectBorder: Style.line
    property color colorBorder: Style.line
    property int caretSize: 18
    property color colorCaret: Style.fg
    property int gripWidth: 8
    property int gripHeight: 18
    property int gripRadius: 2
    property color colorGrip: Style.lineStrong

    // Selected parent keys; open parents; folded groups.
    property var picked: ([])
    property var opened: ({})
    property var collapsed: ({})
    property string _dragFrom: ""

    signal parentMenu(string key, string title, string userName, string groupName, var item, real x, real y)
    signal groupMenu(string groupName, var item, real x, real y)
    signal actionMenu(string parentKey, int seq, string title, var item, real x, real y)
    signal pageMenu(var item, real x, real y)
    signal actionClicked(string parentKey, int seq, string title)
    signal clearFilters()

    function toggleOpen(key) {
        var next = Object.assign({}, opened)
        next[key] = !next[key]
        opened = next
    }

    function toggleGroup(key) {
        var next = Object.assign({}, collapsed)
        next[key] = !next[key]
        collapsed = next
    }

    function select(key, shift) {
        var next = picked.slice()
        if (!shift) {
            next = [key]
        } else {
            var at = next.indexOf(key)
            if (at < 0)
                next.push(key)
            else
                next.splice(at, 1)
        }
        picked = next
        layout.setSelection(next)
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
        if (kind !== "group" && collapsed[groupKey])
            return false
        if (kind === "writer" && !showSummary)
            return false
        if (kind === "writer" || kind === "child")
            return showChildren && !!opened[parentKey]
        return true
    }

    // Moves run after the mouse and drop handlers finish: the move rebuilds the
    // rows, and a handler still running in a destroyed row loses its names.
    function moveLater(kind, from, to, where) {
        if (!from || !to)
            return
        var model = layout
        Qt.callLater(function() {
            if (kind === "row")
                model.moveRow(from, to)
            else
                model.moveParent(from, to, where)
        })
    }

    function padEdge(shape, size, side) {
        return shape === "box" ? size : side
    }

    function padPx(shape, size, side) {
        return Style.dp(padEdge(shape, size, side))
    }

    // How far a row's box starts from the list's left edge.
    function rowIndent(kind) {
        if (kind === "group")
            return 0
        if (kind === "parent")
            return Style.dp(parentIndent)
        return Style.dp(parentIndent + childIndent)
    }

    // Text inset inside the row's box. Action text lines up with its parent's text.
    function rowLeft(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadLeft)
        var parentLeft = padPx(parentPadShape, parentPad, parentPadLeft)
        if (kind === "parent")
            return parentLeft
        return parentLeft + padPx(childPadShape, childPad, childPadLeft)
    }

    function rowRight(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadRight)
        if (kind === "parent")
            return padPx(parentPadShape, parentPad, parentPadRight)
        return padPx(childPadShape, childPad, childPadRight)
    }

    function rowTop(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadTop)
        if (kind === "parent")
            return padPx(parentPadShape, parentPad, parentPadTop)
        return padPx(childPadShape, childPad, childPadTop)
    }

    function rowBottom(kind) {
        if (kind === "group")
            return padPx(groupPadShape, groupPad, groupPadBottom)
        if (kind === "parent")
            return padPx(parentPadShape, parentPad, parentPadBottom)
        return padPx(childPadShape, childPad, childPadBottom)
    }

    ListView {
        id: _list
        anchors.fill: parent
        anchors.leftMargin: _tree.padPx(_tree.listPadShape, _tree.listPad, _tree.listPadLeft)
        anchors.rightMargin: _tree.padPx(_tree.listPadShape, _tree.listPad, _tree.listPadRight)
        anchors.topMargin: _tree.padPx(_tree.listPadShape, _tree.listPad, _tree.listPadTop)
        anchors.bottomMargin: _tree.padPx(_tree.listPadShape, _tree.listPad, _tree.listPadBottom)
        clip: true
        spacing: 0
        model: _tree.layout
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

        MouseArea {
            z: -1
            anchors.fill: parent
            acceptedButtons: Qt.RightButton
            onClicked: (mouse) => _tree.pageMenu(_list, mouse.x, mouse.y)
        }

        // Nothing listed: say why, and how to start (01 S143).
        EmptyState {
            objectName: _tree.namePrefix + "Empty"
            anchors.centerIn: parent
            width: Math.min(parent.width - Style.dp(32), Style.dp(360))
            visible: _list.count === 0
            text: _tree.filtering ? "Nothing matches the Find filters." : _tree.emptyText
            actionText: _tree.filtering ? "Clear Filters" : ""
            onAction: _tree.clearFilters()
        }

        delegate: Rectangle {
            id: _row
            required property var model
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
            required property int sequenceIndex
            required property int childCount
            readonly property int extraWriters: model.extraWriters || 0

            readonly property bool shown: _tree._rowVisible(rowKind, groupKey, parentKey)
            width: _list.width - Style.dp(16)
            readonly property int rowGap: rowKind === "group" ? 0 : Style.dp(_tree.groupInside)
            readonly property int rowMin: Style.dp(rowKind === "group" ? 40 : (rowKind === "parent" ? _tree.parentHeight : _tree.childHeight))
            readonly property int rowPadY: _tree.rowTop(rowKind) + _tree.rowBottom(rowKind)
            readonly property int rowNeed: _line.implicitHeight + rowPadY
            readonly property int rowBody: Math.max(rowMin, rowNeed)
            height: shown ? implicitHeight : 0
            visible: shown
            clip: true
            implicitHeight: shown ? (rowBody + rowGap + Style.dp(_tree.rowSpacing)) : 0
            color: "transparent"
            border.width: 0

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: _tree.rowIndent(rowKind)
                height: _row.rowBody
                color: _tree.picked.indexOf(key) >= 0 ? _tree.colorSelected : (rowKind === "group" ? _tree.colorGroup : (rowKind === "parent" ? _tree.colorParent : _tree.colorChild))
                border.color: _tree.picked.indexOf(key) >= 0 ? _tree.colorSelectBorder : _tree.colorBorder
                border.width: Style.dp(1)
                radius: Style.dp(rowKind === "group" ? _tree.groupRadius : (rowKind === "parent" ? _tree.parentRadius : _tree.childRadius))
            }

            RowLayout {
                id: _line
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: _tree.rowIndent(rowKind) + _tree.rowLeft(rowKind)
                anchors.rightMargin: _tree.rowRight(rowKind)
                anchors.topMargin: _tree.rowTop(rowKind)
                height: Math.max(implicitHeight, _row.rowMin - _row.rowPadY)
                spacing: Style.dp(6)

                Label {
                    id: _caret
                    visible: _tree._hasList(rowKind, childCount, _row.extraWriters)
                    text: (rowKind === "group" ? _tree.collapsed[groupKey] : !_tree.opened[key]) ? "▸" : "▾"
                    color: _tree.colorCaret
                    font.pixelSize: Style.dp(_tree.caretSize)
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: visible ? implicitWidth : 0
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (rowKind === "group")
                                _tree.toggleGroup(groupKey)
                            else
                                _tree.toggleOpen(key)
                        }
                    }
                }
                Rectangle {
                    visible: rowKind === "parent" || rowKind === "group"
                    implicitWidth: visible ? Style.dp(_tree.gripWidth) : 0
                    implicitHeight: visible ? Style.dp(_tree.gripHeight) : 0
                    Layout.preferredWidth: visible ? Style.dp(_tree.gripWidth) : 0
                    Layout.preferredHeight: visible ? Style.dp(_tree.gripHeight) : 0
                    Layout.alignment: Qt.AlignVCenter
                    radius: Style.dp(_tree.gripRadius)
                    color: _tree.colorGrip
                    MouseArea {
                        id: _grip
                        anchors.fill: parent
                        anchors.margins: -Style.dp(6)
                        enabled: !_tree.locked
                        cursorShape: rowKind === "parent" ? Qt.OpenHandCursor : Qt.SizeAllCursor
                        preventStealing: true
                        onPressed: (mouse) => {
                            if (rowKind !== "parent") {
                                _tree._dragFrom = key
                                return
                            }
                            // The ghost is held where the row was pressed.
                            var inRow = mapToItem(_row, mouse.x, mouse.y)
                            _payload.Drag.hotSpot.x = inRow.x
                            _payload.Drag.hotSpot.y = inRow.y
                            _payload.pressAt = mapToItem(_tree.dragLayer, mouse.x, mouse.y)
                            _row.grabToImage(function(result) {
                                _payload.ghost = result.url
                            }, Qt.size(_row.width, _row.height))
                        }
                        // In-app drag: it starts while the button is held, never
                        // after release, so it cannot swallow the next click.
                        onPositionChanged: (mouse) => {
                            if (rowKind !== "parent")
                                return
                            var pos = mapToItem(_tree.dragLayer, mouse.x, mouse.y)
                            if (!_payload.Drag.active
                                    && Math.abs(pos.x - _payload.pressAt.x) + Math.abs(pos.y - _payload.pressAt.y) < Style.dp(4))
                                return
                            _payload.x = pos.x - _payload.Drag.hotSpot.x
                            _payload.y = pos.y - _payload.Drag.hotSpot.y
                            _payload.Drag.active = true
                        }
                        onReleased: (mouse) => {
                            if (rowKind === "parent") {
                                if (_payload.Drag.active)
                                    _payload.Drag.drop()
                                return
                            }
                            var pos = mapToItem(_list.contentItem, mouse.x, mouse.y)
                            var hit = _list.indexAt(pos.x, pos.y)
                            var from = _tree._dragFrom
                            _tree._dragFrom = ""
                            if (hit >= 0)
                                _tree.moveLater("row", from, _tree.layout.keyAt(hit), "")
                        }
                        onCanceled: {
                            if (_payload.Drag.active)
                                _payload.Drag.cancel()
                            _tree._dragFrom = ""
                        }
                    }
                }
                Item {
                    visible: rowKind === "parent"
                    Layout.preferredWidth: visible ? Style.dp(16) : 0
                    Layout.preferredHeight: Style.dp(16)
                    Layout.alignment: Qt.AlignVCenter

                    Rectangle {
                        visible: key.indexOf(":button:") >= 0
                        anchors.centerIn: parent
                        width: Style.dp(14)
                        height: Style.dp(14)
                        radius: Style.dp(7)
                        color: "transparent"
                        border.color: _tree.colorText
                        border.width: Style.dp(2)
                        Rectangle {
                            anchors.centerIn: parent
                            width: Style.dp(6)
                            height: Style.dp(6)
                            radius: Style.dp(3)
                            color: _tree.colorText
                        }
                    }
                    Item {
                        visible: key.indexOf(":axis:") >= 0
                        anchors.fill: parent
                        Rectangle {
                            anchors.centerIn: parent
                            width: Style.dp(2)
                            height: Style.dp(14)
                            color: _tree.colorText
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: Style.dp(8)
                            height: Style.dp(6)
                            radius: Style.dp(2)
                            color: _tree.colorText
                        }
                    }
                    Item {
                        visible: key.indexOf(":hat:") >= 0
                        anchors.fill: parent
                        Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _tree.colorText; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top }
                        Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _tree.colorText; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom }
                        Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _tree.colorText; anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left }
                        Rectangle { width: Style.dp(4); height: Style.dp(4); radius: Style.dp(1); color: _tree.colorText; anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: Style.dp(2)
                    Label {
                        text: title
                        color: _tree.colorText
                        font.bold: rowKind === "child" ? false : _tree.parentBold
                        font.pixelSize: Style.dp(rowKind === "group" ? _tree.groupFont : (rowKind === "parent" ? _tree.parentFont : _tree.childFont))
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        HoverHandler { id: _nameHover }
                        ToolTip {
                            visible: _nameHover.hovered && rowKind === "parent" && userName.length > 0
                            text: systemName
                            x: _nameHover.point.position.x - width / 2
                            y: _nameHover.point.position.y - height - Style.dp(8)
                        }
                    }
                    Label {
                        visible: _tree.showSummary && subtitle.length > 0 && rowKind !== "writer"
                        text: subtitle
                        color: rowKind === "child" ? _tree.colorActionTarget : _tree.colorMuted
                        font.pixelSize: Style.dp(rowKind === "child" ? _tree.targetFont : _tree.summaryFont)
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        Layout.bottomMargin: visible ? Style.dp(4) : 0
                    }
                }
                Loader {
                    // Presses on these widgets stay with them.
                    property bool ownsPress: true
                    property var rowModel: _row.model
                    property bool locked: _tree.locked
                    active: _tree.rowExtras !== null
                    sourceComponent: _tree.rowExtras
                    visible: !!item && item.wanted === true
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            DropArea {
                id: _drop
                anchors.fill: parent
                anchors.bottomMargin: _row.rowGap
                z: 4
                enabled: !_tree.locked && (rowKind === "parent" || rowKind === "group")
                keys: [_tree.dragMime]
                property bool placeBefore: true
                onPositionChanged: (drag) => {
                    var source = drag.source && drag.source.dragKey ? drag.source.dragKey : ""
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
                    var source = drop.source && drop.source.dragKey ? drop.source.dragKey : ""
                    if (!source || source === key)
                        return
                    drop.accept(Qt.MoveAction)
                    _tree.moveLater("parent", source, key,
                                    rowKind === "group" ? "into" : (placeBefore ? "before" : "after"))
                }
                Rectangle {
                    id: _insertLine
                    visible: false
                    z: 6
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: Style.dp(2)
                    color: Style.info
                }
            }

            Item {
                id: _payload
                parent: _tree.dragLayer
                z: 100
                width: Style.dp(1)
                height: Style.dp(1)
                property string dragKey: key
                property url ghost
                property point pressAt
                Drag.dragType: Drag.Internal
                Drag.keys: [_tree.dragMime]
                Drag.supportedActions: Qt.MoveAction
                Drag.proposedAction: Qt.MoveAction
                Image {
                    visible: _payload.Drag.active
                    source: _payload.ghost
                    width: _row.width
                    height: _row.height
                    opacity: 0.85
                }
            }

            MouseArea {
                z: 1
                anchors.fill: parent
                anchors.bottomMargin: _row.rowGap
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                propagateComposedEvents: true
                onPressed: (mouse) => {
                    // Leave presses on the caret, the grip and the row's own widgets to them.
                    if (mouse.button !== Qt.LeftButton)
                        return
                    var at = mapToItem(_line, mouse.x, mouse.y)
                    var hit = _line.childAt(at.x, at.y)
                    if (hit && (hit === _caret || hit === _grip.parent || hit.ownsPress))
                        mouse.accepted = false
                }
                onClicked: (mouse) => {
                    if (mouse.button === Qt.RightButton) {
                        if (rowKind === "parent") {
                            if (_tree.picked.indexOf(key) < 0)
                                _tree.select(key, false)
                            _tree.parentMenu(key, title, userName, groupName, _row, mouse.x, mouse.y)
                        } else if (rowKind === "group" && groupName.length > 0) {
                            _tree.groupMenu(groupName, _row, mouse.x, mouse.y)
                        } else if (rowKind === "child" && !_tree.locked) {
                            _tree.actionMenu(parentKey, sequenceIndex, title, _row, mouse.x, mouse.y)
                        } else {
                            _tree.pageMenu(_row, mouse.x, mouse.y)
                        }
                        return
                    }
                    if (rowKind === "parent")
                        _tree.select(key, mouse.modifiers & Qt.ShiftModifier)
                    else if (rowKind === "child")
                        _tree.actionClicked(parentKey, sequenceIndex, title)
                    else if (rowKind === "group")
                        _tree.toggleGroup(groupKey)
                }
            }
        }
    }
}

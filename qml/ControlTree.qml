// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The control list shared by the control pages (Device Bindings, Logical
// Device, OSC): group, parent and action rows from the page's layout model,
// carets, multi-select, drag order. Menus stay with the page: the rows only
// say where the right-click was. Live lights and bars are an optional
// decoration, on for the Device Bindings page only (05 S131).
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
    // View only: no grips, no drag or drop, no right-click menus and no
    // signals that open a pane; a click only selects, carets still fold.
    property bool readOnly: false
    // False: group rows are not drawn and rows are not indented under them.
    property bool showGroups: true
    // False: the list doesn't scroll itself (no flick, no scrollbar); an
    // outer ScrollView sizes it from listHeight and scrolls it.
    property bool ownScroll: true
    // The rows' full height with the list padding, for that outer view.
    readonly property real listHeight: _list.contentHeight
        + padPx(listPadShape, listPad, listPadTop)
        + padPx(listPadShape, listPad, listPadBottom)

    // Appearance; the defaults are the Logical Device page's.
    property int parentHeight: 44
    property int childHeight: 32
    property int rowSpacing: 4
    property int groupInside: 0
    // Row placement (AP3): input (parent) rows and action rows (every other
    // non-group row) take widthPct of the room right of their indent, placed
    // left, center or right; groupSpacing is extra room above each group
    // after the first. Defaults: today's full-width, left-placed rows.
    property string parentAlign: "left"
    property int parentWidthPct: 100
    property string childAlign: "left"
    property int childWidthPct: 100
    property int groupSpacing: 0
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
    // The grey "N actions · targets" after a parent row's name (05 S142):
    // off unless the page turns it on (Appearance › Shown); the Xbox
    // Output View's read-only list leaves it off.
    property bool showActionSummary: false
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

    // Live decoration (05 S131): a pressed button or hat tints its parent
    // row, an axis gets a bar along the row's bottom. The values come from
    // liveState (a DeviceLiveState: stamp, kindAt(i), valueAt(i)) at the
    // row's "liveIndex" role (-1 or missing: no live value).
    property bool liveDecoration: false
    property var liveState: null
    property bool liveBars: true
    property bool liveLeds: true
    property color colorLive: Style.ok

    // The row last shown by showKey(); _flashKey outlines it for a moment.
    property string highlightKey: ""
    property string _flashKey: ""

    // Selected parent keys; open parents; folded groups. No [] / {} here:
    // a literal is a binding, and select() / toggleOpen() / toggleGroup()
    // assign them (qt.qml.binding.removal). Set in Component.onCompleted;
    // rows built before that read them guarded.
    property var picked: null
    property var opened: null
    property var collapsed: null
    property string _dragFrom: ""

    signal parentMenu(string key, string title, string userName, string groupName, var item, real x, real y)
    signal groupMenu(string groupName, var item, real x, real y)
    signal actionMenu(string parentKey, int seq, string title, var item, real x, real y)
    signal pageMenu(var item, real x, real y)
    signal actionClicked(string parentKey, int seq, string title)
    // Left click on a parent row, after the tree has selected it.
    signal parentClicked(string key, string title, bool shift)
    // Rows of kind "feedback" (OSC, 09 S153): offered while locked too,
    // since feedback stays editable while a profile runs (S155).
    signal feedbackMenu(string key, string title, bool enabled, var item, real x, real y)
    signal feedbackClicked(string key, string title)
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
        var next = (picked || []).slice()
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
        if (kind === "group" && !showGroups)
            return false
        if (kind !== "group" && showGroups && (collapsed || {})[groupKey])
            return false
        if (kind === "writer" && !showSummary)
            return false
        if (kind === "writer" || kind === "child")
            return showChildren && !!(opened || {})[parentKey]
        // Feedback rows sit under an input (opened with it) or in a group
        // of their own (shown while the group is unfolded).
        if (kind === "feedback")
            return parentKey === groupKey || (showChildren && !!(opened || {})[parentKey])
        return true
    }

    function _rowOf(key) {
        if (!layout || !key)
            return -1
        for (var i = 0; i < _list.count; ++i) {
            if (layout.keyAt(i) === key)
                return i
        }
        return -1
    }

    // Jump to an input (the pressed one): unfold its group and its parent,
    // scroll it into view and flash it. False when the key isn't listed.
    // Selecting it is the page's choice (select()).
    function showKey(key) {
        var row = _rowOf(key)
        if (row < 0)
            return false
        _list.positionViewAtIndex(row, ListView.Contain)
        var item = _list.itemAtIndex(row)
        if (item && collapsed[item.groupKey])
            toggleGroup(item.groupKey)
        if (item && item.rowKind !== "group" && item.rowKind !== "parent" && item.parentKey && !opened[item.parentKey])
            toggleOpen(item.parentKey)
        highlightKey = key
        _flashKey = key
        _flashTimer.restart()
        Qt.callLater(function() {
            var again = _rowOf(key)
            if (again >= 0)
                _list.positionViewAtIndex(again, ListView.Contain)
        })
        return true
    }

    Timer {
        id: _flashTimer
        interval: 600
        onTriggered: _tree._flashKey = ""
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
        var under = showGroups ? parentIndent : 0
        if (kind === "parent")
            return Style.dp(under)
        return Style.dp(under + childIndent)
    }

    // The row box's left edge and width in a row "total" wide.
    function boxWidth(kind, total) {
        var room = Math.max(0, total - rowIndent(kind))
        if (kind === "group")
            return room
        var pct = kind === "parent" ? parentWidthPct : childWidthPct
        return Math.round(room * Math.max(1, Math.min(100, pct)) / 100)
    }

    function boxX(kind, total) {
        var room = Math.max(0, total - rowIndent(kind))
        var align = kind === "group" ? "left" : (kind === "parent" ? parentAlign : childAlign)
        var spare = room - boxWidth(kind, total)
        if (align === "center")
            return rowIndent(kind) + Math.round(spare / 2)
        if (align === "right")
            return rowIndent(kind) + spare
        return rowIndent(kind)
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
        interactive: _tree.ownScroll
        ScrollBar.vertical: ScrollBar {
            objectName: _tree.namePrefix + "ScrollBar"
            visible: _tree.ownScroll
            policy: _tree.ownScroll ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
        }

        MouseArea {
            z: -1
            anchors.fill: parent
            acceptedButtons: Qt.RightButton
            enabled: !_tree.readOnly
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
            // A group the page keeps in place: no drag, nothing dropped into it.
            readonly property bool fixedGroup: !!model.fixedGroup
            // Live value of a parent row (only with liveDecoration).
            readonly property bool liveOn: _tree.liveDecoration && _tree.liveState !== null
                                           && rowKind === "parent" && (model.liveIndex === undefined ? -1 : model.liveIndex) >= 0
            readonly property int liveStamp: liveOn ? _tree.liveState.stamp : -1
            readonly property string liveKind: (liveOn && liveStamp >= 0) ? _tree.liveState.kindAt(model.liveIndex) : ""
            readonly property real liveValue: (liveOn && liveStamp >= 0) ? _tree.liveState.valueAt(model.liveIndex) : 0
            readonly property bool ledOn: _tree.liveLeds && (liveKind === "button" || liveKind === "hat") && liveValue > 0.5

            readonly property bool shown: _tree._rowVisible(rowKind, groupKey, parentKey)
            width: _list.width - Style.dp(16)
            readonly property int rowGap: rowKind === "group" ? 0 : Style.dp(_tree.groupInside)
            // Space between groups sits above each group row after the first.
            readonly property int groupTop: (rowKind === "group" && index > 0) ? Style.dp(_tree.groupSpacing) : 0
            readonly property int boxX: _tree.boxX(rowKind, width)
            readonly property int boxW: _tree.boxWidth(rowKind, width)
            readonly property int rowMin: Style.dp(rowKind === "group" ? 40 : (rowKind === "parent" ? _tree.parentHeight : _tree.childHeight))
            readonly property int rowPadY: _tree.rowTop(rowKind) + _tree.rowBottom(rowKind)
            readonly property int rowNeed: _line.implicitHeight + rowPadY
            readonly property int rowBody: Math.max(rowMin, rowNeed)
            height: shown ? implicitHeight : 0
            visible: shown
            clip: true
            implicitHeight: shown ? (groupTop + rowBody + rowGap + Style.dp(_tree.rowSpacing)) : 0
            color: "transparent"
            border.width: 0

            Rectangle {
                x: _row.boxX
                y: _row.groupTop
                width: _row.boxW
                height: _row.rowBody
                color: {
                    var chosen = (_tree.picked || []).indexOf(key) >= 0
                    if (_row.ledOn)
                        return Qt.rgba(_tree.colorLive.r, _tree.colorLive.g, _tree.colorLive.b, chosen ? 0.55 : 0.28)
                    return chosen ? _tree.colorSelected : (rowKind === "group" ? _tree.colorGroup : (rowKind === "parent" ? _tree.colorParent : _tree.colorChild))
                }
                border.color: _tree._flashKey === key ? _tree.colorLive : ((_tree.picked || []).indexOf(key) >= 0 ? _tree.colorSelectBorder : _tree.colorBorder)
                border.width: Style.dp(_tree._flashKey === key ? 2 : 1)
                radius: Style.dp(rowKind === "group" ? _tree.groupRadius : (rowKind === "parent" ? _tree.parentRadius : _tree.childRadius))

                // An axis's live bar along the bottom of its row.
                Rectangle {
                    visible: _tree.liveBars && _row.liveKind === "axis"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: Style.dp(1)
                    height: Style.dp(5)
                    color: _tree.colorBorder
                    Rectangle {
                        width: Math.max(0, Math.min(parent.width, parent.width * ((_row.liveValue + 1.0) * 0.5)))
                        height: parent.height
                        color: _tree.colorLive
                    }
                }
            }

            RowLayout {
                id: _line
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: _row.boxX + _tree.rowLeft(rowKind)
                anchors.rightMargin: _row.width - _row.boxX - _row.boxW + _tree.rowRight(rowKind)
                anchors.topMargin: _row.groupTop + _tree.rowTop(rowKind)
                height: Math.max(implicitHeight, _row.rowMin - _row.rowPadY)
                spacing: Style.dp(6)

                Label {
                    id: _caret
                    visible: _tree._hasList(rowKind, childCount, _row.extraWriters)
                    text: (rowKind === "group" ? (_tree.collapsed || {})[groupKey] : !(_tree.opened || {})[key]) ? "▸" : "▾"
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
                    objectName: "rowGrip"
                    visible: (rowKind === "parent" || rowKind === "group") && !_row.fixedGroup && !_tree.readOnly
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
                        enabled: !_tree.locked && !_tree.readOnly
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
                // Can't be sent (D-05-CANT-SEND): the action row, and its
                // input row so a closed row is still found; the tooltip
                // says why.
                Label {
                    id: _cantSend
                    objectName: "cantSendMark"
                    readonly property string why: _row.model.cantSend || ""
                    visible: why.length > 0 && (rowKind === "child" || rowKind === "parent")
                    text: "⚠"
                    color: Style.danger
                    font.bold: true
                    font.pixelSize: Style.dp(rowKind === "parent" ? _tree.parentFont : _tree.childFont)
                    Layout.alignment: Qt.AlignVCenter
                    HoverHandler { id: _cantHover }
                    ToolTip {
                        objectName: "cantSendTip"
                        visible: _cantHover.hovered
                        text: _cantSend.why
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: Style.dp(2)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.dp(8)
                        Label {
                            objectName: "rowName"
                            text: title
                            color: _tree.colorText
                            font.bold: (rowKind === "child" || rowKind === "feedback") ? false : _tree.parentBold
                            font.pixelSize: Style.dp(rowKind === "group" ? _tree.groupFont : (rowKind === "parent" ? _tree.parentFont : _tree.childFont))
                            elide: Text.ElideRight
                            Layout.fillWidth: !_actionSummary.visible
                            Layout.maximumWidth: _actionSummary.visible ? implicitWidth : -1
                            HoverHandler { id: _nameHover }
                            ToolTip {
                                visible: _nameHover.hovered && rowKind === "parent" && userName.length > 0
                                text: systemName
                                x: _nameHover.point.position.x - width / 2
                                y: _nameHover.point.position.y - height - Style.dp(8)
                            }
                        }
                        // What is bound here in the shown mode (05 S142):
                        // the rest of the row, cut with "…", all on hover.
                        Label {
                            id: _actionSummary
                            objectName: "actionSummary"
                            text: _row.model.actionSummary || ""
                            visible: _tree.showActionSummary && rowKind === "parent" && text.length > 0
                            color: _tree.colorMuted
                            font.pixelSize: Style.dp(_tree.summaryFont)
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            PointerTip {
                                objectName: "actionSummaryTip"
                                text: _actionSummary.text
                                show: _actionSummary.visible
                            }
                        }
                    }
                    // The wire label: an action that can't be sent is red,
                    // with the reason as its tooltip (D-05-CANT-SEND).
                    Label {
                        id: _wire
                        readonly property bool cantSend: rowKind === "child" && _cantSend.why.length > 0
                        visible: _tree.showSummary && subtitle.length > 0 && rowKind !== "writer"
                        text: subtitle
                        color: cantSend ? Style.danger : (rowKind === "child" ? _tree.colorActionTarget : _tree.colorMuted)
                        font.pixelSize: Style.dp(rowKind === "child" ? _tree.targetFont : _tree.summaryFont)
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        Layout.bottomMargin: visible ? Style.dp(4) : 0
                        HoverHandler { id: _wireHover; enabled: _wire.cantSend }
                        ToolTip {
                            objectName: "wireTip"
                            visible: _wireHover.hovered && _wire.cantSend
                            text: _wire.cantSend ? _cantSend.why : ""
                        }
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
                anchors.topMargin: _row.groupTop
                anchors.bottomMargin: _row.rowGap
                z: 4
                enabled: !_tree.locked && !_tree.readOnly && (rowKind === "parent" || rowKind === "group") && !_row.fixedGroup
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
                anchors.topMargin: _row.groupTop
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
                    if (_tree.readOnly) {
                        // View only: a click selects the input (an action
                        // line selects its input); no menus, no pane.
                        if (mouse.button !== Qt.LeftButton)
                            return
                        if (rowKind === "parent")
                            _tree.select(key, mouse.modifiers & Qt.ShiftModifier)
                        else if ((rowKind === "child" || rowKind === "writer") && parentKey.length > 0)
                            _tree.select(parentKey, mouse.modifiers & Qt.ShiftModifier)
                        else if (rowKind === "group")
                            _tree.toggleGroup(groupKey)
                        return
                    }
                    if (mouse.button === Qt.RightButton) {
                        if (rowKind === "parent") {
                            if (_tree.picked.indexOf(key) < 0)
                                _tree.select(key, false)
                            _tree.parentMenu(key, title, userName, groupName, _row, mouse.x, mouse.y)
                        } else if (rowKind === "group" && groupName.length > 0) {
                            _tree.groupMenu(groupName, _row, mouse.x, mouse.y)
                        } else if (rowKind === "feedback") {
                            _tree.feedbackMenu(key, title, !!_row.model.enabled, _row, mouse.x, mouse.y)
                        } else if (rowKind === "child" && !_tree.locked) {
                            _tree.actionMenu(parentKey, sequenceIndex, title, _row, mouse.x, mouse.y)
                        } else {
                            _tree.pageMenu(_row, mouse.x, mouse.y)
                        }
                        return
                    }
                    if (rowKind === "parent") {
                        _tree.select(key, mouse.modifiers & Qt.ShiftModifier)
                        _tree.parentClicked(key, title, !!(mouse.modifiers & Qt.ShiftModifier))
                    } else if (rowKind === "child")
                        _tree.actionClicked(parentKey, sequenceIndex, title)
                    else if (rowKind === "feedback")
                        _tree.feedbackClicked(key, title)
                    else if (rowKind === "group")
                        _tree.toggleGroup(groupKey)
                }
            }
        }
    }

    Component.onCompleted: {
        picked = []
        opened = {}
        collapsed = {}
    }
}

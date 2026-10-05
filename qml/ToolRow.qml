// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.Menus
import Gremlin.Style

// One of a window's tool rows: "top" (under the menus), "bottom", or a side
// row, "left" or "right" (between the top and bottom rows; its tabs read up
// the left one and down the right one). It holds the tabs of the tools on
// it. An open tool's tab takes its panel's color and has no line on the side
// facing the map, where its panel (ToolPane) joins it; a closed one is an
// outline. What each tool does, and where its tab sits, is the ToolDock's
// (`dock`); see there for the rules. A tab can be dragged along its row or
// onto another row (unlocked); the row it would land on lights up; let go
// off every row, its panel floats there. Its right-click menu floats or
// docks it. A floating tool's tab stays on its row (it shows and hides the
// panel) with a small floating mark. Places along a row are kept as shares
// of its length.
//
//   ToolRow { dock: _tools; side: "top" }
Item {
    id: _row

    property var dock: null
    property string side: "bottom"
    readonly property bool vertical: side === "left" || side === "right"
    readonly property real gap: Style.dp(6)
    readonly property real grid: Style.dp(8)
    // A tab is being dragged here from another row, or along this one.
    readonly property bool dropTarget: !!dock && dock.dragging.length > 0 && dock.dropSide === side
    // The row's length (along its tabs).
    readonly property real span: vertical ? _buttons.height : _buttons.width

    implicitHeight: vertical ? 0 : Style.dp(30)
    implicitWidth: vertical ? Style.dp(30) : 0
    // A tab dragged off this row is drawn over the map.
    z: (dock && dock.dragging.length && dock.sideOf(dock.dragging) === side) ? 50 : 0

    Component.onCompleted: _register()
    onDockChanged: _register()
    onSideChanged: _register()

    function _register() {
        if (!dock)
            return
        var next = {}
        for (var k in dock.rows)
            next[k] = dock.rows[k]
        next[side] = _row
        dock.rows = next
        relayout()
    }

    // A tab's place along the row, and its length there.
    function _at(b) { return vertical ? b.y : b.x }
    function _len(b) { return vertical ? b.height : b.width }
    function _place(b, v) {
        if (vertical)
            b.y = v
        else
            b.x = v
    }

    // Where a tool's tab sits: its start along the row, or -1 (for tests).
    function placeOf(id) {
        var b = _button(id)
        return b ? _at(b) : -1
    }

    function buttonLength(id) {
        var b = _button(id)
        return b ? _len(b) : 0
    }

    function _button(id) {
        for (var i = 0; i < _rep.count; i++) {
            var b = _rep.itemAt(i)
            if (b && b.modelData === id)
                return b
        }
        return null
    }

    function relayout() {
        Qt.callLater(_layout)
    }

    // Each tab's middle as a share of the row's length (the dock keeps
    // these once one tab is moved).
    function shares() {
        var out = {}
        if (!(span > 0))
            return out
        for (var i = 0; i < _rep.count; i++) {
            var b = _rep.itemAt(i)
            if (b)
                out[b.modelData] = (_at(b) + _len(b) / 2) / span
        }
        return out
    }

    // A tab let go here with its start at `at`: snapped, then the nearest
    // free spot among this row's other tabs, as a share.
    function shareAt(id, at) {
        var length = buttonLength(id)
        if (!(length > 0) && dock) {
            for (var k in dock.rows) {
                if (dock.rows[k] && dock.rows[k] !== _row)
                    length = Math.max(length, dock.rows[k].buttonLength(id))
            }
        }
        var others = []
        for (var j = 0; j < _rep.count; j++) {
            var ob = _rep.itemAt(j)
            if (ob && ob.modelData !== id)
                others.push({ x: _at(ob), w: _len(ob) })
        }
        var start = _freeSpot(_snap(at, length), length, others)
        return (start + length / 2) / Math.max(1, span)
    }

    // Places the tabs: together and centred, or each where it was put.
    function _layout() {
        var w = span
        if (!(w > 0) || !dock)
            return
        var ids = dock.order(side)
        var pos = dock._pos || {}
        if (!Object.keys(pos).length) {
            var total = 0
            var shown = []
            for (var i = 0; i < ids.length; i++) {
                var b = _button(ids[i])
                if (!b)
                    continue
                shown.push(b)
                total += _len(b)
            }
            total += _row.gap * Math.max(0, shown.length - 1)
            var x = Math.round((w - total) / 2)
            for (var j = 0; j < shown.length; j++) {
                _place(shown[j], x)
                x += _len(shown[j]) + _row.gap
            }
            dock.layoutRev++
            return
        }
        var placed = []
        for (var k = 0; k < ids.length; k++) {
            var bk = _button(ids[k])
            if (!bk)
                continue
            var at = pos[ids[k]]
            var want = at === undefined ? (w - _len(bk)) / 2 : at * w - _len(bk) / 2
            // One not placed yet (new) goes to the free spot nearest the middle.
            _place(bk, Math.round(_freeSpot(want, _len(bk), placed)))
            placed.push({ x: _at(bk), w: _len(bk) })
        }
        dock.layoutRev++
    }

    // The start nearest `want` where a tab this long fits on the row
    // without covering one of `others` ([{x, w}], along the row).
    function _freeSpot(want, length, others) {
        var lo = _row.gap
        var hi = Math.max(lo, span - _row.gap - length)
        function fits(x) {
            if (x < lo - 0.5 || x > hi + 0.5)
                return false
            for (var i = 0; i < others.length; i++) {
                var o = others[i]
                if (x < o.x + o.w + _row.gap && x + length + _row.gap > o.x)
                    return false
            }
            return true
        }
        var x = Math.max(lo, Math.min(hi, want))
        if (fits(x))
            return x
        var best = x
        var bestD = Infinity
        var tries = [lo, hi]
        for (var j = 0; j < others.length; j++) {
            tries.push(others[j].x - _row.gap - length)
            tries.push(others[j].x + others[j].w + _row.gap)
        }
        for (var t = 0; t < tries.length; t++) {
            var c = tries[t]
            if (fits(c) && Math.abs(c - want) < bestD) {
                best = c
                bestD = Math.abs(c - want)
            }
        }
        return best
    }

    // Snapping: the row's ends and middle when close, else a small grid.
    function _snap(x, length) {
        var near = Style.dp(10)
        var spots = [_row.gap, (span - length) / 2, span - _row.gap - length]
        for (var i = 0; i < spots.length; i++) {
            if (Math.abs(x - spots[i]) <= near)
                return spots[i]
        }
        return Math.round(x / _row.grid) * _row.grid
    }

    Rectangle {
        anchors.fill: parent
        color: Style.bgRaised
        // The line on the side facing the map.
        Rectangle {
            x: _row.side === "left" ? parent.width - 1 : 0
            y: _row.side === "top" ? parent.height - 1 : 0
            width: _row.vertical ? 1 : parent.width
            height: _row.vertical ? parent.height : 1
            color: Style.line
        }
        // Lit while a tab would land here.
        Rectangle {
            anchors.fill: parent
            visible: _row.dropTarget
            color: Style.clear
            border.color: Style.accent
            border.width: Style.dp(2)
        }
    }

    Item {
        id: _buttons
        anchors.fill: parent
        onWidthChanged: _row.relayout()
        onHeightChanged: _row.relayout()

        Repeater {
            id: _rep
            model: { _row.dock ? _row.dock.rev : 0; return _row.dock ? _row.dock.order(_row.side) : [] }
            delegate: Rectangle {
                id: _btn
                required property string modelData
                required property int index
                readonly property var dock: _row.dock
                readonly property var tool: dock ? dock.tool(modelData) : null
                readonly property bool open: { dock.rev; return dock.isOpen(modelData) }
                readonly property bool pinned: { dock.rev; return dock.isPinned(modelData) }
                readonly property bool locked: { dock.rev; return dock.isLocked(modelData) }
                readonly property bool usableNow: { dock.rev; return dock.isUsable(modelData) }
                objectName: "tool:" + modelData
                // A tab: from near the row's outer edge to its inner edge
                // (the side facing the map, where an open tool's panel joins).
                readonly property string side: _row.side
                // Joined to its panel (showing); open without one: lit.
                readonly property bool floating: { dock.rev; return dock.isFloating(modelData) }
                readonly property bool joined: open && !floating && !!_row.dock.paneShown[modelData]
                readonly property color edge: open ? Style.lineStrong : Style.line
                readonly property real lengthWanted: _inner.implicitWidth + Style.dp(14)
                width: _row.vertical ? _row.width - Style.dp(4) : lengthWanted
                height: _row.vertical ? lengthWanted : _row.height - Style.dp(4)
                x: _row.side === "left" ? Style.dp(4) : 0
                y: _row.side === "top" ? Style.dp(4) : 0
                onWidthChanged: _row.relayout()
                onHeightChanged: _row.relayout()
                onXChanged: if (_row.dock) _row.dock.layoutRev++
                onYChanged: if (_row.dock) _row.dock.layoutRev++
                Component.onCompleted: _row.relayout()
                opacity: usableNow ? 1 : 0.45
                color: joined ? _row.dock.paneColor(modelData)
                       : open ? Style.bgSelected
                       : (_main.containsMouse && usableNow ? Style.bgCard : Style.clear)

                // Its outer edge (accent while open), its two sides, and its
                // inner edge only while not joined.
                component Edge: Rectangle {
                    // "top", "bottom", "left" or "right" of the tab.
                    required property string at
                    x: at === "right" ? _btn.width - 1 : 0
                    y: at === "bottom" ? _btn.height - 1 : 0
                    width: (at === "left" || at === "right") ? 1 : _btn.width
                    height: (at === "top" || at === "bottom") ? 1 : _btn.height
                }
                readonly property string outer: side
                readonly property string inner: ({ top: "bottom", bottom: "top", left: "right", right: "left" })[side]
                readonly property var sides: _row.vertical ? ["top", "bottom"] : ["left", "right"]
                Edge { at: _btn.outer; color: _btn.open ? Style.accent : _btn.edge }
                Edge { at: _btn.sides[0]; color: _btn.edge }
                Edge { at: _btn.sides[1]; color: _btn.edge }
                Edge { at: _btn.inner; color: _btn.edge; visible: !_btn.joined }

                // How far it is being dragged (an unlocked tab).
                property real dragDx: 0
                property real dragDy: 0
                transform: Translate { x: _btn.dragDx; y: _btn.dragDy }
                z: _main.pressed ? 2 : 1

                // Its name, pin and lock; turned on a side row (reading up
                // the left row, down the right one).
                Item {
                    anchors.centerIn: parent
                    width: _row.vertical ? _inner.implicitHeight : _inner.implicitWidth
                    height: _row.vertical ? _inner.implicitWidth : _inner.implicitHeight
                    Row {
                        id: _inner
                        anchors.centerIn: parent
                        spacing: Style.dp(6)
                        rotation: _row.side === "left" ? -90 : (_row.side === "right" ? 90 : 0)
                        Label {
                            anchors.verticalCenter: parent.verticalCenter
                            text: _btn.tool ? _btn.tool.label : _btn.modelData
                            font.pixelSize: Style.dp(12)
                            color: _btn.open ? Style.fg : Style.fgMuted
                        }
                        // Floating: two small frames, one over the other.
                        Item {
                            objectName: "floatMark"
                            visible: _btn.floating
                            anchors.verticalCenter: parent.verticalCenter
                            width: Style.dp(11)
                            height: Style.dp(10)
                            Rectangle {
                                width: Style.dp(8)
                                height: Style.dp(6)
                                color: Style.clear
                                border.color: Style.fgMuted
                                border.width: 1
                            }
                            Rectangle {
                                x: Style.dp(3)
                                y: Style.dp(4)
                                width: Style.dp(8)
                                height: Style.dp(6)
                                color: _btn.color.a > 0 ? _btn.color : Style.bgRaised
                                border.color: Style.accent
                                border.width: 1
                            }
                        }
                        // Pin: stays open when the map is clicked.
                        Label {
                            id: _pin
                            anchors.verticalCenter: parent.verticalCenter
                            font.family: Style.iconFont
                            font.pixelSize: Style.dp(11)
                            text: _btn.pinned ? "\uF4EC" : "\uF4EB"
                            color: _btn.pinned ? Style.accent : (_pinArea.containsMouse ? Style.fg : Style.fgMuted)
                            MouseArea {
                                id: _pinArea
                                anchors.fill: parent
                                anchors.margins: -Style.dp(3)
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: _btn.dock.setPinned(_btn.modelData, !_btn.pinned)
                            }
                            ToolTip.visible: _pinArea.containsMouse
                            ToolTip.delay: 600
                            ToolTip.text: _btn.pinned ? "Unpin: hides when you click the map" : "Pin: stays open when you click the map"
                        }
                        // Lock: can't be dragged or resized.
                        Label {
                            id: _lock
                            anchors.verticalCenter: parent.verticalCenter
                            font.family: Style.iconFont
                            font.pixelSize: Style.dp(11)
                            text: _btn.locked ? "\uF47A" : "\uF600"
                            color: _btn.locked ? Style.accent : (_lockArea.containsMouse ? Style.fg : Style.fgMuted)
                            MouseArea {
                                id: _lockArea
                                anchors.fill: parent
                                anchors.margins: -Style.dp(3)
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: _btn.dock.setLocked(_btn.modelData, !_btn.locked)
                            }
                            ToolTip.visible: _lockArea.containsMouse
                            ToolTip.delay: 600
                            ToolTip.text: _btn.locked ? "Unlock: can be moved and resized" : "Lock: can't be moved or resized"
                        }
                    }
                }

                // Click: open or hide. Drag (unlocked): move along the row or
                // onto another one.
                // Float and Dock (its panel over the map, or back on this row).
                ThemedMenu {
                    id: _tabMenu
                    ThemedMenuItem {
                        text: "Float"
                        enabled: _btn.dock.canFloat(_btn.modelData) && !_btn.floating && !_btn.locked
                        onTriggered: _btn.dock.setFloating(_btn.modelData, true)
                    }
                    ThemedMenuItem {
                        text: "Dock"
                        enabled: _btn.floating && !_btn.locked
                        onTriggered: _btn.dock.setFloating(_btn.modelData, false)
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    z: -2
                    acceptedButtons: Qt.RightButton
                    onClicked: (m) => _tabMenu.popup()
                }
                MouseArea {
                    id: _main
                    anchors.fill: parent
                    z: -1
                    hoverEnabled: true
                    enabled: _btn.usableNow
                    // A hand, as over the pool's chips; closed while dragging it.
                    cursorShape: pressed && _moved ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    property point _start: Qt.point(0, 0)
                    property bool _moved: false
                    onPressed: (m) => {
                        _start = mapToItem(_buttons, m.x, m.y)
                        _moved = false
                    }
                    onPositionChanged: (m) => {
                        if (!pressed || _btn.locked)
                            return
                        var p = mapToItem(_buttons, m.x, m.y)
                        var dx = p.x - _start.x
                        var dy = p.y - _start.y
                        if (Math.abs(dx) > Style.dp(4) || Math.abs(dy) > Style.dp(4))
                            _moved = true
                        if (!_moved)
                            return
                        _btn.dragDx = dx
                        _btn.dragDy = dy
                        var s = mapToItem(null, m.x, m.y)
                        _btn.dock.dragging = _btn.modelData
                        // "" off every row: let go there, its panel floats.
                        _btn.dock.dropSide = _btn.dock.sideAt(s.x, s.y)
                    }
                    onReleased: (m) => {
                        var dock = _btn.dock
                        if (!_moved) {
                            dock.toggle(_btn.modelData)
                            return
                        }
                        var id = _btn.modelData
                        // Let go off every row: its panel floats there.
                        if (!dock.dropSide.length && dock.canFloat(id) && dock.floatArea) {
                            var f = dock.floatArea.mapFromItem(_buttons, _btn.x + _btn.dragDx, _btn.y + _btn.dragDy)
                            _btn.dragDx = 0
                            _btn.dragDy = 0
                            dock.dragging = ""
                            Qt.callLater(function() { dock.floatAt(id, f.x, f.y) })
                            return
                        }
                        // Where it was let go: on this row or another, along
                        // that row, snapped, then the nearest free spot there.
                        var target = dock.dropSide || _row.side
                        var row = (dock.rows || {})[target] || _row
                        var p = row.mapFromItem(_buttons, _btn.x + _btn.dragDx, _btn.y + _btn.dragDy)
                        var along = row.vertical ? p.y : p.x
                        _btn.dragDx = 0
                        _btn.dragDy = 0
                        dock.dragging = ""
                        dock.dropSide = ""
                        // After this handler: a tab put on another row leaves
                        // this one (its delegate goes).
                        Qt.callLater(function() { dock.dropAt(id, along, target) })
                    }
                    onCanceled: {
                        _btn.dragDx = 0
                        _btn.dragDy = 0
                        _btn.dock.dragging = ""
                        _btn.dock.dropSide = ""
                    }
                }
                ToolTip.visible: _main.containsMouse && !!(_btn.tool && _btn.tool.tip)
                ToolTip.delay: 700
                ToolTip.text: _btn.tool && _btn.tool.tip ? _btn.tool.tip : ""
            }
        }
    }
}

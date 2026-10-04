// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.Style

// One of a window's tool rows ("top", under the menus, or "bottom"): the
// tabs of the tools on it. An open tool's tab takes its panel's color and
// has no line on the side facing the map, where its panel (ToolPane) joins
// it; a closed one is an outline. What each tool does, and where its button
// sits, is the ToolDock's (`dock`); see there for the rules. A button can be
// dragged along the row or onto the other row (unlocked); the row it would
// land on lights up.
//
//   ToolRow { dock: _tools; side: "top" }
Item {
    id: _row

    property var dock: null
    property string side: "bottom"
    readonly property real gap: Style.dp(6)
    readonly property real grid: Style.dp(8)
    // A button is being dragged here from the other row, or along this one.
    readonly property bool dropTarget: !!dock && dock.dragging.length > 0 && dock.dropSide === side

    implicitHeight: Style.dp(30)
    // A button dragged off this row is drawn over the map.
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

    // Where a tool's button sits: its left edge, or -1 (for tests).
    function placeOf(id) {
        var b = _button(id)
        return b ? b.x : -1
    }

    function buttonWidth(id) {
        var b = _button(id)
        return b ? b.width : 0
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

    // Each button's middle as a share of the row's width (the dock keeps
    // these once one button is moved).
    function shares() {
        var out = {}
        var w = _buttons.width
        if (!(w > 0))
            return out
        for (var i = 0; i < _rep.count; i++) {
            var b = _rep.itemAt(i)
            if (b)
                out[b.modelData] = (b.x + b.width / 2) / w
        }
        return out
    }

    // A button let go here with its left edge at x: snapped, then the
    // nearest free spot among this row's other buttons, as a share.
    function shareAt(id, x) {
        var width = buttonWidth(id)
        if (!(width > 0) && dock) {
            for (var k in dock.rows) {
                if (dock.rows[k] && dock.rows[k] !== _row)
                    width = Math.max(width, dock.rows[k].buttonWidth(id))
            }
        }
        var others = []
        for (var j = 0; j < _rep.count; j++) {
            var ob = _rep.itemAt(j)
            if (ob && ob.modelData !== id)
                others.push({ x: ob.x, w: ob.width })
        }
        var left = _freeSpot(_snap(x, width), width, others)
        return (left + width / 2) / Math.max(1, _buttons.width)
    }

    // Places the buttons: together and centred, or each where it was put.
    function _layout() {
        var w = _buttons.width
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
                total += b.width
            }
            total += _row.gap * Math.max(0, shown.length - 1)
            var x = Math.round((w - total) / 2)
            for (var j = 0; j < shown.length; j++) {
                shown[j].x = x
                x += shown[j].width + _row.gap
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
            var want = at === undefined ? (w - bk.width) / 2 : at * w - bk.width / 2
            // One not placed yet (new) goes to the free spot nearest the middle.
            bk.x = Math.round(_freeSpot(want, bk.width, placed))
            placed.push({ x: bk.x, w: bk.width })
        }
        dock.layoutRev++
    }

    // The left edge nearest `want` where a button this wide fits on the row
    // without covering one of `others` ([{x, w}]).
    function _freeSpot(want, width, others) {
        var lo = _row.gap
        var hi = Math.max(lo, _buttons.width - _row.gap - width)
        function fits(x) {
            if (x < lo - 0.5 || x > hi + 0.5)
                return false
            for (var i = 0; i < others.length; i++) {
                var o = others[i]
                if (x < o.x + o.w + _row.gap && x + width + _row.gap > o.x)
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
            tries.push(others[j].x - _row.gap - width)
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

    // Snapping: the row's edges and middle when close, else a small grid.
    function _snap(x, width) {
        var near = Style.dp(10)
        var spots = [_row.gap, (_buttons.width - width) / 2, _buttons.width - _row.gap - width]
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
            width: parent.width
            height: 1
            y: _row.side === "top" ? parent.height - 1 : 0
            color: Style.line
        }
        // Lit while a button would land here.
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
                readonly property bool atTop: _row.side === "top"
                // Joined to its panel (showing); open without one: lit.
                readonly property bool joined: open && !!_row.dock.paneShown[modelData]
                readonly property color edge: open ? Style.lineStrong : Style.line
                width: _inner.implicitWidth + Style.dp(14)
                height: _row.height - Style.dp(4)
                y: atTop ? Style.dp(4) : 0
                onWidthChanged: _row.relayout()
                onXChanged: if (_row.dock) _row.dock.layoutRev++
                Component.onCompleted: _row.relayout()
                opacity: usableNow ? 1 : 0.45
                color: joined ? _row.dock.paneColor(modelData)
                       : open ? Style.bgSelected
                       : (_main.containsMouse && usableNow ? Style.bgCard : Style.clear)
                // Its sides and outer edge; its inner edge only while closed.
                Rectangle { width: 1; height: parent.height; color: _btn.edge }
                Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: _btn.edge }
                Rectangle {
                    width: parent.width
                    height: 1
                    y: _btn.atTop ? 0 : parent.height - 1
                    color: _btn.open ? Style.accent : _btn.edge
                }
                Rectangle {
                    visible: !_btn.joined
                    width: parent.width
                    height: 1
                    y: _btn.atTop ? parent.height - 1 : 0
                    color: _btn.edge
                }
                // How far it is being dragged (an unlocked button).
                property real dragDx: 0
                property real dragDy: 0
                transform: Translate { x: _btn.dragDx; y: _btn.dragDy }
                z: _main.pressed ? 2 : 1

                Row {
                    id: _inner
                    anchors.centerIn: parent
                    spacing: Style.dp(6)
                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: _btn.tool ? _btn.tool.label : _btn.modelData
                        font.pixelSize: Style.dp(12)
                        color: _btn.open ? Style.fg : Style.fgMuted
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

                // Click: open or hide. Drag (unlocked): move along the row or
                // onto the other one.
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
                        _btn.dock.dropSide = _btn.dock.sideAt(s.x, s.y) || _row.side
                    }
                    onReleased: (m) => {
                        var dock = _btn.dock
                        if (!_moved) {
                            dock.toggle(_btn.modelData)
                            return
                        }
                        // Where it was let go: on this row or the other,
                        // snapped, then the nearest free spot there.
                        var target = dock.dropSide || _row.side
                        var row = (dock.rows || {})[target] || _row
                        var left = row.mapFromItem(_buttons, _btn.x + _btn.dragDx, 0).x
                        _btn.dragDx = 0
                        _btn.dragDy = 0
                        dock.dragging = ""
                        dock.dropSide = ""
                        // After this handler: a button put on the other row
                        // leaves this one (its delegate goes).
                        var id = _btn.modelData
                        Qt.callLater(function() { dock.dropAt(id, left, target) })
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

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.UI
import Gremlin.Style

// A window's tool row: one button per tool, centred. Every tool behaves the
// same way:
//   - its button opens it, and hides it again;
//   - pinned (the pin on its button), it stays open when the map is clicked;
//     unpinned, it hides when the map is clicked or another tool opens;
//   - locked (the lock on its button), it can't be dragged or resized, nor
//     its button moved; unlocked, the button can be dragged to any place on
//     the row: it snaps to the edges, the middle and a small grid, and goes
//     to the nearest free spot rather than onto another button. Until one
//     is moved (and after resetPlaces()) the buttons sit together, centred.
// What is open, pinned and locked, and the order, are kept with the window
// layout under `name`. Adding a tool is one more entry in `tools`.
//
//   ToolRow { name: "button-map"; tools: [{ id: "chips", label: "Chips" }] }
//   row.isOpen("chips"), row.setOpen("chips", true), row.mapClicked()
Item {
    id: _row

    property string name: ""
    // [{ id, label, tip }] in their first order.
    property var tools: []
    // Starting state for a tool never used: { id: { open, pinned, locked } }.
    property var defaults: ({})
    // Tools that can't be used now (e.g. only while editing): id -> false.
    property var usable: ({})

    // id -> { open, pinned, locked }, and the ids in the row's order.
    property var _state: ({})
    property var _order: []
    // Where each button sits once one has been moved: id -> its middle as a
    // share (0..1) of the row's width. Empty: all together, centred.
    property var _pos: ({})
    readonly property real gap: Style.dp(6)
    readonly property real grid: Style.dp(8)
    // Bumped on every change: bindings on the getters follow it.
    property int rev: 0

    signal toolChanged(string id)

    implicitHeight: Style.dp(30)

    WindowPlacement { id: _store }

    Component.onCompleted: _load()
    onToolsChanged: _load()

    function _entry(id) {
        var s = _state[id]
        if (!s) {
            var d = defaults[id] || {}
            s = { open: !!d.open, pinned: !!d.pinned, locked: !!d.locked }
            _state[id] = s
        }
        return s
    }

    function _load() {
        var saved = {}
        try {
            saved = JSON.parse(name.length ? _store.toolRowState(name) : "{}") || {}
        } catch (e) {
            saved = {}
        }
        var items = saved.items || {}
        _state = {}
        for (var i = 0; i < tools.length; i++) {
            var id = tools[i].id
            var s = _entry(id)
            var keep = items[id]
            if (keep) {
                s.pinned = !!keep.pinned
                s.locked = !!keep.locked
                // Only a pinned tool reopens in a new session.
                s.open = !!keep.open && s.pinned
            }
        }
        // The saved order, then any tool it doesn't have yet.
        var order = (saved.order || []).filter(function(t) { return _has(t) })
        for (i = 0; i < tools.length; i++) {
            if (order.indexOf(tools[i].id) < 0)
                order.push(tools[i].id)
        }
        _order = order
        var pos = saved.pos || {}
        _pos = {}
        for (var key in pos) {
            if (_has(key) && pos[key] >= 0 && pos[key] <= 1)
                _pos[key] = pos[key]
        }
        rev++
        _relayout()
    }

    function _has(id) {
        for (var i = 0; i < tools.length; i++) {
            if (tools[i].id === id)
                return true
        }
        return false
    }

    function _save() {
        rev++
        if (!name.length)
            return
        var items = {}
        for (var i = 0; i < tools.length; i++) {
            var s = _entry(tools[i].id)
            items[tools[i].id] = { open: s.open, pinned: s.pinned, locked: s.locked }
        }
        _store.saveToolRowState(name, JSON.stringify({ order: _order, items: items, pos: _pos }))
    }

    function tool(id) {
        for (var i = 0; i < tools.length; i++) {
            if (tools[i].id === id)
                return tools[i]
        }
        return null
    }

    function isUsable(id) { return usable[id] !== false }
    function isOpen(id) { rev; return _entry(id).open && isUsable(id) }
    function isPinned(id) { rev; return _entry(id).pinned }
    function isLocked(id) { rev; return _entry(id).locked }

    // Opening a tool hides the other unpinned ones.
    function setOpen(id, on) {
        var s = _entry(id)
        if (on) {
            for (var i = 0; i < tools.length; i++) {
                var other = tools[i].id
                var o = _entry(other)
                if (other !== id && o.open && !o.pinned) {
                    o.open = false
                    toolChanged(other)
                }
            }
        }
        if (s.open === !!on) {
            _save()
            return
        }
        s.open = !!on
        _save()
        toolChanged(id)
    }

    function toggle(id) { setOpen(id, !_entry(id).open) }

    function setPinned(id, on) {
        _entry(id).pinned = !!on
        _save()
        toolChanged(id)
    }

    function setLocked(id, on) {
        _entry(id).locked = !!on
        _save()
        toolChanged(id)
    }

    // A click on the map: unpinned tools hide.
    function mapClicked() {
        for (var i = 0; i < tools.length; i++) {
            var id = tools[i].id
            var s = _entry(id)
            if (s.open && !s.pinned) {
                s.open = false
                toolChanged(id)
            }
        }
        _save()
    }

    // The row's ids in order (for tests and the window).
    function order() { rev; return _order.slice() }

    // Puts a tool at another place in the row's order (the buttons sit
    // together, centred, in this order until one is moved freely).
    function moveTo(id, index) {
        if (isLocked(id))
            return
        var order = _order.slice()
        var at = order.indexOf(id)
        if (at < 0)
            return
        order.splice(at, 1)
        order.splice(Math.max(0, Math.min(index, order.length)), 0, id)
        _order = order
        _save()
        _relayout()
    }

    // Back to all together, centred (View > Reset Tool Row).
    function resetPlaces() {
        _pos = {}
        _save()
        _relayout()
    }

    // Where a tool's button sits: its left edge, or -1 (for tests).
    function placeOf(id) {
        var b = _button(id)
        return b ? b.x : -1
    }

    function _button(id) {
        for (var i = 0; i < _rep.count; i++) {
            var b = _rep.itemAt(i)
            if (b && b.modelData === id)
                return b
        }
        return null
    }

    function _relayout() {
        Qt.callLater(_layout)
    }

    // Places the buttons: together and centred, or each where it was put.
    function _layout() {
        var w = _buttons.width
        if (!(w > 0))
            return
        var ids = _order
        if (!Object.keys(_pos).length) {
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
            return
        }
        var placed = []
        for (var k = 0; k < ids.length; k++) {
            var bk = _button(ids[k])
            if (!bk)
                continue
            var at = _pos[ids[k]]
            var want = at === undefined ? (w - bk.width) / 2 : at * w - bk.width / 2
            // One not placed yet (new) goes to the free spot nearest the middle.
            bk.x = Math.round(_freeSpot(want, bk.width, placed))
            placed.push({ x: bk.x, w: bk.width })
        }
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

    // A button let go with its left edge at `x`: snapped, moved to the
    // nearest free spot, and kept (every button gets its place the first
    // time, so the others stay where they are).
    function dropAt(id, x) {
        var b = _button(id)
        if (!b || isLocked(id))
            return
        var w = _buttons.width
        if (!Object.keys(_pos).length) {
            var pos = {}
            for (var i = 0; i < _rep.count; i++) {
                var o = _rep.itemAt(i)
                if (o)
                    pos[o.modelData] = (o.x + o.width / 2) / w
            }
            _pos = pos
        }
        var others = []
        for (var j = 0; j < _rep.count; j++) {
            var ob = _rep.itemAt(j)
            if (ob && ob !== b)
                others.push({ x: ob.x, w: ob.width })
        }
        var left = _freeSpot(_snap(x, b.width), b.width, others)
        var next = {}
        for (var key in _pos)
            next[key] = _pos[key]
        next[id] = (left + b.width / 2) / w
        _pos = next
        // The order follows the places (keyboard and lists).
        var order = _order.slice()
        order.sort(function(a, c) { return (_pos[a] || 0) - (_pos[c] || 0) })
        _order = order
        _save()
        _relayout()
    }

    Rectangle {
        anchors.fill: parent
        color: Style.bgRaised
        Rectangle {
            width: parent.width
            height: 1
            color: Style.line
        }
    }

    Item {
        id: _buttons
        anchors.fill: parent
        onWidthChanged: _row._relayout()

        Repeater {
            id: _rep
            model: { _row.rev; return _row._order }
            delegate: Rectangle {
                id: _btn
                required property string modelData
                required property int index
                readonly property var tool: _row.tool(modelData)
                readonly property bool open: { _row.rev; return _row.isOpen(modelData) }
                readonly property bool pinned: { _row.rev; return _row.isPinned(modelData) }
                readonly property bool locked: { _row.rev; return _row.isLocked(modelData) }
                readonly property bool usableNow: { _row.rev; return _row.isUsable(modelData) }
                objectName: "tool:" + modelData
                width: _inner.implicitWidth + Style.dp(12)
                height: _row.height - Style.dp(6)
                y: (_row.height - height) / 2
                onWidthChanged: _row._relayout()
                Component.onCompleted: _row._relayout()
                radius: Style.dp(4)
                opacity: usableNow ? 1 : 0.45
                color: open ? Style.bgSelected : (_main.containsMouse && usableNow ? Style.bgCard : Style.clear)
                border.color: open ? Style.accent : Style.line
                border.width: 1
                // How far it is being dragged (an unlocked button).
                property real dragDx: 0
                transform: Translate { x: _btn.dragDx }
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
                        text: _btn.pinned ? "" : ""
                        color: _btn.pinned ? Style.accent : (_pinArea.containsMouse ? Style.fg : Style.fgMuted)
                        MouseArea {
                            id: _pinArea
                            anchors.fill: parent
                            anchors.margins: -Style.dp(3)
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: _row.setPinned(_btn.modelData, !_btn.pinned)
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
                        text: _btn.locked ? "" : ""
                        color: _btn.locked ? Style.accent : (_lockArea.containsMouse ? Style.fg : Style.fgMuted)
                        MouseArea {
                            id: _lockArea
                            anchors.fill: parent
                            anchors.margins: -Style.dp(3)
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: _row.setLocked(_btn.modelData, !_btn.locked)
                        }
                        ToolTip.visible: _lockArea.containsMouse
                        ToolTip.delay: 600
                        ToolTip.text: _btn.locked ? "Unlock: can be moved and resized" : "Lock: can't be moved or resized"
                    }
                }

                // Click: open or hide. Drag (unlocked): move along the row.
                MouseArea {
                    id: _main
                    anchors.fill: parent
                    z: -1
                    hoverEnabled: true
                    enabled: _btn.usableNow
                    // A hand, as over the pool's chips; closed while dragging it.
                    cursorShape: pressed && _moved ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    property real _startX: 0
                    property bool _moved: false
                    onPressed: (m) => {
                        _startX = mapToItem(_buttons, m.x, m.y).x
                        _moved = false
                    }
                    onPositionChanged: (m) => {
                        if (!pressed || _btn.locked)
                            return
                        var dx = mapToItem(_buttons, m.x, m.y).x - _startX
                        if (Math.abs(dx) > Style.dp(4))
                            _moved = true
                        if (_moved)
                            _btn.dragDx = dx
                    }
                    onReleased: (m) => {
                        if (!_moved) {
                            _row.toggle(_btn.modelData)
                            return
                        }
                        // Where it was let go: snapped, then the nearest free spot.
                        var left = _btn.x + _btn.dragDx
                        _btn.dragDx = 0
                        _row.dropAt(_btn.modelData, left)
                    }
                    onCanceled: _btn.dragDx = 0
                }
                ToolTip.visible: _main.containsMouse && !!(_btn.tool && _btn.tool.tip)
                ToolTip.delay: 700
                ToolTip.text: _btn.tool && _btn.tool.tip ? _btn.tool.tip : ""
            }
        }
    }
}

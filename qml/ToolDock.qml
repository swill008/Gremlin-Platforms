// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import Gremlin.UI
import Gremlin.Style

// A window's tools and their tool rows: what each tool's state is, and
// which row (ToolRow, "top" or "bottom") its button is on. Every tool
// behaves the same way, on either row:
//   - its button opens it, and hides it again;
//   - pinned (the pin on its button), it stays open when the map is clicked;
//     unpinned, it hides when the map is clicked or another tool opens;
//   - locked (the lock on its button), it can't be dragged or resized, nor
//     its button moved; unlocked, the button can be dragged to any place on
//     its row or onto the other row: it snaps to the edges, the middle and a
//     small grid, and goes to the nearest free spot rather than onto another
//     button. Until one is moved (and after resetPlaces()) each row's buttons
//     sit together, centred.
// A tool with a panel also has a dock, the edge its panel sits against
// ("top" or "bottom"): it follows the button to another row, and the panel
// can be dragged to the other edge on its own (dockOf / setDock).
// What is open, pinned and locked, the rows, places and docks are kept with
// the window layout under `name`. Adding a tool is one more entry in `tools`.
//
//   ToolDock { id: _tools; name: "button-map"; tools: [{ id: "chips", label: "Chips" }] }
//   ToolRow { dock: _tools; side: "top" }   ToolRow { dock: _tools; side: "bottom" }
//   _tools.isOpen("chips"), _tools.setOpen("chips", true), _tools.mapClicked()
Item {
    id: _dock

    property string name: ""
    // [{ id, label, tip }] in their first order.
    property var tools: []
    // Starting state for a tool never used: { id: { open, pinned, locked,
    // side } } (side: the row it starts on, "bottom" unless said; its panel
    // docks there too).
    property var defaults: ({})
    // Tools that can't be used now (e.g. only while editing): id -> false.
    property var usable: ({})

    // id -> { open, pinned, locked, side, dock }, and the ids in order.
    // Plain values, not bindings (_load sets them; a binding replaced would
    // be reported at start-up).
    property var _state: null
    property var _order: null
    // Where each button sits once one has been moved: id -> its middle as a
    // share (0..1) of its row's width. Empty: each row together, centred.
    property var _pos: null
    // The rows drawing the buttons, side -> row (ToolRow registers itself;
    // a plain value, not a binding, as the rows set it).
    property var rows: null
    // A button being dragged (its id), and the row it would land on.
    property string dragging: ""
    property string dropSide: ""
    // Bumped on every change: bindings on the getters follow it.
    property int rev: 0

    signal toolChanged(string id)

    visible: false

    WindowPlacement { id: _store }

    Component.onCompleted: _load()
    onToolsChanged: _load()

    function _entry(id) {
        if (!_state)
            _state = {}
        var s = _state[id]
        if (!s) {
            var d = defaults[id] || {}
            var home = _side(d.side)
            s = { open: !!d.open, pinned: !!d.pinned, locked: !!d.locked, side: home, dock: home }
            _state[id] = s
        }
        return s
    }

    function _side(v) { return v === "top" ? "top" : "bottom" }

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
                if (keep.side !== undefined) {
                    s.side = _side(keep.side)
                    s.dock = _side(keep.dock || keep.side)
                }
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
        relayout()
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
            items[tools[i].id] = { open: s.open, pinned: s.pinned, locked: s.locked, side: s.side, dock: s.dock }
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
    // The row a tool's button is on, and the edge its panel docks to.
    function sideOf(id) { rev; return _entry(id).side }
    function dockOf(id) { rev; return _entry(id).dock }

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

    // A tool's panel to the other edge on its own (its button stays).
    function setDock(id, side) {
        if (isLocked(id))
            return
        _entry(id).dock = _side(side)
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

    // The ids in order (for tests and the window), or only one row's.
    function order(side) {
        rev
        var ids = (_order || []).slice()
        if (side === undefined)
            return ids
        return ids.filter(function(id) { return _entry(id).side === side })
    }

    // Puts a tool at another place in the order (the buttons sit together,
    // centred, in this order until one is moved freely).
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
        relayout()
    }

    // Back to every button on the row it starts on (the bottom unless its
    // defaults say), together and centred, its panel docked there (View >
    // Reset Tool Rows).
    function resetPlaces() {
        _pos = {}
        for (var i = 0; i < tools.length; i++) {
            var s = _entry(tools[i].id)
            var home = _side((defaults[tools[i].id] || {}).side)
            s.side = home
            s.dock = home
        }
        _save()
        relayout()
        for (i = 0; i < tools.length; i++)
            toolChanged(tools[i].id)
    }

    // Where a tool's button sits on its row: its left edge, or -1 (tests).
    function placeOf(id) {
        var row = rows ? rows[sideOf(id)] : null
        return row ? row.placeOf(id) : -1
    }

    function relayout() {
        for (var side in rows) {
            if (rows[side])
                rows[side].relayout()
        }
    }

    // A button let go on a row (side) with its left edge at x there:
    // snapped, moved to the nearest free spot, and kept. Every button gets
    // its place the first time, so the others stay where they are. A button
    // put on the other row takes its panel's dock along.
    function dropAt(id, x, side) {
        if (isLocked(id))
            return
        side = side === undefined ? sideOf(id) : _side(side)
        var row = rows ? rows[side] : null
        if (!row)
            return
        if (!Object.keys(_pos || {}).length) {
            var all = {}
            for (var s in rows) {
                var shares = rows[s] ? rows[s].shares() : {}
                for (var k in shares)
                    all[k] = shares[k]
            }
            _pos = all
        }
        var entry = _entry(id)
        if (entry.side !== side) {
            entry.side = side
            entry.dock = side
        }
        var next = {}
        for (var key in _pos)
            next[key] = _pos[key]
        next[id] = row.shareAt(id, x)
        _pos = next
        // The order follows the places (keyboard and lists).
        var order = _order.slice()
        order.sort(function(a, c) { return (_pos[a] || 0) - (_pos[c] || 0) })
        _order = order
        _save()
        relayout()
        toolChanged(id)
    }

    // The row under a point of the window (scene coordinates), or "".
    function sideAt(sceneX, sceneY) {
        var reach = Style.dp(12)
        for (var side in rows) {
            var row = rows[side]
            if (!row || !row.visible)
                continue
            var p = row.mapFromItem(null, sceneX, sceneY)
            if (p.x >= 0 && p.x <= row.width && p.y >= -reach && p.y <= row.height + reach)
                return side
        }
        return ""
    }
}

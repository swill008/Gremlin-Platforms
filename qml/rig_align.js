// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Lining up and spacing out several selected items.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
//
// Items are measured by their boxes on the page (a turned drawing by its
// unturned box) and moved like an arrow-key nudge, so a shape drawn around
// chips moves its chips and a table moves with its chips. Locked items stay.

function _alignItems() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : []
    var out = []
    var seen = {}
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n || isLocked(n) || seen[n.id])
            continue
        seen[n.id] = true
        out.push({ n: n, b: nodeBox(n) })
    }
    return out
}

function canAlign() {
    tick
    return _alignItems().length >= 2
}

function canDistribute() {
    tick
    return _alignItems().length >= 3
}

function _move(item, dxPx, dyPx, seenPack) {
    var s = spaceRect()
    moveNodeBy(item.n, dxPx / Math.max(1, s.w), dyPx / Math.max(1, s.h), seenPack)
}

// mode: left, center, right (across) or top, middle, bottom (down), to the
// edges or middle of the selection's bounds.
function alignSelection(mode) {
    var items = _alignItems()
    if (items.length < 2)
        return
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9
    items.forEach(function(it) {
        x0 = Math.min(x0, it.b.x)
        y0 = Math.min(y0, it.b.y)
        x1 = Math.max(x1, it.b.x + it.b.w)
        y1 = Math.max(y1, it.b.y + it.b.h)
    })
    var seenPack = {}
    items.forEach(function(it) {
        var b = it.b
        var dx = 0
        var dy = 0
        if (mode === "left") dx = x0 - b.x
        else if (mode === "center") dx = (x0 + x1) / 2 - (b.x + b.w / 2)
        else if (mode === "right") dx = x1 - (b.x + b.w)
        else if (mode === "top") dy = y0 - b.y
        else if (mode === "middle") dy = (y0 + y1) / 2 - (b.y + b.h / 2)
        else if (mode === "bottom") dy = y1 - (b.y + b.h)
        if (dx || dy)
            _move(it, dx, dy, seenPack)
    })
    bump()
}

// Equal gaps between three or more items, across ("h") or down ("v"); the
// first and last stay where they are.
function distributeSelection(axis) {
    var items = _alignItems()
    if (items.length < 3)
        return
    var h = axis !== "v"
    items.sort(function(a, b) {
        return h ? (a.b.x + a.b.w / 2) - (b.b.x + b.b.w / 2) : (a.b.y + a.b.h / 2) - (b.b.y + b.b.h / 2)
    })
    var first = items[0].b
    var last = items[items.length - 1].b
    var start = h ? first.x : first.y
    var end = h ? last.x + last.w : last.y + last.h
    var total = 0
    items.forEach(function(it) { total += h ? it.b.w : it.b.h })
    var gap = (end - start - total) / (items.length - 1)
    var at = start
    var seenPack = {}
    items.forEach(function(it, i) {
        var size = h ? it.b.w : it.b.h
        if (i > 0 && i < items.length - 1) {
            var d = at - (h ? it.b.x : it.b.y)
            if (d)
                _move(it, h ? d : 0, h ? 0 : d, seenPack)
        }
        at += size + gap
    })
    bump()
}

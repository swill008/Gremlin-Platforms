// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Turning several selected items together about their middle:
// a handle above the selection's box, and the menu's typed turns.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
//
// Shapes, text boxes and pictures move round the middle and turn by the same
// angle; lines swing round with both ends; chips, groups and tables move but
// stay upright so they still read. Hotspots stay on the photo. Locked items
// stay where they are.
//
// One selected group turns too: its members swing round the group's middle
// and stay upright (the group switches to its free layout first).
.import "rig_shapes.js" as Shapes

// The selected items that move: not locked, not following something else
// (a shape drawn around chips, chips packed into a table).
function _turnItems() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : []
    var out = []
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n || isLocked(n))
            continue
        if (isDraw(n) && n.around && n.around.length)
            continue
        if (!isTable(n) && tablePackOf(n))
            continue
        out.push(n)
    }
    return out
}

// The one selected group that can turn on its own, or null.
function _turnGroup() {
    var ids = selectedIds || []
    if (ids.length !== 1)
        return null
    var n = nodeAt(ids[0])
    if (!isGroup(n) || isLocked(n) || themeLayout(n) || tablePackOf(n))
        return null
    return (n.members || []).length >= 2 ? n : null
}

function canTurnTogether() {
    tick
    if (!interactive)
        return false
    if (_turnGroup())
        return true
    return (selectedIds || []).length >= 2 && _turnItems().length >= 1
}

// A member's chip box on the editor, in pixels.
function _memberBox(n, mem) {
    return {
        x: fxToX(memberPageFx(n, mem)),
        y: fyToY(memberPageFy(n, mem)),
        w: chipWGuess(n, mem),
        h: chipH(n, mem)
    }
}

// The box around the whole selection, in editor pixels.
function selectionBounds() {
    tick
    var ids = selectedIds || []
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n)
            continue
        var b = nodeBox(n)
        x0 = Math.min(x0, b.x)
        y0 = Math.min(y0, b.y)
        x1 = Math.max(x1, b.x + b.w)
        y1 = Math.max(y1, b.y + b.h)
    }
    if (x1 < x0)
        return { x: 0, y: 0, w: 0, h: 0 }
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }
}

// Whether (mx, my) is on the selection's rotate handle.
function onTurnHandle(mx, my) {
    if (!canTurnTogether())
        return false
    var b = selectionBounds()
    return Math.hypot(mx - (b.x + b.w / 2), my - (b.y - rotateHandleOffset)) < 9
}

// Moves an item by page fractions without keeping it on the page, so a turn
// there and back lands where it started (a hand move keeps items on it).
function _shift(n, dfx, dfy) {
    if (isDraw(n)) {
        n.fx = (n.fx || 0) + dfx
        n.fy = (n.fy || 0) + dfy
        shiftIndependentParts(n, dfx, dfy)
        followTablePacked(n)
    } else {
        n.chipFx = (n.chipFx || 0) + dfx
        n.chipFy = (n.chipFy || 0) + dfy
        refreshChipPack(n)
    }
}

function _centre(n) {
    var b = nodeBox(n)
    return { x: b.x + b.w / 2, y: b.y + b.h / 2 }
}

// Remembers where everything is when the turn starts.
// The turn goes round the average of the items' middles, which a turn does
// not change, so turning there and back ends where it started.
function turnPivot() {
    var g = _turnGroup()
    if (g) {
        var b = nodeBox(g)
        return { x: b.x + b.w / 2, y: b.y + b.h / 2 }
    }
    var list = _turnItems()
    var c = { x: 0, y: 0 }
    for (var i = 0; i < list.length; i++) {
        var mid = _centre(list[i])
        c.x += mid.x / list.length
        c.y += mid.y / list.length
    }
    return c
}

function beginTurn(mx, my) {
    var g = _turnGroup()
    if (g) {
        bakeAlignToFree(g)
        var gc = turnPivot()
        var mems = []
        var mem = g.members || []
        for (var m = 0; m < mem.length; m++) {
            var mb = _memberBox(g, mem[m])
            mems.push({ x: mb.x + mb.w / 2, y: mb.y + mb.h / 2, w: mb.w, h: mb.h })
        }
        turnStart = { c: gc, a0: Shapes.handleAngle(gc.x, gc.y, mx, my), group: g.id, members: mems }
        return
    }
    var items = []
    var list = _turnItems()
    var c = turnPivot()
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        var mid = _centre(n)
        var tip = (n.tail && n.tail.fx !== undefined) ? calloutTip(n) : null
        items.push({
            id: n.id,
            c: mid,
            rot: n.rot || 0,
            ends: isLine(n) ? lineEndsAt(n) : null,
            tip: tip
        })
    }
    turnStart = { c: c, a0: Shapes.handleAngle(c.x, c.y, mx, my), items: items }
}

// Puts every item at the start position turned by deg about the middle.
function _turnTo(deg) {
    var st = turnStart
    if (!st)
        return
    var s = spaceRect()
    if (st.group) {
        // Members' middles round the group's middle; each chip upright.
        var g = nodeAt(st.group)
        var mem = g ? (g.members || []) : []
        var ax = g ? fxToX(g.chipFx) : 0
        var ay = g ? fyToY(g.chipFy) : 0
        for (var m = 0; m < mem.length && m < st.members.length; m++) {
            var sm = st.members[m]
            var o = Shapes.rotatePt(sm.x - st.c.x, sm.y - st.c.y, deg)
            mem[m].ox = (st.c.x + o.x - sm.w / 2 - ax) / Math.max(1, s.w)
            mem[m].oy = (st.c.y + o.y - sm.h / 2 - ay) / Math.max(1, s.h)
        }
        return
    }
    for (var i = 0; i < st.items.length; i++) {
        var it = st.items[i]
        var n = nodeAt(it.id)
        if (!n)
            continue
        if (it.ends) {
            var a = Shapes.rotatePt(it.ends.ax - st.c.x, it.ends.ay - st.c.y, deg)
            var bb = Shapes.rotatePt(it.ends.bx - st.c.x, it.ends.by - st.c.y, deg)
            setLineEnds(n, st.c.x + a.x, st.c.y + a.y, st.c.x + bb.x, st.c.y + bb.y)
            continue
        }
        var off = Shapes.rotatePt(it.c.x - st.c.x, it.c.y - st.c.y, deg)
        var now = _centre(n)
        var dx = st.c.x + off.x - now.x
        var dy = st.c.y + off.y - now.y
        if (dx || dy)
            _shift(n, dx / Math.max(1, s.w), dy / Math.max(1, s.h))
        if (isRotatable(n))
            n.rot = Shapes.normDeg(it.rot + deg)
        if (it.tip) {
            var t = Shapes.rotatePt(it.tip.x - st.c.x, it.tip.y - st.c.y, deg)
            n.tail = { fx: xToFx(st.c.x + t.x), fy: yToFy(st.c.y + t.y) }
        }
    }
}

function dragTurn(mx, my) {
    var st = turnStart
    if (!st)
        return
    var deg = Shapes.handleAngle(st.c.x, st.c.y, mx, my) - st.a0
    deg = shiftHeld ? Math.round(deg / rotateSnap) * rotateSnap : Math.round(deg * 10) / 10
    turnAngle = Shapes.normDeg(deg)
    _turnTo(deg)
    tick++
}

function endTurn() {
    turnStart = null
    turnAngle = 0
    bump()
}

// The menu's typed turn for several items.
function turnSelectionBy(deg) {
    var b = selectionBounds()
    beginTurn(b.x + b.w / 2, b.y - rotateHandleOffset)
    _turnTo(deg)
    endTurn()
}

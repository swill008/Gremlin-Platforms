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

// Resizing several selected items together by the selection box's eight
// handles (07 S153). A corner keeps the box's proportions (Shift frees
// them), a side stretches one way, Alt resizes from the middle. Drawings
// and pictures scale with the box; chips, hotspots, text boxes, callouts,
// tables and groups keep their own size and only move; lines take both
// ends with them. The whole drag is one undo step (the pointer's gesture).

function canGroupResize() {
    tick
    return interactive && (selectedIds || []).length >= 2 && _turnItems().length >= 1
}

// The box's handles in editor pixels, by name.
function groupResizeHandles(b) {
    var x0 = b.x, y0 = b.y, x1 = b.x + b.w, y1 = b.y + b.h
    var xm = b.x + b.w / 2, ym = b.y + b.h / 2
    return [
        { h: "tl", x: x0, y: y0 }, { h: "t", x: xm, y: y0 }, { h: "tr", x: x1, y: y0 },
        { h: "r", x: x1, y: ym }, { h: "br", x: x1, y: y1 }, { h: "b", x: xm, y: y1 },
        { h: "bl", x: x0, y: y1 }, { h: "l", x: x0, y: ym }
    ]
}

// The handle under (mx, my), or "".
function onGroupResizeHandle(mx, my) {
    if (!canGroupResize())
        return ""
    var hs = groupResizeHandles(selectionBounds())
    var r = Math.max(8, groupHandleSize)
    for (var i = 0; i < hs.length; i++) {
        if (Math.hypot(mx - hs[i].x, my - hs[i].y) < r)
            return hs[i].h
    }
    return ""
}

// Items that scale with the box; the rest only move.
function _groupScales(n) {
    return isDraw(n) && !isLine(n) && !isText(n) && !isTable(n) && !isCallout(n)
}

function beginGroupResize(handle, mx, my) {
    var b = selectionBounds()
    var list = _turnItems()
    var items = []
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        var it = { id: n.id }
        if (isLine(n)) {
            it.ends = lineEndsAt(n)
        } else if (_groupScales(n)) {
            it.box = drawGeom(n)
        } else {
            it.c = _centre(n)
            if (n.tail && n.tail.fx !== undefined)
                it.tip = calloutTip(n)
        }
        items.push(it)
    }
    groupRz = { h: handle, px: mx, py: my, box: b, items: items }
}

// The box for the pointer at (mx, my): { x0, y0, x1, y1 }.
function _groupBoxFor(st, mx, my) {
    var b = st.box
    var h = st.h
    var dx = mx - st.px
    var dy = my - st.py
    var x0 = b.x, y0 = b.y, x1 = b.x + b.w, y1 = b.y + b.h
    var corner = h.length === 2
    var fromMid = altHeld
    if (h.indexOf("l") >= 0) { x0 += dx; if (fromMid) x1 -= dx }
    if (h.indexOf("r") >= 0) { x1 += dx; if (fromMid) x0 -= dx }
    if (h.indexOf("t") >= 0) { y0 += dy; if (fromMid) y1 -= dy }
    if (h.indexOf("b") >= 0) { y1 += dy; if (fromMid) y0 -= dy }
    // No mirroring for a group: the box keeps a minimum size, on its own side.
    var minPx = 4
    var w0 = Math.max(1, b.w)
    var h0 = Math.max(1, b.h)
    var nw = Math.max(minPx, x1 - x0)
    var nh = Math.max(minPx, y1 - y0)
    if (corner && !shiftHeld) {
        // Keep the box's proportions at the press: the larger change wins.
        var sx = nw / w0
        var sy = nh / h0
        var s = Math.abs(sx - 1) >= Math.abs(sy - 1) ? sx : sy
        s = Math.max(minPx / Math.min(w0, h0), s)
        nw = w0 * s
        nh = h0 * s
    }
    // Anchor: the middle with Alt, else the side or corner opposite the handle.
    var cx = b.x + b.w / 2
    var cy = b.y + b.h / 2
    var ox, oy
    if (fromMid) {
        ox = cx - nw / 2
        oy = cy - nh / 2
    } else {
        ox = h.indexOf("l") >= 0 ? b.x + b.w - nw : b.x
        oy = h.indexOf("t") >= 0 ? b.y + b.h - nh : b.y
    }
    // A side handle leaves the other direction alone.
    if (h === "t" || h === "b") {
        nw = b.w
        ox = b.x
    }
    if (h === "l" || h === "r") {
        nh = b.h
        oy = b.y
    }
    return { x0: ox, y0: oy, x1: ox + nw, y1: oy + nh }
}

function dragGroupResize(mx, my) {
    var st = groupRz
    if (!st)
        return
    var nb = _groupBoxFor(st, mx, my)
    var b = st.box
    var sx = (nb.x1 - nb.x0) / Math.max(1, b.w)
    var sy = (nb.y1 - nb.y0) / Math.max(1, b.h)
    function mapX(x) { return nb.x0 + (x - b.x) * sx }
    function mapY(y) { return nb.y0 + (y - b.y) * sy }
    var s = spaceRect()
    for (var i = 0; i < st.items.length; i++) {
        var it = st.items[i]
        var n = nodeAt(it.id)
        if (!n)
            continue
        if (it.ends) {
            setLineEnds(n, mapX(it.ends.ax), mapY(it.ends.ay), mapX(it.ends.bx), mapY(it.ends.by))
            continue
        }
        if (it.box) {
            // Size first (the box's corner stays), then move it into place so
            // parts that follow the item move with it.
            n.fw = Math.max(1, it.box.w * sx) / Math.max(1, s.w)
            n.fh = Math.max(1, it.box.h * sy) / Math.max(1, s.h)
            var g = drawGeom(n)
            var tx = mapX(it.box.x)
            var ty = mapY(it.box.y)
            if (tx !== g.x || ty !== g.y)
                _shift(n, (tx - g.x) / Math.max(1, s.w), (ty - g.y) / Math.max(1, s.h))
            continue
        }
        var now = _centre(n)
        var dx = mapX(it.c.x) - now.x
        var dy = mapY(it.c.y) - now.y
        if (dx || dy)
            _shift(n, dx / Math.max(1, s.w), dy / Math.max(1, s.h))
        if (it.tip)
            n.tail = { fx: xToFx(mapX(it.tip.x)), fy: yToFy(mapY(it.tip.y)) }
    }
    tick++
}

function endGroupResize() {
    if (!groupRz)
        return
    groupRz = null
    bump()
}

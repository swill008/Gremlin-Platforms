// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Mirroring a whole layout left to right: for a left-hand stick laid out
// from a right-hand one (Edit → Mirror layout, File → Copy layout from).
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
//
// Every item's box goes to the other side of the page; hotspots, leader
// bends and loose leader ends too. Shapes and lines are mirrored as well, so
// an arrow points the other way; text, tables and a group's own arrangement
// are kept as they are, so they still read. Pictures are mirrored only when
// asked, since text in them would read backwards.
.import "rig_shapes.js" as Shapes

function _mirrorX(fx) {
    return 1 - (Number(fx) || 0)
}

function _swapPin(p) {
    return p === "left" ? "right" : (p === "right" ? "left" : p)
}

// A chip's first leader can share its ends and bends with the chip itself:
// each object is mirrored once.
function _once(done, obj) {
    if (!obj || done.indexOf(obj) >= 0)
        return false
    done.push(obj)
    return true
}

function _mirrorEnd(e, done) {
    if (!_once(done, e))
        return
    if (e.fx !== undefined)
        e.fx = _mirrorX(e.fx)
    if (e.pin)
        e.pin = _swapPin(e.pin)
}

function _mirrorSpines(list, done) {
    for (var i = 0; list && i < list.length; i++) {
        if (_once(done, list[i]) && list[i].fx !== undefined)
            list[i].fx = _mirrorX(list[i].fx)
    }
}

// The drawing itself, inside its box (its place is moved separately).
function _mirrorDrawing(n, pictures) {
    if (isLine(n)) {
        var e = n.ends
        if (e && e.length === 4)
            n.ends = [1 - e[0], e[1], 1 - e[2], e[3]]
        return
    }
    if (n.tail && n.tail.fx !== undefined)
        n.tail.fx = _mirrorX(n.tail.fx)
    if (n.skew)
        n.skew = [-(Number(n.skew[0]) || 0), -(Number(n.skew[1]) || 0)]
    if (isText(n) || isTable(n))
        return
    if (isOverlay(n) && !pictures) {
        if (n.rot)
            n.rot = Shapes.normDeg(-n.rot)
        return
    }
    if (n.flipH)
        delete n.flipH
    else
        n.flipH = true
    if (n.rot)
        n.rot = Shapes.normDeg(-n.rot)
}

function mirrorLayout(pictures) {
    var list = nodes || []
    var s = spaceRect()
    var seenPack = {}
    // Boxes first, measured before anything moves.
    var moves = []
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        if (!n)
            continue
        // These follow what they belong to: a shape drawn around chips, and
        // chips or text packed into a table.
        if (isDraw(n) && n.around && n.around.length)
            continue
        if (!isTable(n) && tablePackOf(n))
            continue
        var b = nodeBox(n)
        moves.push({ n: n, dx: 2 * s.x + s.w - 2 * b.x - b.w })
    }
    for (i = 0; i < moves.length; i++) {
        var m = moves[i]
        // A locked item stays put when moved by hand, but goes with the rest here.
        var locked = m.n.locked
        if (locked)
            m.n.locked = false
        moveNodeBy(m.n, m.dx / Math.max(1, s.w), 0, seenPack)
        if (locked)
            m.n.locked = locked
    }
    var done = []
    for (i = 0; i < list.length; i++) {
        var o = list[i]
        if (!o)
            continue
        if (isDraw(o)) {
            _mirrorDrawing(o, pictures)
            continue
        }
        if (o.hotFx !== undefined)
            o.hotFx = _mirrorX(o.hotFx)
        if (o.pin)
            o.pin = _swapPin(o.pin)
        _mirrorSpines(o.spines, done)
        _mirrorEnd(o.from, done)
        _mirrorEnd(o.to, done)
        var leads = o.leaders || []
        for (var k = 0; k < leads.length; k++) {
            _mirrorSpines(leads[k].spines, done)
            _mirrorEnd(leads[k].from, done)
            _mirrorEnd(leads[k].to, done)
        }
    }
    bump()
}

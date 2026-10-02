// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Pure shape maths for the Button Map editor: block arrows, line ends,
// arrowheads, dash patterns, distance to a line and angle snapping. No editor
// state; test/unit/test_rig_shapes.py runs these directly.
.pragma library

// Outline of a block arrow in a w x h box: "arrow" points right, "arrow2"
// points both ways. The shaft is half the height; a head is as long as the
// box is high, but never more than 45% of the width.
function blockArrow(shape, w, h) {
    var head = Math.min(h, w * 0.45)
    var top = h * 0.25
    var bottom = h * 0.75
    var mid = h * 0.5
    if (shape === "arrow2") {
        head = Math.min(h, w * 0.3)
        return [
            [0, mid], [head, 0], [head, top], [w - head, top], [w - head, 0],
            [w, mid], [w - head, h], [w - head, bottom], [head, bottom], [head, h]
        ]
    }
    return [
        [0, top], [w - head, top], [w - head, 0], [w, mid],
        [w - head, h], [w - head, bottom], [0, bottom]
    ]
}

// Canvas dash array for an outline style. Qt measures dashes in multiples of
// the line width, so the lengths are divided by it to stay the same size.
function dashFor(style, width) {
    var w = Math.max(0.5, Number(width) || 1)
    if (style === "dash")
        return [8 / w, 6 / w]
    if (style === "dot")
        return [Math.max(1, w) / w, 4 / w]
    return []
}

// A line's two ends in its w x h box, from its stored fractions.
function lineEnds(ends, w, h) {
    var e = (ends && ends.length === 4) ? ends : [0, 0.5, 1, 0.5]
    return { ax: e[0] * w, ay: e[1] * h, bx: e[2] * w, by: e[3] * h }
}

// The box and end fractions for a line from (ax, ay) to (bx, by). The box
// keeps margin on every side: a drawing paints only inside its box, and
// arrowheads and thick strokes reach past the ends.
function lineBox(ax, ay, bx, by, margin) {
    var m = Math.max(1, margin || 8)
    var x = Math.min(ax, bx) - m
    var y = Math.min(ay, by) - m
    var w = Math.abs(bx - ax) + 2 * m
    var h = Math.abs(by - ay) + 2 * m
    return {
        x: x, y: y, w: w, h: h,
        ends: [(ax - x) / w, (ay - y) / h, (bx - x) / w, (by - y) / h]
    }
}

// Margin a line's box needs around its ends for its width and heads.
function lineMargin(width) {
    var w = Number(width) || 2
    return Math.max(8, headSize(w) * 0.5 + w)
}

// Arrowhead at tip (tx, ty) for a line arriving from (fx, fy): the two back
// corners and the middle of the back edge, where a hollow head's line stops.
function arrowHead(tx, ty, fx, fy, size) {
    var dx = tx - fx
    var dy = ty - fy
    var len = Math.hypot(dx, dy)
    if (len < 0.001)
        return null
    var ux = dx / len
    var uy = dy / len
    var s = Math.min(size, len)
    var bx = tx - ux * s
    var by = ty - uy * s
    var half = s * 0.5
    return {
        tip: [tx, ty],
        left: [bx - uy * half, by + ux * half],
        right: [bx + uy * half, by - ux * half],
        base: [bx, by]
    }
}

// Arrowhead length for a line width: big enough to read at width 1.
function headSize(width) {
    return Math.max(10, (Number(width) || 2) * 4)
}

// Shortest distance from (px, py) to the segment (ax, ay)-(bx, by).
function distToSegment(px, py, ax, ay, bx, by) {
    var dx = bx - ax
    var dy = by - ay
    var len2 = dx * dx + dy * dy
    var t = len2 > 0 ? ((px - ax) * dx + (py - ay) * dy) / len2 : 0
    t = Math.max(0, Math.min(1, t))
    return Math.hypot(px - (ax + t * dx), py - (ay + t * dy))
}

// (bx, by) moved onto the nearest stepDeg angle around (ax, ay), keeping its
// distance: Shift while drawing or dragging a line end.
function snapAngle(ax, ay, bx, by, stepDeg) {
    var dx = bx - ax
    var dy = by - ay
    var len = Math.hypot(dx, dy)
    if (len < 0.001)
        return { x: bx, y: by }
    var step = (stepDeg || 15) * Math.PI / 180
    var a = Math.round(Math.atan2(dy, dx) / step) * step
    return { x: ax + Math.cos(a) * len, y: ay + Math.sin(a) * len }
}

// --- rotation ------------------------------------------------------------------

// (x, y) turned by deg degrees (clockwise on screen, as Item.rotation).
function rotatePt(x, y, deg) {
    var a = deg * Math.PI / 180
    var c = Math.cos(a)
    var s = Math.sin(a)
    return { x: x * c - y * s, y: x * s + y * c }
}

// An angle in [0, 360).
function normDeg(a) {
    var d = Number(a) || 0
    d = d % 360
    return d < 0 ? d + 360 : d
}

// The angle of (px, py) seen from the centre, 0 straight up and growing
// clockwise: what a rotate handle above the top edge sets.
function handleAngle(cx, cy, px, py) {
    return normDeg(Math.atan2(px - cx, -(py - cy)) * 180 / Math.PI)
}

function snapDeg(a, step) {
    var s = step || 15
    return normDeg(Math.round(a / s) * s)
}

// Resizes a box drawn turned by rot degrees about its centre, from one of its
// handles (n, s, e, w, ne, nw, se, sw), keeping the opposite side or corner
// where it is on screen. box is the unturned box (x, y, w, h); the pointer is
// on screen. keepAspect keeps the width to height ratio (corner handles).
// Returns the new unturned box.
function rotatedResize(box, rot, handle, px, py, minW, minH, keepAspect) {
    var sx = handle.indexOf("e") >= 0 ? 1 : (handle.indexOf("w") >= 0 ? -1 : 0)
    var sy = handle.indexOf("s") >= 0 ? 1 : (handle.indexOf("n") >= 0 ? -1 : 0)
    var cx = box.x + box.w / 2
    var cy = box.y + box.h / 2
    // The fixed point: the opposite corner, or the middle of the opposite edge.
    var fixedLocal = { x: -sx * box.w / 2, y: -sy * box.h / 2 }
    var f = rotatePt(fixedLocal.x, fixedLocal.y, rot)
    var fx = cx + f.x
    var fy = cy + f.y
    // The pointer in the box's own axes, measured from the fixed point.
    var d = rotatePt(px - fx, py - fy, -rot)
    var w = sx ? Math.max(minW, d.x * sx) : box.w
    var h = sy ? Math.max(minH, d.y * sy) : box.h
    if (keepAspect && sx && sy && box.w > 0 && box.h > 0) {
        var ratio = box.w / box.h
        if (w / ratio > h)
            h = w / ratio
        else
            w = h * ratio
    }
    // New centre: from the fixed point, half the new size towards the handle
    // (along one axis only for an edge handle).
    var half = rotatePt(sx * w / 2, sy * h / 2, rot)
    var ncx = fx + half.x
    var ncy = fy + half.y
    return { x: ncx - w / 2, y: ncy - h / 2, w: w, h: h }
}

// --- cropping a picture -----------------------------------------------------------

// A crop: the fractions of the picture cut off each side.
function cropOf(c) {
    c = c || {}
    return { l: Number(c.l) || 0, t: Number(c.t) || 0, r: Number(c.r) || 0, b: Number(c.b) || 0 }
}

// Keeps at least 2% of the picture each way and nothing below zero.
function clampCrop(c) {
    var o = cropOf(c)
    o.l = Math.max(0, Math.min(0.98, o.l))
    o.t = Math.max(0, Math.min(0.98, o.t))
    o.r = Math.max(0, Math.min(0.98 - o.l, o.r))
    o.b = Math.max(0, Math.min(0.98 - o.t, o.b))
    return o
}

// The box showing crop c1 of a picture that box shows at crop c0, so what
// stays visible does not move or change size on screen (rot as Item.rotation).
function cropBox(box, rot, c0, c1) {
    var a = cropOf(c0)
    var z = cropOf(c1)
    var pxX = box.w / Math.max(0.0001, 1 - a.l - a.r)
    var pxY = box.h / Math.max(0.0001, 1 - a.t - a.b)
    var left = -box.w / 2 + (z.l - a.l) * pxX
    var right = box.w / 2 - (z.r - a.r) * pxX
    var top = -box.h / 2 + (z.t - a.t) * pxY
    var bottom = box.h / 2 - (z.b - a.b) * pxY
    var mid = rotatePt((left + right) / 2, (top + bottom) / 2, rot || 0)
    var w = right - left
    var h = bottom - top
    var cx = box.x + box.w / 2 + mid.x
    var cy = box.y + box.h / 2 + mid.y
    return { x: cx - w / 2, y: cy - h / 2, w: w, h: h }
}

// The crop a handle drag asks for: the handle's edges move to where
// rotatedResize puts them, the picture staying still under them.
function cropFromDrag(box, rot, c0, handle, px, py) {
    var a = cropOf(c0)
    var want = rotatedResize(box, rot, handle, px, py, 1, 1, false)
    var pxX = box.w / Math.max(0.0001, 1 - a.l - a.r)
    var pxY = box.h / Math.max(0.0001, 1 - a.t - a.b)
    var c = cropOf(a)
    if (handle.indexOf("e") >= 0) c.r = a.r + (box.w - want.w) / pxX
    if (handle.indexOf("w") >= 0) c.l = a.l + (box.w - want.w) / pxX
    if (handle.indexOf("s") >= 0) c.b = a.b + (box.h - want.h) / pxY
    if (handle.indexOf("n") >= 0) c.t = a.t + (box.h - want.h) / pxY
    return clampCrop(c)
}

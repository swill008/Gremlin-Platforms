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

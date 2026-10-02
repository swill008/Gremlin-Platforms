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

// --- callouts ------------------------------------------------------------------

// The outline of a callout: a w x h box with a pointer to (tx, ty), in the
// box's own coordinates, as [[x, y], ...] going round clockwise. The pointer
// leaves the side facing its tip, centred under the tip where it can be,
// base wide (at most a third of that side). A tip inside the box gives the
// box alone.
function calloutOutline(w, h, tx, ty, base) {
    var dx = tx < 0 ? -tx : (tx > w ? tx - w : 0)
    var dy = ty < 0 ? -ty : (ty > h ? ty - h : 0)
    var box = [[0, 0], [w, 0], [w, h], [0, h]]
    if (!dx && !dy)
        return box
    function along(len, at) {
        var half = Math.min(base / 2, len / 6)
        var c = Math.max(half, Math.min(len - half, at))
        return { a: c - half, b: c + half }
    }
    if (dy >= dx) {
        var bx = along(w, tx)
        if (ty < 0)
            return [[0, 0], [bx.a, 0], [tx, ty], [bx.b, 0], [w, 0], [w, h], [0, h]]
        return [[0, 0], [w, 0], [w, h], [bx.b, h], [tx, ty], [bx.a, h], [0, h]]
    }
    var by = along(h, ty)
    if (tx > w)
        return [[0, 0], [w, 0], [w, by.a], [tx, ty], [w, by.b], [w, h], [0, h]]
    return [[0, 0], [w, 0], [w, h], [0, h], [0, by.b], [tx, ty], [0, by.a]]
}

// --- paths (several points, and freehand) -------------------------------------------

// Fewer points along the same line (Ramer-Douglas-Peucker): every point
// dropped is within tol of the line kept. pts are [[x, y], ...].
function simplifyPath(pts, tol) {
    if (!pts || pts.length < 3)
        return (pts || []).slice()
    var keep = []
    for (var k = 0; k < pts.length; k++)
        keep.push(false)
    keep[0] = true
    keep[pts.length - 1] = true
    var stack = [[0, pts.length - 1]]
    while (stack.length) {
        var span = stack.pop()
        var a = pts[span[0]]
        var b = pts[span[1]]
        var far = -1
        var best = tol
        for (var i = span[0] + 1; i < span[1]; i++) {
            var d = distToSegment(pts[i][0], pts[i][1], a[0], a[1], b[0], b[1])
            if (d > best) {
                best = d
                far = i
            }
        }
        if (far >= 0) {
            keep[far] = true
            stack.push([span[0], far])
            stack.push([far, span[1]])
        }
    }
    return pts.filter(function(_p, idx) { return keep[idx] })
}

// The box round some points with margin on every side, and the points as
// fractions of it (as a path drawing stores them).
function pathBox(pts, margin) {
    var m = Math.max(1, margin || 8)
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9
    for (var i = 0; i < pts.length; i++) {
        x0 = Math.min(x0, pts[i][0])
        y0 = Math.min(y0, pts[i][1])
        x1 = Math.max(x1, pts[i][0])
        y1 = Math.max(y1, pts[i][1])
    }
    var x = x0 - m
    var y = y0 - m
    var w = x1 - x0 + 2 * m
    var h = y1 - y0 + 2 * m
    return {
        x: x, y: y, w: w, h: h,
        rel: pts.map(function(p) { return [(p[0] - x) / w, (p[1] - y) / h] })
    }
}

// Shortest distance from (px, py) to a path through pts (closed: back to
// the first point too).
function distToPath(px, py, pts, closed) {
    var best = 1e9
    var n = pts.length
    var last = closed ? n : n - 1
    for (var i = 0; i < last; i++) {
        var a = pts[i]
        var b = pts[(i + 1) % n]
        best = Math.min(best, distToSegment(px, py, a[0], a[1], b[0], b[1]))
    }
    return n === 1 ? Math.hypot(px - pts[0][0], py - pts[0][1]) : best
}

// Whether (px, py) is inside the polygon through pts.
function insidePolygon(px, py, pts) {
    var inside = false
    for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        var a = pts[i]
        var b = pts[j]
        if ((a[1] > py) !== (b[1] > py)
                && px < (b[0] - a[0]) * (py - a[1]) / (b[1] - a[1]) + a[0])
            inside = !inside
    }
    return inside
}

// --- light page for printing ------------------------------------------------------

// A colour with its lightness turned over (HSL): dark becomes light and light
// dark, keeping its hue, saturation and alpha. Takes and gives "#RGB",
// "#RRGGBB" or "#AARRGGBB"; anything else (a name, "transparent") as it is.
function invertLightness(c) {
    var s = String(c || "")
    var m = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.exec(s)
    if (!m)
        return c
    var hex = m[1]
    if (hex.length === 3)
        hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
    var alpha = ""
    if (hex.length === 8) {
        alpha = hex.slice(0, 2)
        hex = hex.slice(2)
    }
    var r = parseInt(hex.slice(0, 2), 16) / 255
    var g = parseInt(hex.slice(2, 4), 16) / 255
    var b = parseInt(hex.slice(4, 6), 16) / 255
    var max = Math.max(r, g, b)
    var min = Math.min(r, g, b)
    var l = (max + min) / 2
    var h = 0
    var sat = 0
    if (max !== min) {
        var d = max - min
        sat = l > 0.5 ? d / (2 - max - min) : d / (max + min)
        if (max === r)
            h = (g - b) / d + (g < b ? 6 : 0)
        else if (max === g)
            h = (b - r) / d + 2
        else
            h = (r - g) / d + 4
        h /= 6
    }
    l = 1 - l
    function channel(p, q, t) {
        if (t < 0) t += 1
        if (t > 1) t -= 1
        if (t < 1 / 6) return p + (q - p) * 6 * t
        if (t < 1 / 2) return q
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6
        return p
    }
    var out
    if (sat === 0) {
        out = [l, l, l]
    } else {
        var q = l < 0.5 ? l * (1 + sat) : l + sat - l * sat
        var p = 2 * l - q
        out = [channel(p, q, h + 1 / 3), channel(p, q, h), channel(p, q, h - 1 / 3)]
    }
    function two(v) {
        var t = Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).toUpperCase()
        return t.length < 2 ? "0" + t : t
    }
    return "#" + alpha + two(out[0]) + two(out[1]) + two(out[2])
}

// --- shaping block arrows and other shapes (Transform in the menu) -----------------

// A block arrow's measures in a w x h box. adj: headLen (fraction of the
// width), headW and shaft (fractions of the arrow's thickness); bend: how
// far the shaft's middle leaves the straight line, as a fraction of the
// box's height (-0.4..0.4). A bent arrow keeps its thickness, T, in the
// part of the box the bend leaves.
function arrowMeasures(shape, w, h, adj, bend) {
    var a = adj || {}
    var b = Math.max(-0.4, Math.min(0.4, Number(bend) || 0))
    var T = h * (1 - 2 * Math.abs(b))
    var two = shape === "arrow2"
    var defLen = Math.min(h, w * (two ? 0.3 : 0.45)) / Math.max(1, w)
    var headLen = a.headLen > 0 ? a.headLen : defLen
    headLen = Math.min(headLen, two ? 0.48 : 0.95)
    var headW = a.headW > 0 ? Math.min(1, a.headW) : 1
    var shaft = a.shaft > 0 ? a.shaft : 0.5
    var H = headW * T
    var S = Math.min(shaft * T, H)
    return { L: headLen * w, H: H, S: S, T: T, off: b * h, mid: h / 2, two: two }
}

// The middle line of an arrow: from (0, mid) to (w, mid), through
// (w / 2, mid - off) at its middle.
function arrowCurve(w, m) {
    var cy = m.mid - 2 * m.off
    function at(t) {
        var u = 1 - t
        return [2 * u * t * (w / 2) + t * t * w, u * u * m.mid + 2 * u * t * cy + t * t * m.mid]
    }
    function up(t) {
        var tx = w
        var ty = 2 * (1 - t) * (cy - m.mid) + 2 * t * (m.mid - cy)
        var len = Math.hypot(tx, ty) || 1
        return [ty / len, -tx / len]
    }
    return { at: at, up: up }
}

// Where along the curve (t) the arc length from the start is s.
function _tAtLength(curve, s, total, samples) {
    if (s <= 0)
        return 0
    if (s >= total)
        return 1
    var prev = curve.at(0)
    var run = 0
    for (var i = 1; i <= samples; i++) {
        var p = curve.at(i / samples)
        var d = Math.hypot(p[0] - prev[0], p[1] - prev[1])
        if (run + d >= s)
            return (i - 1 + (s - run) / (d || 1)) / samples
        run += d
        prev = p
    }
    return 1
}

function _curveLength(curve, samples) {
    var prev = curve.at(0)
    var run = 0
    for (var i = 1; i <= samples; i++) {
        var p = curve.at(i / samples)
        run += Math.hypot(p[0] - prev[0], p[1] - prev[1])
        prev = p
    }
    return run
}

// Where along the arrow its heads meet the shaft: {tStart, tEnd}.
function arrowHeadTs(shape, w, h, adj, bend) {
    var m = arrowMeasures(shape, w, h, adj, bend)
    var c = arrowCurve(w, m)
    var N = 48
    var total = _curveLength(c, N)
    return {
        tStart: m.two ? _tAtLength(c, m.L, total, N) : 0,
        tEnd: _tAtLength(c, total - m.L, total, N)
    }
}

// The outline of a block arrow, shaped and bent. Unshaped and straight, it
// is blockArrow's outline.
function arrowOutline(shape, w, h, adj, bend) {
    var hasAdj = adj && (adj.headLen > 0 || adj.headW > 0 || adj.shaft > 0)
    if (!hasAdj && !Number(bend))
        return blockArrow(shape, w, h)
    var m = arrowMeasures(shape, w, h, adj, bend)
    var c = arrowCurve(w, m)
    var ts = arrowHeadTs(shape, w, h, adj, bend)
    function off(t, d) {
        var p = c.at(t)
        var u = c.up(t)
        return [p[0] + u[0] * d, p[1] + u[1] * d]
    }
    var steps = Number(bend) ? 16 : 1
    var top = []
    var bottom = []
    for (var i = 0; i <= steps; i++) {
        var t = ts.tStart + (ts.tEnd - ts.tStart) * i / steps
        top.push(off(t, m.S / 2))
        bottom.push(off(t, -m.S / 2))
    }
    var out = []
    if (m.two) {
        out.push(c.at(0))
        out.push(off(ts.tStart, m.H / 2))
    }
    out = out.concat(top)
    out.push(off(ts.tEnd, m.H / 2))
    out.push(c.at(1))
    out.push(off(ts.tEnd, -m.H / 2))
    out = out.concat(bottom.reverse())
    if (m.two)
        out.push(off(ts.tStart, -m.H / 2))
    return out
}

// A rounded rectangle's corner radius: adj.r as a fraction of the shorter
// side (0..0.5), else as it has always been drawn.
function roundRadius(n, w, h) {
    var adj = (n && n.adj) || {}
    if (adj.r >= 0)
        return Math.max(0, Math.min(0.5, adj.r)) * Math.min(w, h)
    return Math.min(14, w * 0.2, h * 0.2)
}

// A triangle's apex across its top, 0..1 (0.5 unless shaped).
function triangleApex(n) {
    var a = n && n.adj ? n.adj.apex : undefined
    return a >= 0 && a <= 1 ? a : 0.5
}

// A shape's outline as points in its w x h box, for Edit points (turning it
// into a path). smooth: the path is drawn as a curve.
function shapeOutline(n, w, h) {
    var shape = n.shape || "rect"
    if (shape === "arrow" || shape === "arrow2")
        return { pts: arrowOutline(shape, w, h, n.adj, n.bend), smooth: false }
    if (shape === "triangle")
        return { pts: [[triangleApex(n) * w, 0], [w, h], [0, h]], smooth: false }
    if (shape === "diamond")
        return { pts: [[w / 2, 0], [w, h / 2], [w / 2, h], [0, h / 2]], smooth: false }
    if (shape === "ellipse") {
        var e = []
        for (var k = 0; k < 12; k++) {
            var a = k / 12 * 2 * Math.PI
            e.push([w / 2 + Math.cos(a) * w / 2, h / 2 + Math.sin(a) * h / 2])
        }
        return { pts: e, smooth: true }
    }
    if (shape === "roundrect") {
        var r = roundRadius(n, w, h)
        var pts = []
        var corners = [[w - r, r, -90], [w - r, h - r, 0], [r, h - r, 90], [r, r, 180]]
        for (var q = 0; q < 4; q++) {
            for (var j = 0; j <= 2; j++) {
                var ang = (corners[q][2] + j * 45) * Math.PI / 180
                pts.push([corners[q][0] + Math.cos(ang) * r, corners[q][1] + Math.sin(ang) * r])
            }
        }
        return { pts: pts, smooth: false }
    }
    return { pts: [[0, 0], [w, 0], [w, h], [0, h]], smooth: false }
}

// Skewing: (x, y) about the middle of a w x h box, sideways by kx for each
// pixel down and down by ky for each pixel across.
function skewPt(x, y, w, h, kx, ky) {
    var dx = x - w / 2
    var dy = y - h / 2
    return [w / 2 + dx + (kx || 0) * dy, h / 2 + dy + (ky || 0) * dx]
}

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Transform: which handles a selected drawing shows (the right-click menu's
// Transform → Handles), and what dragging them does.
//   resize  the box's eight handles (and the rotate handle)
//   shape   a block arrow's head length and width and its shaft's thickness
//           (adj.headLen / headW / shaft), a rounded rectangle's corners
//           (adj.r), a triangle's apex (adj.apex)
//   tips    a block arrow's two ends, put anywhere: the box stretches and
//           turns between them
//   skew    leaning the box sideways or up and down (skew: [kx, ky])
//   bend    curving a block arrow's shaft (bend, a fraction of the box's
//           height; the box grows so the arrow keeps its thickness)
// Edit points turns a shape into a path with a handle on every corner.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
.import "rig_shapes.js" as Shapes

var MODE_LABELS = { resize: "Resize", shape: "Shape", tips: "Tips", skew: "Skew", bend: "Bend" }

function _isArrow(n) {
    return isDraw(n) && (n.shape === "arrow" || n.shape === "arrow2")
}

// The handle modes that make sense for a drawing, Resize first.
function transformModesFor(n) {
    if (!isDraw(n) || isTable(n) || isLine(n))
        return []
    var out = ["resize"]
    if (_isArrow(n) || n.shape === "roundrect" || n.shape === "triangle")
        out.push("shape")
    if (_isArrow(n))
        out.push("tips")
    if (!isPath(n))
        out.push("skew")
    if (_isArrow(n))
        out.push("bend")
    return out
}

function setTransformMode(mode) {
    transformMode = mode || "resize"
    bump()
}

function canEditPoints(n) {
    return isDraw(n) && ["rect", "roundrect", "ellipse", "triangle", "diamond", "arrow", "arrow2"]
        .indexOf(n.shape || "rect") >= 0
}

function hasShaping(n) {
    return !!(n && (n.adj || n.bend || n.skew))
}

// --- skew ---------------------------------------------------------------------------

function _skewOf(n) {
    var k = n && n.skew
    return { kx: k ? Number(k[0]) || 0 : 0, ky: k ? Number(k[1]) || 0 : 0 }
}

// The drawing's skew as a matrix about its middle, for its transform.
function skewMatrix(n, w, h) {
    var k = _skewOf(n)
    return Qt.matrix4x4(1, k.kx, 0, -k.kx * h / 2,
                        k.ky, 1, 0, -k.ky * w / 2,
                        0, 0, 1, 0,
                        0, 0, 0, 1)
}

// A point in the drawing's own (unskewed) box from one in its wrapper.
function _unskew(n, x, y, w, h) {
    var k = _skewOf(n)
    var dx = x - w / 2
    var dy = y - h / 2
    var det = 1 - k.kx * k.ky
    if (Math.abs(det) < 0.01)
        det = 0.01
    return [w / 2 + (dx - k.kx * dy) / det, h / 2 + (dy - k.ky * dx) / det]
}

// --- where the handles are ------------------------------------------------------------

function _flipPt(n, x, y, w, h) {
    return [n.flipH ? w - x : x, n.flipV ? h - y : y]
}

// The handles for the current mode, in the drawing's own box (the box is
// skewed with them): [{name, x, y}].
function transformHandles(n, w, h) {
    tick
    if (!n || transformMode === "resize")
        return []
    var out = []
    function add(name, p) {
        var q = _flipPt(n, p[0], p[1], w, h)
        out.push({ name: name, x: q[0], y: q[1] })
    }
    if (transformMode === "skew") {
        out.push({ name: "skewX", x: w / 2, y: 0 })
        out.push({ name: "skewY", x: w, y: h / 2 })
        return out
    }
    if (transformMode === "shape") {
        if (_isArrow(n)) {
            var m = Shapes.arrowMeasures(n.shape, w, h, n.adj, n.bend)
            var c = Shapes.arrowCurve(w, m)
            var ts = Shapes.arrowHeadTs(n.shape, w, h, n.adj, n.bend)
            var pe = c.at(ts.tEnd)
            var ue = c.up(ts.tEnd)
            add("head", [pe[0] + ue[0] * m.H / 2, pe[1] + ue[1] * m.H / 2])
            var tm = (ts.tStart + ts.tEnd) / 2
            var pm = c.at(tm)
            var um = c.up(tm)
            add("shaft", [pm[0] + um[0] * m.S / 2, pm[1] + um[1] * m.S / 2])
        } else if (n.shape === "roundrect") {
            add("radius", [Shapes.roundRadius(n, w, h), 0])
        } else if (n.shape === "triangle") {
            add("apex", [Shapes.triangleApex(n) * w, 0])
        }
        return out
    }
    if (!_isArrow(n))
        return out
    if (transformMode === "tips") {
        add("tipA", [0, h / 2])
        add("tipB", [w, h / 2])
    } else if (transformMode === "bend") {
        var mb = Shapes.arrowMeasures(n.shape, w, h, n.adj, n.bend)
        add("bend", Shapes.arrowCurve(w, mb).at(0.5))
    }
    return out
}

// The handle at (px, py) in the drawing's wrapper, or "".
function transformHandleAt(n, px, py, w, h) {
    var hs = transformHandles(n, w, h)
    var k = _skewOf(n)
    for (var i = 0; i < hs.length; i++) {
        var p = Shapes.skewPt(hs[i].x, hs[i].y, w, h, k.kx, k.ky)
        if (Math.hypot(px - p[0], py - p[1]) < 8)
            return hs[i].name
    }
    return ""
}

// --- dragging them ---------------------------------------------------------------------

function _wrapperOf(n) {
    var i = nodeIndex(n.id)
    return (i >= 0 && _chips) ? _chips.itemAt(i) : null
}

// Editor point of a point in the drawing's own box.
function _toEditor(n, x, y, w, h) {
    var k = _skewOf(n)
    var q = Shapes.skewPt(x, y, w, h, k.kx, k.ky)
    var g = drawGeom(n)
    var r = Shapes.rotatePt(q[0] - w / 2, q[1] - h / 2, n.rot || 0)
    return [g.x + g.w / 2 + r.x, g.y + g.h / 2 + r.y]
}

function dragTransform(n, name, mx, my) {
    if (!isDraw(n) || isLocked(n))
        return
    var g = drawGeom(n)
    var w = g.w
    var h = g.h
    var s = spaceRect()
    if (name === "skewX" || name === "skewY") {
        var c = Shapes.rotatePt(mx - (g.x + w / 2), my - (g.y + h / 2), -(n.rot || 0))
        var k = _skewOf(n)
        if (name === "skewX")
            k.kx = Math.max(-1.5, Math.min(1.5, -c.x / Math.max(1, h / 2)))
        else
            k.ky = Math.max(-1.5, Math.min(1.5, c.y / Math.max(1, w / 2)))
        if (Math.abs(k.kx) < 0.03) k.kx = 0
        if (Math.abs(k.ky) < 0.03) k.ky = 0
        if (k.kx || k.ky)
            n.skew = [k.kx, k.ky]
        else
            delete n.skew
        return
    }
    if (name === "tipA" || name === "tipB") {
        var a = _toEditor(n, n.flipH ? w : 0, h / 2, w, h)
        var b = _toEditor(n, n.flipH ? 0 : w, h / 2, w, h)
        var p = snapEnt(mx, my, altHeld)
        if (name === "tipA")
            a = [p.x, p.y]
        else
            b = [p.x, p.y]
        var len = Math.max(16, Math.hypot(b[0] - a[0], b[1] - a[1]))
        var deg = Math.atan2(b[1] - a[1], b[0] - a[0]) * 180 / Math.PI
        if (shiftHeld)
            deg = Math.round(deg / rotateSnap) * rotateSnap
        var cx = (a[0] + b[0]) / 2
        var cy = (a[1] + b[1]) / 2
        n.fx = xToFx(cx - len / 2)
        n.fy = yToFy(cy - h / 2)
        n.fw = len / Math.max(1, s.w)
        n.rot = Shapes.normDeg(deg)
        delete n.flipH
        delete n.skew
        n.around = []
        return
    }
    // The pointer in the drawing's own, unflipped box.
    var it = _wrapperOf(n)
    if (!it)
        return
    var lp = it.mapFromItem(_ed, mx, my)
    var q = _unskew(n, lp.x, lp.y, w, h)
    q = _flipPt(n, q[0], q[1], w, h)
    var adj = n.adj ? JSON.parse(JSON.stringify(n.adj)) : {}
    if (name === "radius") {
        adj.r = Math.max(0, Math.min(0.5, q[0] / Math.max(1, Math.min(w, h))))
        n.adj = adj
        return
    }
    if (name === "apex") {
        adj.apex = Math.max(0, Math.min(1, q[0] / Math.max(1, w)))
        n.adj = adj
        return
    }
    var m = Shapes.arrowMeasures(n.shape, w, h, n.adj, n.bend)
    var curve = Shapes.arrowCurve(w, m)
    var ts = Shapes.arrowHeadTs(n.shape, w, h, n.adj, n.bend)
    if (name === "head") {
        var pe = curve.at(ts.tEnd)
        var ue = curve.up(ts.tEnd)
        var across = Math.abs((q[0] - pe[0]) * ue[0] + (q[1] - pe[1]) * ue[1])
        adj.headLen = Math.max(0.05, Math.min(n.shape === "arrow2" ? 0.48 : 0.95, (w - q[0]) / Math.max(1, w)))
        adj.headW = Math.max(0.1, Math.min(1, 2 * across / Math.max(1, m.T)))
        if (!(adj.shaft > 0))
            adj.shaft = m.S / Math.max(1, m.T)
        adj.shaft = Math.min(adj.shaft, adj.headW)
        n.adj = adj
        return
    }
    if (name === "shaft") {
        var tm = (ts.tStart + ts.tEnd) / 2
        var pm = curve.at(tm)
        var um = curve.up(tm)
        var half = Math.abs((q[0] - pm[0]) * um[0] + (q[1] - pm[1]) * um[1])
        if (!(adj.headW > 0))
            adj.headW = m.H / Math.max(1, m.T)
        adj.shaft = Math.max(0.05, Math.min(adj.headW, 2 * half / Math.max(1, m.T)))
        n.adj = adj
        return
    }
    if (name === "bend") {
        // How far the shaft's middle is from the straight line (up is +).
        var off = m.mid - q[1]
        var bend = off / (m.T + 2 * Math.abs(off))
        bend = Math.max(-0.4, Math.min(0.4, bend))
        if (Math.abs(bend) < 0.02)
            bend = 0
        _setBend(n, bend, m.T)
    }
}

// Sets a block arrow's bend, growing or shrinking its box about its middle
// so the arrow keeps thickness T.
function _setBend(n, bend, T) {
    var g = drawGeom(n)
    var s = spaceRect()
    var newH = T / (1 - 2 * Math.abs(bend))
    var cy = g.y + g.h / 2
    n.fh = newH / Math.max(1, s.h)
    n.fy = yToFy(cy - newH / 2)
    if (bend)
        n.bend = bend
    else
        delete n.bend
}

// --- Edit points and Reset shape ---------------------------------------------------------

// Turns the selected shape into a path through its corners, as it looks now
// (shaped, bent, skewed, flipped and turned), keeping its colours.
function convertToPath() {
    var n = nodeAt(selectedId)
    if (!canEditPoints(n) || isLocked(n))
        return
    var g = drawGeom(n)
    var outline = Shapes.shapeOutline(n, g.w, g.h)
    var pts = outline.pts.map(function(p) {
        var f = _flipPt(n, p[0], p[1], g.w, g.h)
        return _toEditor(n, f[0], f[1], g.w, g.h)
    })
    n.shape = "path"
    n.closed = true
    n.smooth = outline.smooth
    n.headStart = "none"
    n.headEnd = "none"
    delete n.adj
    delete n.bend
    delete n.skew
    setPathPoints(n, pts)
    transformMode = "resize"
    bump()
}

// Back to the plain shape: no shaping, bend or skew (a bent arrow's box
// shrinks back to its thickness).
function resetShape() {
    var n = nodeAt(selectedId)
    if (!n || isLocked(n))
        return
    if (n.bend) {
        var g = drawGeom(n)
        var m = Shapes.arrowMeasures(n.shape, g.w, g.h, n.adj, n.bend)
        _setBend(n, 0, m.T)
    }
    delete n.adj
    delete n.skew
    bump()
}

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Drawings: geometry, resizing, default style, drawing new shapes and painting them.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
.import "rig_shapes.js" as Shapes

function isDraw(n) {
    return !!(n && n.kind === "draw")
}

function isTable(n) {
    return !!(n && n.kind === "draw" && n.shape === "table")
}

function isText(n) {
    return !!(n && n.kind === "draw" && n.shape === "text")
}

function drawGeom(n) {
    var pad = (n && n.pad > 0) ? n.pad : 8
    var around = (n && n.around) ? n.around : []
    if (around.length) {
        var minx = 1e9
        var miny = 1e9
        var maxx = -1e9
        var maxy = -1e9
        var k
        for (k = 0; k < around.length; k++) {
            var q = nodeAt(around[k])
            if (!q || isDraw(q))
                continue
            var b = chipBounds(q)
            minx = Math.min(minx, b.x)
            miny = Math.min(miny, b.y)
            maxx = Math.max(maxx, b.x + b.w)
            maxy = Math.max(maxy, b.y + b.h)
        }
        if (minx < 1e8)
            return { x: minx - pad, y: miny - pad, w: (maxx - minx) + pad * 2, h: (maxy - miny) + pad * 2 }
    }
    return {
        x: fxToX(n && n.fx ? n.fx : 0),
        y: fyToY(n && n.fy ? n.fy : 0),
        w: fwToW(n && n.fw ? n.fw : 0.08),
        h: fhToH(n && n.fh ? n.fh : 0.06)
    }
}

// A line's end, a new line and an Arrow line's end turn in 45 degree steps
// with Shift (07 S146); the rotate grip keeps rotateSnap.
var LINE_SNAP = 45

// The drawing's flip at the press of the current resize, so dragging back
// over the opposite edge mirrors it back (07 S149). Keyed on the gesture's
// snapshot and the box at the press: the same key is the same press state.
var _rzPress = null

function _pressFlip(n) {
    var key = n.id + "|" + rzX0 + "|" + rzY0 + "|" + rzX1 + "|" + rzY1
    if (!_rzPress || _rzPress.key !== key || _rzPress.snap !== _gestureSnap)
        _rzPress = { key: key, snap: _gestureSnap, flipH: !!n.flipH, flipV: !!n.flipV }
    return _rzPress
}

// A drawing's skew as [kx, ky] numbers.
function _skewPair(n) {
    var k = n && n.skew
    return { kx: k ? Number(k[0]) || 0 : 0, ky: k ? Number(k[1]) || 0 : 0 }
}

// altOff is kept for the forwarder's signature; snapping off is Ctrl now
// (snapOffHeld, 07 S142) and Alt resizes from the centre (07 S141).
function applyDrawResize(n, mx, my, handle, altOff) {
    if (!n)
        return
    n.around = []
    var p = snapEnt(mx, my, snapOffHeld)
    if (handle === "end0" || handle === "end1") {
        // A line end: Shift keeps the line on 45 degree steps around the other end.
        var e = lineEndsAt(n)
        var px = p.x
        var py = p.y
        var ox = handle === "end0" ? e.bx : e.ax
        var oy = handle === "end0" ? e.by : e.ay
        if (shiftHeld) {
            var s = Shapes.snapAngle(ox, oy, px, py, LINE_SNAP)
            px = s.x
            py = s.y
        }
        if (handle === "end0")
            setLineEnds(n, px, py, e.bx, e.by)
        else
            setLineEnds(n, e.ax, e.ay, px, py)
        return
    }
    if (cropId === n.id && isOverlay(n)) {
        // Crop mode: the handles cut the picture; what stays does not move.
        // Shift on a corner keeps the crop's proportions (07 S148). The drag
        // works on the crop as seen, so a flipped picture's side you see is
        // the side that moves.
        var start = { x: rzX0, y: rzY0, w: rzX1 - rzX0, h: rzY1 - rzY0 }
        var c0 = Shapes.cropOf(cropStart)
        var seen = Shapes.cropFromDrag(start, n.rot || 0, Shapes.cropSeen(c0, n.flipH, n.flipV), handle, mx, my,
                                       shiftHeld && handle.length === 2)
        _applyCrop(n, start, c0, Shapes.cropSeen(seen, n.flipH, n.flipV))
        return
    }
    if (handle === "rotate") {
        // The handle above the top edge: the angle round the centre, 15 degree
        // steps with Shift.
        var gr = drawGeom(n)
        var a = Shapes.handleAngle(gr.x + gr.w / 2, gr.y + gr.h / 2, mx, my)
        n.rot = shiftHeld ? Shapes.snapDeg(a, rotateSnap) : Math.round(a * 10) / 10
        return
    }
    // A corner keeps the box's proportions at the press on pictures and
    // shapes, Shift frees it; text boxes, callouts and tables the other way
    // round. Sides stretch one way, Shift or not (07 S141).
    var corner = handle.length === 2
    var keepFirst = !isText(n) && !isTable(n)
    var press = _pressFlip(n)
    var k = _skewPair(n)
    var rot = Shapes.normDeg(n.rot || 0)
    // Snapping only lines up with the grid when the box is level and square.
    var level = rot === 0 && !k.kx && !k.ky
    var minW = isTable(n) ? Math.max(8, tableMinW(n)) : 8
    var minH = isTable(n) ? Math.max(8, tableMinH(n)) : 8
    var b = Shapes.boxResize({ x: rzX0, y: rzY0, w: rzX1 - rzX0, h: rzY1 - rzY0 }, rot, handle,
                             level ? p.x : mx, level ? p.y : my, {
                                 keep: corner && (keepFirst !== shiftHeld),
                                 centre: altHeld,
                                 kx: k.kx, ky: k.ky,
                                 minW: minW, minH: minH
                             })
    var oldH = fhToH(n.fh || 0)
    n.fx = xToFx(b.x)
    n.fy = yToFy(b.y)
    n.fw = b.w / Math.max(1, spaceRect().w)
    n.fh = b.h / Math.max(1, spaceRect().h)
    // Past the opposite edge the drawing mirrors (07 S149).
    if (isFlippable(n)) {
        _setFlag(n, "flipH", press.flipH !== b.flipX)
        _setFlag(n, "flipV", press.flipV !== b.flipY)
    }
    _scaleTextFont(n, oldH, b.h)
}

function _setFlag(n, key, on) {
    if (on)
        n[key] = true
    else
        delete n[key]
}

// A text box set to scale its font follows its new height.
function _scaleTextFont(n, oldH, newH) {
    if (isText(n) && n.scaleFont && oldH > 1) {
        var fs = n.fontSize > 0 ? n.fontSize : 12
        n.fontSize = Math.max(6, Math.min(72, Math.round(fs * (newH / oldH))))
    }
}

// Sets a picture's crop, moving its box so what stays visible stays put.
// c0 and c1 are stored crops; the box moves by the crop as seen, so a
// flipped picture's cut sides move on the side they show (07 S148).
function _applyCrop(n, box, c0, c1) {
    var b = Shapes.cropBox(box, n.rot || 0, Shapes.cropSeen(c0, n.flipH, n.flipV),
                           Shapes.cropSeen(c1, n.flipH, n.flipV))
    n.fx = xToFx(b.x)
    n.fy = yToFy(b.y)
    n.fw = b.w / Math.max(1, spaceRect().w)
    n.fh = b.h / Math.max(1, spaceRect().h)
    if (c1.l || c1.t || c1.r || c1.b)
        n.crop = { l: c1.l, t: c1.t, r: c1.r, b: c1.b }
    else
        delete n.crop
    syncOverlayChips(n)
}

// Crop mode for the selected picture: its handles cut instead of scale.
// Entering it records the picture's crop and box for Esc (cancelCrop).
function toggleCrop() {
    var n = nodeAt(selectedId)
    cropId = (isOverlay(n) && cropId !== n.id && !isLocked(n)) ? n.id : ""
    cropEnterSnap = cropId ? {
        id: n.id,
        crop: n.crop ? { l: n.crop.l, t: n.crop.t, r: n.crop.r, b: n.crop.b } : null,
        fx: n.fx, fy: n.fy, fw: n.fw, fh: n.fh
    } : null
    bump()
}

// Enter in crop mode: keeps the crop and leaves crop mode (07 S148).
function finishCrop() {
    if (!cropId)
        return
    cropId = ""
    cropEnterSnap = null
    bump()
}

// Esc in crop mode: the crop and box as they were when crop mode started,
// then out of crop mode. Nothing changed, no undo step (bump's step is the
// same as the last one).
function cancelCrop() {
    if (!cropId)
        return
    var snap = cropEnterSnap
    var n = snap ? nodeAt(snap.id) : null
    if (n && isOverlay(n)) {
        if (snap.crop)
            n.crop = { l: snap.crop.l, t: snap.crop.t, r: snap.crop.r, b: snap.crop.b }
        else
            delete n.crop
        n.fx = snap.fx
        n.fy = snap.fy
        n.fw = snap.fw
        n.fh = snap.fh
        syncOverlayChips(n)
    }
    cropId = ""
    cropEnterSnap = null
    bump()
}

// One side of the selected picture's crop, in percent of the picture.
function setCropEdge(edge, pct) {
    var n = nodeAt(selectedId)
    if (!isOverlay(n) || isLocked(n))
        return
    var c0 = Shapes.cropOf(n.crop)
    var c1 = Shapes.cropOf(n.crop)
    c1[edge] = Math.max(0, Number(pct) || 0) / 100
    c1 = Shapes.clampCrop(c1)
    _applyCrop(n, drawGeom(n), c0, c1)
    bump()
}

function resetCrop() {
    var n = nodeAt(selectedId)
    if (!isOverlay(n) || isLocked(n) || !n.crop)
        return
    _applyCrop(n, drawGeom(n), Shapes.cropOf(n.crop), Shapes.cropOf(null))
    bump()
}

// Shapes, lines and pictures turn; text boxes and tables stay level.
// Lines turn by their ends; tables stay upright.
function isRotatable(n) {
    return isDraw(n) && !isTable(n) && !isLine(n)
}

function isFlippable(n) {
    return isDraw(n) && !isTable(n) && !isText(n)
}

// Sets the selected drawings' angle (typed in the menu).
function setRotation(deg) {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (isRotatable(n) && !isLocked(n))
            n.rot = Shapes.normDeg(deg)
    }
    bump()
}

// Mirrors the selected drawings left to right ("h") or top to bottom ("v").
// A line's ends move; shapes and pictures keep a flag their drawing follows.
function flipSelection(axis) {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!isFlippable(n) || isLocked(n))
            continue
        if (isLine(n)) {
            var e = (n.ends && n.ends.length === 4) ? n.ends : [0, 0.5, 1, 0.5]
            n.ends = axis === "h" ? [1 - e[0], e[1], 1 - e[2], e[3]] : [e[0], 1 - e[1], e[2], 1 - e[3]]
            continue
        }
        var key = axis === "h" ? "flipH" : "flipV"
        if (n[key])
            delete n[key]
        else
            n[key] = true
    }
    bump()
}

// A drawn shape's outline points in its w x h box (as the painter draws it).
function shapeOutlinePts(n, w, h) {
    return Shapes.shapeOutline(n, w, h).pts
}

function _drawStyle() {
    return {
        kind: "draw",
        rot: 0,
        fill: "hollow",
        color: "#14532D",
        border: "#22C55E",
        stroke: 2,
        opacity: 1,
        pad: 8,
        around: []
    }
}

function addDrawAround(shape) {
    var ids = selectedIds || []
    var around = []
    var i
    for (i = 0; i < ids.length; i++) {
        var q = nodeAt(ids[i])
        if (q && !isDraw(q))
            around.push(ids[i])
    }
    if (!around.length)
        return
    var st = _drawStyle()
    st.id = _uid("d")
    st.shape = shape
    st.around = around
    var g = drawGeom(st)
    st.fx = xToFx(g.x)
    st.fy = yToFy(g.y)
    st.fw = g.w / Math.max(1, spaceRect().w)
    st.fh = g.h / Math.max(1, spaceRect().h)
    insertBelowChips(st)
    setSelection([st.id])
    bump()
}

// New drawings go on top of the other drawings, under the chips; a text box
// goes on top of everything.
function addDrawFree(shape, x0, y0, x1, y1) {
    // A callout is a text box with a pointer (rig_callout.js).
    var callout = shape === "callout"
    if (callout)
        shape = "text"
    if (isLineTool(shape)) {
        addLineFree(shape, x0, y0, x1, y1)
        return
    }
    if (shiftHeld) {
        var lp = lockAspect(x0, y0, x1, y1)
        x1 = lp.x
        y1 = lp.y
    }
    // Alt while drawing: the press is the centre. Only for a drag with a
    // drawing tool, not a box made by a command (a callout beside a chip).
    var nb = _newShapeBox(x0, y0, x1, y1, altHeld && dragKind === "drawnew")
    var x = nb.x
    var y = nb.y
    var w = nb.w
    var h = nb.h
    if (w < 6 || h < 6)
        return
    var st = _drawStyle()
    st.id = _uid("d")
    st.shape = shape
    st.fx = xToFx(x)
    st.fy = yToFy(y)
    st.fw = w / Math.max(1, spaceRect().w)
    st.fh = h / Math.max(1, spaceRect().h)
    if (shape === "table") {
        st.fill = "filled"
        st.color = "#18181B"
        st.border = "#3F3F46"
        st.stroke = 1
        st.theme = "gremlin"
        st.cols = 2
        st.idCol = false
        st.fontSize = 10
        st.rows = [emptyTableRow(2)]
        var minW = tableMinW(st)
        var minH = tableMinH(st)
        if (w < minW)
            st.fw = minW / Math.max(1, spaceRect().w)
        if (h < minH)
            st.fh = minH / Math.max(1, spaceRect().h)
    }
    if (shape === "text") {
        st.fill = "filled"
        st.color = "#18181B"
        st.border = "#3F3F46"
        st.stroke = 1
        st.theme = "gremlin"
        st.text = "Text"
        st.textColor = "#E4E4E7"
        st.fontSize = 12
        st.bold = false
        st.align = "center"
        st.valign = "middle"
        st.fillOpacity = 1
        st.borderOpacity = 1
        st.wrap = true
        st.scaleFont = false
    }
    if (callout)
        st.tail = { fx: xToFx(x - w * 0.3), fy: yToFy(y + h * 2) }
    if (shape === "text")
        nodes.push(st)
    else
        insertBelowChips(st)
    setSelection([st.id])
    tableRow = 0
    tableCol = 0
    tableExtra = -1
    bump()
}

// The Line and Arrow tools draw a "line" drawing; Arrow starts with a solid
// head at the end.
function isLineTool(tool) {
    return tool === "line" || tool === "arrowline"
}

function addLineFree(tool, x0, y0, x1, y1) {
    if (shiftHeld) {
        var s = Shapes.snapAngle(x0, y0, x1, y1, LINE_SNAP)
        x1 = s.x
        y1 = s.y
    }
    if (Math.hypot(x1 - x0, y1 - y0) < 6)
        return
    var ln = _drawStyle()
    ln.id = _uid("d")
    ln.shape = "line"
    ln.headStart = "none"
    ln.headEnd = tool === "arrowline" ? "solid" : "none"
    setLineEnds(ln, x0, y0, x1, y1)
    insertBelowChips(ln)
    setSelection([ln.id])
    bump()
}

// Pointer position while drawing with a tool: Shift snaps a line's angle to
// 45 degree steps and keeps a shape's proportions (07 S146).
function drawToolPoint(x0, y0, x1, y1) {
    if (!shiftHeld)
        return Qt.point(x1, y1)
    if (isLineTool(drawTool)) {
        var s = Shapes.snapAngle(x0, y0, x1, y1, LINE_SNAP)
        return Qt.point(s.x, s.y)
    }
    return lockAspect(x0, y0, x1, y1)
}

// The box of a shape being drawn from the press (x0, y0) to (x1, y1): with
// Alt the press is its centre (07 S146), else a corner.
function _newShapeBox(x0, y0, x1, y1, centre) {
    var w = Math.abs(x1 - x0)
    var h = Math.abs(y1 - y0)
    if (centre)
        return { x: x0 - w, y: y0 - h, w: w * 2, h: h * 2 }
    return { x: Math.min(x0, x1), y: Math.min(y0, y1), w: w, h: h }
}

// The preview box of the shape being drawn (Alt draws it from the centre).
function drawNewBox() {
    return _newShapeBox(drawX0, drawY0, drawX1, drawY1, altHeld && !isLineTool(drawTool))
}

function setDrawTool(shape) {
    drawTool = (drawTool === shape) ? "" : shape
    pathDraft = []
    pathHover = null
}

function lockAspect(x0, y0, x1, y1) {
    var w = x1 - x0
    var h = y1 - y0
    var s = Math.max(Math.abs(w), Math.abs(h))
    if (s < 1)
        s = 1
    return Qt.point(x0 + (w >= 0 ? s : -s), y0 + (h >= 0 ? s : -s))
}

function requestDrawColor(field) {
    var n = nodeAt(selectedId)
    if (!isDraw(n))
        return
    var hex = "#E4E4E7"
    if (field === "border")
        hex = n.border || "#3F3F46"
    else if (field === "textColor")
        hex = n.textColor || "#E4E4E7"
    else
        hex = n.color || "#18181B"
    colorPickRequested(field, hex)
}

function paintDraw(ctx, n, w, h) {
    if (!n || n.shape === "image")
        return
    if (n.shape === "text")
        return
    if (n.shape === "table") {
        ctx.save()
        ctx.strokeStyle = ink(n.border || "#3F3F46")
        ctx.lineWidth = fixPx(1)
        ctx.fillStyle = ink(n.color || "#18181B")
        ctx.fillRect(0.5, 0.5, Math.max(1, w - 1), Math.max(1, h - 1))
        ctx.strokeRect(0.5, 0.5, Math.max(1, w - 1), Math.max(1, h - 1))
        ctx.beginPath()
        ctx.moveTo(w * 0.5, 0)
        ctx.lineTo(w * 0.5, h)
        ctx.moveTo(0, h * 0.5)
        ctx.lineTo(w, h * 0.5)
        ctx.stroke()
        ctx.restore()
        return
    }
    if (n.shape === "line") {
        paintLine(ctx, n, w, h)
        return
    }
    if (n.shape === "path") {
        paintPath(ctx, n, w, h)
        return
    }
    var stroke = fixPx(n.stroke || 2)
    var inset = stroke * 0.5 + 0.5
    var ww = Math.max(2, w - stroke)
    var hh = Math.max(2, h - stroke)
    var shape = n.shape || "rect"
    ctx.save()
    ctx.translate(inset, inset)
    ctx.beginPath()
    if (shape === "ellipse") {
        ctx.save()
        ctx.translate(ww * 0.5, hh * 0.5)
        ctx.scale(Math.max(0.5, ww * 0.5), Math.max(0.5, hh * 0.5))
        ctx.arc(0, 0, 1, 0, 6.2832)
        ctx.restore()
    } else if (shape === "triangle") {
        ctx.moveTo(ww * Shapes.triangleApex(n), 0)
        ctx.lineTo(ww, hh)
        ctx.lineTo(0, hh)
        ctx.closePath()
    } else if (shape === "diamond") {
        ctx.moveTo(ww * 0.5, 0)
        ctx.lineTo(ww, hh * 0.5)
        ctx.lineTo(ww * 0.5, hh)
        ctx.lineTo(0, hh * 0.5)
        ctx.closePath()
    } else if (shape === "roundrect") {
        var r = Shapes.roundRadius(n, ww, hh)
        ctx.moveTo(r, 0)
        ctx.lineTo(ww - r, 0)
        ctx.quadraticCurveTo(ww, 0, ww, r)
        ctx.lineTo(ww, hh - r)
        ctx.quadraticCurveTo(ww, hh, ww - r, hh)
        ctx.lineTo(r, hh)
        ctx.quadraticCurveTo(0, hh, 0, hh - r)
        ctx.lineTo(0, r)
        ctx.quadraticCurveTo(0, 0, r, 0)
        ctx.closePath()
    } else if (shape === "arrow" || shape === "arrow2") {
        var pts = Shapes.arrowOutline(shape, ww, hh, n.adj, n.bend)
        ctx.moveTo(pts[0][0], pts[0][1])
        for (var k = 1; k < pts.length; k++)
            ctx.lineTo(pts[k][0], pts[k][1])
        ctx.closePath()
    } else {
        ctx.rect(0, 0, ww, hh)
    }
    if (n.fill !== "hollow") {
        ctx.fillStyle = ink(n.color || "#14532D")
        ctx.fill()
    }
    ctx.strokeStyle = ink(n.border || "#22C55E")
    ctx.lineWidth = stroke
    if (n.dash)
        ctx.setLineDash(Shapes.dashFor(n.dash, stroke))
    ctx.stroke()
    ctx.restore()
}

// A line from its stored ends, with a solid or hollow head at either end.
// The line stops at a head's back edge so it never shows through a hollow one.
function paintLine(ctx, n, w, h) {
    var stroke = fixPx(n.stroke || 2)
    var e = Shapes.lineEnds(n.ends, w, h)
    var size = fixPx(Shapes.headSize(n.stroke || 2))
    var headA = isHead(n.headStart) ? Shapes.arrowHead(e.ax, e.ay, e.bx, e.by, size) : null
    var headB = isHead(n.headEnd) ? Shapes.arrowHead(e.bx, e.by, e.ax, e.ay, size) : null
    var from = headA ? headA.base : [e.ax, e.ay]
    var to = headB ? headB.base : [e.bx, e.by]
    var colour = ink(n.border || _drawStyle().border)
    ctx.save()
    ctx.strokeStyle = colour
    ctx.fillStyle = colour
    ctx.lineWidth = stroke
    ctx.lineCap = n.dash === "dot" ? "round" : "butt"
    if (n.dash)
        ctx.setLineDash(Shapes.dashFor(n.dash, stroke))
    ctx.beginPath()
    ctx.moveTo(from[0], from[1])
    ctx.lineTo(to[0], to[1])
    ctx.stroke()
    ctx.setLineDash([])
    ctx.lineCap = "butt"
    ctx.lineJoin = "miter"
    paintHead(ctx, headA, n.headStart)
    paintHead(ctx, headB, n.headEnd)
    ctx.restore()
}

function isHead(style) {
    return style === "solid" || style === "hollow"
}

function paintHead(ctx, head, style) {
    if (!head)
        return
    ctx.beginPath()
    ctx.moveTo(head.tip[0], head.tip[1])
    ctx.lineTo(head.left[0], head.left[1])
    ctx.lineTo(head.right[0], head.right[1])
    ctx.closePath()
    if (style === "hollow")
        ctx.stroke()
    else
        ctx.fill()
}

function isLine(n) {
    return isDraw(n) && n.shape === "line"
}

// A line's two ends in editor pixels.
function lineEndsAt(n) {
    var g = drawGeom(n)
    var e = Shapes.lineEnds(n.ends, g.w, g.h)
    return { ax: g.x + e.ax, ay: g.y + e.ay, bx: g.x + e.bx, by: g.y + e.by }
}

// Puts a line's ends at these editor pixels; its box follows with margin for
// the stroke and heads.
function setLineEnds(n, ax, ay, bx, by) {
    var b = Shapes.lineBox(ax, ay, bx, by, Shapes.lineMargin(n.stroke || 2))
    n.fx = xToFx(b.x)
    n.fy = yToFy(b.y)
    n.fw = b.w / Math.max(1, spaceRect().w)
    n.fh = b.h / Math.max(1, spaceRect().h)
    n.ends = b.ends
    n.around = []
}

// Swaps the start and end heads of the selected lines.
function swapLineHeads() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!isLine(n))
            continue
        var start = n.headStart || "none"
        n.headStart = n.headEnd || "none"
        n.headEnd = start
    }
    bump()
}

// Sets a style field on the selected drawings only (chips are left alone).
// A line's box is re-fitted when its width changes.
function applyDrawField(key, val) {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!isDraw(n))
            continue
        if (isLine(n)) {
            var e = lineEndsAt(n)
            n[key] = val
            setLineEnds(n, e.ax, e.ay, e.bx, e.by)
        } else if (isPath(n) && key === "stroke") {
            // A wider line needs more room round its points.
            var pts = pathPointsAt(n)
            n[key] = val
            setPathPoints(n, pts)
        } else {
            n[key] = val
        }
    }
    bump()
}

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Paths: drawings through several points, clicked one by one (the Path tool)
// or drawn freehand (the Freehand tool). A path keeps its points as
// fractions of its box (pts), so moving, resizing, turning and flipping work
// as for any drawing. It can be closed (and then filled), smooth, and carry
// arrowheads at its ends when open.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
.import "rig_shapes.js" as Shapes

function isPath(n) {
    return isDraw(n) && n.shape === "path"
}

function isPathTool(tool) {
    return tool === "path" || tool === "pen"
}

// A path's points in its own box (w x h), flips applied as the drawing is.
function pathLocal(n, w, h) {
    var rel = (n && n.pts) ? n.pts : []
    return rel.map(function(p) {
        var x = p[0] * w
        var y = p[1] * h
        return [n.flipH ? w - x : x, n.flipV ? h - y : y]
    })
}

// The points in editor pixels: turned about the box's middle.
function pathPointsAt(n) {
    var g = drawGeom(n)
    var local = pathLocal(n, g.w, g.h)
    var rot = n.rot || 0
    return local.map(function(p) {
        var r = Shapes.rotatePt(p[0] - g.w / 2, p[1] - g.h / 2, rot)
        return [g.x + g.w / 2 + r.x, g.y + g.h / 2 + r.y]
    })
}

// Puts a path through these editor points: a new box round them, the turn
// and flips taken into the points themselves.
function setPathPoints(n, pts) {
    var b = Shapes.pathBox(pts, Shapes.lineMargin(n.stroke || 2))
    n.fx = xToFx(b.x)
    n.fy = yToFy(b.y)
    n.fw = b.w / Math.max(1, spaceRect().w)
    n.fh = b.h / Math.max(1, spaceRect().h)
    n.pts = b.rel
    n.rot = 0
    delete n.flipH
    delete n.flipV
    n.around = []
}

function _newPath(pts, smooth, closed) {
    var st = _drawStyle()
    st.id = _uid("d")
    st.shape = "path"
    st.fill = "hollow"
    st.smooth = !!smooth
    st.closed = !!closed
    st.headStart = "none"
    st.headEnd = "none"
    setPathPoints(st, pts)
    insertBelowChips(st)
    setSelection([st.id])
    bump()
}

// --- the Path tool: click points, double-click or Enter to finish ------------------

function pathClick(mx, my) {
    var p = snapEnt(mx, my, altHeld)
    var draft = pathDraft.slice()
    // Back on the first point: a closed shape.
    if (draft.length >= 3 && Math.hypot(p.x - draft[0][0], p.y - draft[0][1]) < 10) {
        finishPath(true)
        return
    }
    if (shiftHeld && draft.length) {
        var last = draft[draft.length - 1]
        var s = Shapes.snapAngle(last[0], last[1], p.x, p.y, rotateSnap)
        p = { x: s.x, y: s.y }
    }
    draft.push([p.x, p.y])
    pathDraft = draft
    tick++
}

function pathHoverAt(mx, my) {
    pathHover = [mx, my]
    tick++
}

function finishPath(closed) {
    var pts = []
    var draft = pathDraft || []
    // A double-click adds the same point twice.
    for (var i = 0; i < draft.length; i++) {
        var last = pts.length ? pts[pts.length - 1] : null
        if (!last || Math.hypot(draft[i][0] - last[0], draft[i][1] - last[1]) > 3)
            pts.push(draft[i])
    }
    pathDraft = []
    pathHover = null
    if (pts.length >= 2)
        _newPath(pts, false, !!closed && pts.length >= 3)
    else
        tick++
}

function cancelPath() {
    pathDraft = []
    pathHover = null
    tick++
}

// --- the Freehand tool: draw while the button is down ------------------------------

function penStart(mx, my) {
    pathDraft = [[mx, my]]
    tick++
}

function penMove(mx, my) {
    var draft = pathDraft
    var last = draft[draft.length - 1]
    if (last && Math.hypot(mx - last[0], my - last[1]) < 3)
        return
    draft.push([mx, my])
    pathDraft = draft
    tick++
}

function penEnd() {
    var pts = Shapes.simplifyPath(pathDraft || [], 1.5)
    pathDraft = []
    if (pts.length >= 2)
        _newPath(pts, true, false)
    else
        tick++
}

// The tool's line so far, with the next segment to the pointer.
function paintPathDraft(ctx) {
    var draft = pathDraft || []
    if (!draft.length)
        return
    ctx.save()
    ctx.strokeStyle = handleFill
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(draft[0][0], draft[0][1])
    for (var i = 1; i < draft.length; i++)
        ctx.lineTo(draft[i][0], draft[i][1])
    if (drawTool === "path" && pathHover)
        ctx.lineTo(pathHover[0], pathHover[1])
    ctx.stroke()
    if (drawTool === "path") {
        ctx.fillStyle = handleFill
        for (var k = 0; k < draft.length; k++) {
            ctx.beginPath()
            ctx.arc(draft[k][0], draft[k][1], k === 0 ? 5 : 3, 0, 6.2832)
            ctx.fill()
        }
    }
    ctx.restore()
}

// --- painting, hitting and editing a path ------------------------------------------

function _trace(ctx, pts, smooth, closed) {
    ctx.moveTo(pts[0][0], pts[0][1])
    if (!smooth || pts.length < 3) {
        for (var i = 1; i < pts.length; i++)
            ctx.lineTo(pts[i][0], pts[i][1])
        if (closed)
            ctx.closePath()
        return
    }
    // Through the middles of the segments, bending at each point.
    var n = pts.length
    if (closed) {
        var m0 = [(pts[n - 1][0] + pts[0][0]) / 2, (pts[n - 1][1] + pts[0][1]) / 2]
        ctx.moveTo(m0[0], m0[1])
        for (var k = 0; k < n; k++) {
            var nx = pts[(k + 1) % n]
            ctx.quadraticCurveTo(pts[k][0], pts[k][1], (pts[k][0] + nx[0]) / 2, (pts[k][1] + nx[1]) / 2)
        }
        ctx.closePath()
        return
    }
    for (var j = 1; j < n - 1; j++)
        ctx.quadraticCurveTo(pts[j][0], pts[j][1], (pts[j][0] + pts[j + 1][0]) / 2, (pts[j][1] + pts[j + 1][1]) / 2)
    ctx.lineTo(pts[n - 1][0], pts[n - 1][1])
}

function paintPath(ctx, n, w, h) {
    var pts = pathLocal(n, w, h)
    // pathLocal flips; the drawing's canvas flips too, so undo it here.
    pts = pts.map(function(p) { return [n.flipH ? w - p[0] : p[0], n.flipV ? h - p[1] : p[1]] })
    if (pts.length < 2)
        return
    var stroke = fixPx(n.stroke || 2)
    var colour = ink(n.border || _drawStyle().border)
    var size = fixPx(Shapes.headSize(n.stroke || 2))
    var open = !n.closed
    var headA = open && isHead(n.headStart) ? Shapes.arrowHead(pts[0][0], pts[0][1], pts[1][0], pts[1][1], size) : null
    var last = pts.length - 1
    var headB = open && isHead(n.headEnd) ? Shapes.arrowHead(pts[last][0], pts[last][1], pts[last - 1][0], pts[last - 1][1], size) : null
    var line = pts.slice()
    if (headA)
        line[0] = headA.base
    if (headB)
        line[last] = headB.base
    ctx.save()
    ctx.lineJoin = "round"
    ctx.lineCap = n.dash === "dot" ? "round" : "butt"
    ctx.beginPath()
    _trace(ctx, line, !!n.smooth, !!n.closed)
    if (n.closed && n.fill === "filled") {
        ctx.fillStyle = ink(n.color || _drawStyle().color)
        ctx.fill()
    }
    ctx.strokeStyle = colour
    ctx.fillStyle = colour
    ctx.lineWidth = stroke
    if (n.dash)
        ctx.setLineDash(Shapes.dashFor(n.dash, stroke))
    ctx.stroke()
    ctx.setLineDash([])
    paintHead(ctx, headA, n.headStart)
    paintHead(ctx, headB, n.headEnd)
    ctx.restore()
}

// What is at (px, py) in the path's own box: a point handle ("pt3"), the
// path itself ("body"), or nothing.
function hitPath(n, px, py, w, h) {
    var pts = pathLocal(n, w, h)
    if (interactive && isSelected(n.id) && !isLocked(n) && !canTurnTogether()) {
        for (var i = 0; i < pts.length; i++) {
            if (Math.hypot(px - pts[i][0], py - pts[i][1]) < 7)
                return "pt" + i
        }
    }
    if (isLocked(n))
        return ""
    var near = Math.max(6, (n.stroke || 2) / 2 + 5)
    if (Shapes.distToPath(px, py, pts, !!n.closed) <= near)
        return "body"
    if (n.closed && n.fill === "filled" && Shapes.insidePolygon(px, py, pts))
        return "body"
    return ""
}

// Drags point i of the selected path to (mx, my).
function dragPathPoint(i, mx, my) {
    var n = nodeAt(selectedId)
    if (!isPath(n))
        return
    var pts = pathPointsAt(n)
    if (i < 0 || i >= pts.length)
        return
    var p = snapEnt(mx, my, altHeld)
    pts[i] = [p.x, p.y]
    setPathPoints(n, pts)
}

function togglePathClosed() {
    var n = nodeAt(selectedId)
    if (!isPath(n) || (n.pts || []).length < 3)
        return
    n.closed = !n.closed
    bump()
}

function togglePathSmooth() {
    var n = nodeAt(selectedId)
    if (!isPath(n))
        return
    n.smooth = !n.smooth
    bump()
}

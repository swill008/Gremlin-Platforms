// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Grid snapping, snapping to other items, and the alignment guides.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function snapWorld(w) {
    var g = gridSize
    if (!snapOn || g < 1)
        return w
    return Math.round(w / g) * g
}

function snapPx(v) {
    return worldToX(snapWorld(xToWorld(v)))
}

function nodeBox(n) {
    if (!n)
        return { x: 0, y: 0, w: 8, h: 8 }
    if (isDraw(n))
        return drawGeom(n)
    if (isGroup(n)) {
        return {
            x: fxToX(n.chipFx) + groupMinX(n),
            y: fyToY(n.chipFy) + groupMinY(n),
            w: Math.max(8, groupSpanW(n)),
            h: Math.max(8, groupSpanH(n))
        }
    }
    return chipBounds(n)
}

function clearMoveGuides() {
    guideX = -1
    guideY = -1
    guideXKind = ""
    guideYKind = ""
}

function guideSkipTarget(moving, other) {
    if (!other || !moving || other.id === moving.id)
        return true
    var ids = selectedIds || []
    var i
    for (i = 0; i < ids.length; i++) {
        if (ids[i] === other.id)
            return true
    }
    var pack = tablePackOf(moving)
    if (pack && tablePackOf(other) === pack)
        return true
    return false
}

function updateMoveGuides(n) {
    clearMoveGuides()
    if (!n || altHeld)
        return
    var s = spaceRect()
    var b = nodeBox(n)
    var slop = Style.dp(10)
    var cx = b.x + b.w * 0.5
    var cy = b.y + b.h * 0.5
    var left = b.x
    var right = b.x + b.w
    var top = b.y
    var bot = b.y + b.h
    var bestX = slop + 1
    var bestY = slop + 1
    var rankX = 9
    var rankY = 9
    function considerX(line, kind, rank, dist) {
        if (dist > slop)
            return
        if (rank < rankX || (rank === rankX && dist < bestX)) {
            guideX = line
            guideXKind = kind
            bestX = dist
            rankX = rank
        }
    }
    function considerY(line, kind, rank, dist) {
        if (dist > slop)
            return
        if (rank < rankY || (rank === rankY && dist < bestY)) {
            guideY = line
            guideYKind = kind
            bestY = dist
            rankY = rank
        }
    }
    var pageCx = s.x + s.w * 0.5
    var pageCy = s.y + s.h * 0.5
    considerX(pageCx, "center", 0, Math.abs(cx - pageCx))
    considerY(pageCy, "center", 0, Math.abs(cy - pageCy))
    // Ruler guides win: they were put there to line things up on.
    var rg = rulerGuideLines()
    var gi
    for (gi = 0; gi < rg.xs.length; gi++) {
        considerX(rg.xs[gi], "center", 0, Math.abs(cx - rg.xs[gi]))
        considerX(rg.xs[gi], "left", 0, Math.abs(left - rg.xs[gi]))
        considerX(rg.xs[gi], "right", 0, Math.abs(right - rg.xs[gi]))
    }
    for (gi = 0; gi < rg.ys.length; gi++) {
        considerY(rg.ys[gi], "center", 0, Math.abs(cy - rg.ys[gi]))
        considerY(rg.ys[gi], "top", 0, Math.abs(top - rg.ys[gi]))
        considerY(rg.ys[gi], "bottom", 0, Math.abs(bot - rg.ys[gi]))
    }
    considerX(s.x, "left", 2, Math.abs(left - s.x))
    considerX(s.x + s.w, "right", 2, Math.abs(right - (s.x + s.w)))
    considerY(s.y, "top", 2, Math.abs(top - s.y))
    considerY(s.y + s.h, "bottom", 2, Math.abs(bot - (s.y + s.h)))
    if (!snapEntOn)
        return
    var list = nodes || []
    var i
    for (i = 0; i < list.length; i++) {
        var o = list[i]
        if (guideSkipTarget(n, o))
            continue
        var ob = nodeBox(o)
        if (ob.w < 2 || ob.h < 2)
            continue
        var oL = ob.x
        var oR = ob.x + ob.w
        var oC = ob.x + ob.w * 0.5
        var oT = ob.y
        var oB = ob.y + ob.h
        var oM = ob.y + ob.h * 0.5
        considerX(oC, "center", 1, Math.abs(cx - oC))
        considerX(oL, "left", 3, Math.abs(left - oL))
        considerX(oR, "right", 3, Math.abs(right - oR))
        considerX(oL, "right", 3, Math.abs(right - oL))
        considerX(oR, "left", 3, Math.abs(left - oR))
        considerY(oM, "center", 1, Math.abs(cy - oM))
        considerY(oT, "top", 3, Math.abs(top - oT))
        considerY(oB, "bottom", 3, Math.abs(bot - oB))
        considerY(oT, "bottom", 3, Math.abs(bot - oT))
        considerY(oB, "top", 3, Math.abs(top - oB))
    }
}

function commitGuideSnap() {
    if (guideX < 0 && guideY < 0)
        return
    var n = nodeAt(selectedId)
    if (!n)
        return
    var b = nodeBox(n)
    var nx = b.x
    var ny = b.y
    if (guideXKind === "center")
        nx = guideX - b.w * 0.5
    else if (guideXKind === "left")
        nx = guideX
    else if (guideXKind === "right")
        nx = guideX - b.w
    if (guideYKind === "center")
        ny = guideY - b.h * 0.5
    else if (guideYKind === "top")
        ny = guideY
    else if (guideYKind === "bottom")
        ny = guideY - b.h
    var dx = nx - b.x
    var dy = ny - b.y
    if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5)
        return
    var pack = tablePackOf(n)
    if (pack) {
        moveTablePack(pack, dx / Math.max(1, spaceRect().w), dy / Math.max(1, spaceRect().h))
    } else if (isDraw(n)) {
        n.fx = xToFx(nx)
        n.fy = yToFy(ny)
        followTablePacked(n)
    } else {
        n.chipFx = xToFx(nx - (isGroup(n) ? groupMinX(n) : 0))
        n.chipFy = yToFy(ny - (isGroup(n) ? groupMinY(n) : 0))
    }
}

function snapPos(x, y, altOff) {
    if (altOff || !snapOn)
        return Qt.point(x, y)
    return Qt.point(worldToX(snapWorld(xToWorld(x))), worldToY(snapWorld(yToWorld(y))))
}

// The nearest of lines within d of v, or v.
function _nearLine(v, lines, d) {
    var best = v
    for (var i = 0; i < lines.length; i++) {
        var dd = Math.abs(v - lines[i])
        if (dd < d) {
            d = dd
            best = lines[i]
        }
    }
    return best
}

function snapEnt(x, y, altOff) {
    if (altOff)
        return Qt.point(x, y)
    var rg = rulerGuideLines()
    if (!snapEntOn) {
        var p = snapOn ? snapPos(x, y, false) : Qt.point(x, y)
        return Qt.point(_nearLine(p.x, rg.xs, 8), _nearLine(p.y, rg.ys, 8))
    }
    var xs = rg.xs.slice()
    var ys = rg.ys.slice()
    function ax(v) { xs.push(v) }
    function ay(v) { ys.push(v) }
    var list = nodes || []
    var i
    for (i = 0; i < list.length; i++) {
        var nn = list[i]
        if (dragKind && nn.id === selectedId)
            continue
        if (isDraw(nn)) {
            var g = drawGeom(nn)
            ax(g.x); ax(g.x + g.w); ax(g.x + g.w * 0.5)
            ay(g.y); ay(g.y + g.h); ay(g.y + g.h * 0.5)
            continue
        }
        var bb = chipBounds(nn)
        ax(bb.x); ax(bb.x + bb.w); ax(bb.x + bb.w * 0.5)
        ay(bb.y); ay(bb.y + bb.h); ay(bb.y + bb.h * 0.5)
        if (!isDraw(nn)) {
            var hp = hotPt(nn)
            ax(hp.x)
            ay(hp.y)
        }
    }
    function nearest(v, arr) {
        var best = v
        var d = 8
        var j
        for (j = 0; j < arr.length; j++) {
            var dd = Math.abs(v - arr[j])
            if (dd < d) {
                d = dd
                best = arr[j]
            }
        }
        if (snapOn) {
            var g2 = (arr === xs) ? worldToX(snapWorld(xToWorld(v))) : worldToY(snapWorld(yToWorld(v)))
            if (Math.abs(g2 - v) <= d)
                best = g2
        }
        return best
    }
    return Qt.point(nearest(x, xs), nearest(y, ys))
}

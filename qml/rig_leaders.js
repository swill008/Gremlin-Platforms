// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Leader lines: ends, spines (bend points), curves, drawing and hit distance.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function hotPt(n) {
    if (!n)
        return Qt.point(0, 0)
    return Qt.point(fxToX(hotFxOf(n)), fyToY(hotFyOf(n)))
}

function fromEnd(n) {
    if (n && n.from && n.from.type)
        return n.from
    return { type: "chip", id: n ? n.id : "", pin: n && n.pin ? n.pin : "right" }
}

function toEnd(n) {
    if (n && n.to && n.to.type)
        return n.to
    return { type: "hot", id: n ? n.id : "" }
}

function endPt(end) {
    if (!end)
        return Qt.point(0, 0)
    if (end.type === "free")
        return Qt.point(fxToX(end.fx || 0), fyToY(end.fy || 0))
    if (end.type === "member") {
        var gn = nodeAt(end.id)
        if (!gn || !gn.members || end.member < 0 || end.member >= gn.members.length)
            return chipXY(gn || {})
        var gm = gn.members[end.member]
        var gx = fxToX(gn.chipFx) + groupMinX(gn) + memberLocalX(gn, gm)
        var gy = fyToY(gn.chipFy) + groupMinY(gn) + memberLocalY(gn, gm)
        var gw = chipWGuess(gn, gm)
        var gh = chipH(gn)
        var pin = end.pin || "right"
        var px = pin === "left" ? gx : (pin === "top" || pin === "bottom" ? gx + gw * 0.5 : gx + gw)
        var py = pin === "top" ? gy : (pin === "bottom" ? gy + gh : gy + gh * 0.5)
        return Qt.point(px, py)
    }
    if (end.type === "chip") {
        var cn = nodeAt(end.id)
        var it = _chips.itemAt(nodeIndex(end.id))
        return pinPt(cn, it, end.pin)
    }
    if (end.type === "hot") {
        return hotPt(nodeAt(end.id))
    }
    return Qt.point(0, 0)
}

function _legacyLeader(n) {
    return {
        id: ((n && n.id) ? n.id : "n") + "_L0",
        from: fromEnd(n),
        to: toEnd(n),
        spines: (n && n.spines) ? n.spines : [],
        curve: n ? n.curve : true,
        fromCurve: n ? n.fromCurve : undefined
    }
}

function leaderList(n) {
    if (!n || n.kind === "draw")
        return []
    if (fiveWayFormat(n) === "radial") {
        if (n.leaders && n.leaders.length)
            return n.leaders
        return buildRadialLeaders(n)
    }
    if (n.leaders)
        return n.leaders
    return [_legacyLeader(n)]
}

function ensureLeaders(n) {
    if (!n || n.kind === "draw")
        return []
    if (n.leaders === undefined || n.leaders === null)
        n.leaders = [_legacyLeader(n)]
    return n.leaders
}

function currentLeader(n) {
    var ls = ensureLeaders(n)
    if (!ls.length)
        return null
    var i = selectedLeader
    if (i < 0 || i >= ls.length)
        i = 0
    return ls[i]
}

function hollowMarkPad(end) {
    if (!end)
        return null
    if (end.type === "hot") {
        var hn = nodeAt(end.id)
        if (!hn)
            return null
        if ((hn.hotFill || "filled") !== "hollow")
            return null
        var hs = hotSz(hn)
        var r = hs * 0.5 + 2
        if ((hn.hotShape || "round") === "square")
            return { shape: "square", hw: r, hh: r }
        return { shape: "round", r: r }
    }
    if (end.type === "chip" || end.type === "member") {
        var cn = nodeAt(end.id)
        if (!cn)
            return null
        var mem = null
        if (end.type === "member" && cn.members && end.member >= 0 && end.member < cn.members.length)
            mem = cn.members[end.member]
        if (!chipIsHollow(cn, mem))
            return null
        var w = chipWGuess(cn, mem)
        var h = chipH(cn, mem)
        var shape = styleVal(cn, mem, "chipShape", "round")
        if (shape === "square")
            return { shape: "square", hw: w * 0.5 + 1, hh: h * 0.5 + 1 }
        return { shape: "round", r: Math.min(w, h) * 0.5 + 1 }
    }
    return null
}

function pullToCircle(prev, center, r) {
    var dx = center.x - prev.x
    var dy = center.y - prev.y
    var len = Math.hypot(dx, dy)
    if (len < 0.001)
        return prev
    if (len <= r)
        return prev
    var u = r / len
    return Qt.point(center.x - dx * u, center.y - dy * u)
}

function pullToBox(prev, center, hw, hh) {
    var dx = center.x - prev.x
    var dy = center.y - prev.y
    if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001)
        return prev
    var tx = Math.abs(dx) < 0.001 ? 1e9 : hw / Math.abs(dx)
    var ty = Math.abs(dy) < 0.001 ? 1e9 : hh / Math.abs(dy)
    var t = Math.min(tx, ty)
    if (t > 1)
        return prev
    return Qt.point(center.x - t * dx, center.y - t * dy)
}

function clipHollowEnd(prev, tip, end) {
    var pad = hollowMarkPad(end)
    if (!pad)
        return tip
    if (end.type === "chip" || end.type === "member")
        return tip
    if (pad.shape === "square")
        return pullToBox(prev, tip, pad.hw, pad.hh)
    return pullToCircle(prev, tip, pad.r)
}

function pathPtsL(L) {
    if (!L)
        return []
    var pts = [endPt(L.from)]
    var spines = L.spines || []
    for (var s = 0; s < spines.length; s++) {
        pts.push(Qt.point(fxToX(spines[s].fx), fyToY(spines[s].fy)))
    }
    pts.push(endPt(L.to))
    if (pts.length >= 2) {
        pts[0] = clipHollowEnd(pts[1], pts[0], L.from)
        pts[pts.length - 1] = clipHollowEnd(pts[pts.length - 2], pts[pts.length - 1], L.to)
    }
    return pts
}

function pathPts(n) {
    return pathPtsL(leaderList(n)[0])
}

function segIsCurve(L, j) {
    if (!L)
        return true
    if (j <= 0) {
        if (L.fromCurve !== undefined)
            return L.fromCurve !== false
        return L.curve !== false
    }
    var sp = (L.spines || [])[j - 1]
    if (sp && sp.curve !== undefined)
        return sp.curve !== false
    return L.curve !== false
}

function setSegCurve(L, j, on) {
    if (!L)
        return
    if (j <= 0)
        L.fromCurve = on
    else if (L.spines && L.spines[j - 1])
        L.spines[j - 1].curve = on
    bump()
}

function toggleSegCurve() {
    var n = nodeAt(selectedId)
    if (!n)
        return
    var L = currentLeader(n)
    if (!L)
        return
    var j = selectedSeg
    if (j < 0)
        j = (selectedSpine >= 0) ? (selectedSpine + 1) : 0
    setSegCurve(L, j, !segIsCurve(L, j))
}

function setAllSegCurve(on) {
    var n = nodeAt(selectedId)
    if (!n)
        return
    var L = currentLeader(n)
    if (!L)
        return
    L.curve = on
    L.fromCurve = on
    var s = L.spines || []
    for (var i = 0; i < s.length; i++)
        s[i].curve = on
    if (selectedLeader === 0)
        n.curve = on
    bump()
}

function addLeader() {
    var n = nodeAt(selectedId)
    if (!n)
        return
    var ls = ensureLeaders(n)
    var src = ls.length ? (ls[selectedLeader] || ls[0]) : null
    if (!src) {
        ls.push(_legacyLeader(n))
        selectedLeader = 0
        bump()
        return
    }
    var a = endPt(src.from)
    ls.push({
        id: _uid("L"),
        from: {
            type: src.from && src.from.type ? src.from.type : "chip",
            id: src.from ? src.from.id : n.id,
            pin: src.from ? src.from.pin : (n.pin || "right"),
            fx: src.from ? src.from.fx : 0,
            fy: src.from ? src.from.fy : 0
        },
        to: {
            type: "free",
            fx: xToFx(a.x + 48),
            fy: yToFy(a.y + 36)
        },
        spines: [],
        curve: false,
        fromCurve: false
    })
    selectedLeader = ls.length - 1
    selectedSeg = 0
    bump()
}

function addBranch() {
    var n = nodeAt(selectedId)
    if (!n)
        return
    var ls = ensureLeaders(n)
    var src = ls.length ? (ls[selectedLeader] || ls[0]) : null
    if (!src)
        return
    var origin = (src.to && src.to.type === "free") ? src.to : src.from
    var p = endPt(origin)
    ls.push({
        id: _uid("L"),
        from: {
            type: origin && origin.type ? origin.type : "free",
            id: origin ? origin.id : "",
            pin: origin ? origin.pin : "",
            fx: origin ? origin.fx : xToFx(p.x),
            fy: origin ? origin.fy : yToFy(p.y)
        },
        to: {
            type: "free",
            fx: xToFx(p.x + 56),
            fy: yToFy(p.y - 44)
        },
        spines: [],
        curve: true,
        fromCurve: true
    })
    selectedLeader = ls.length - 1
    selectedSeg = 0
    bump()
}

function stripLeaders(n) {
    if (!n || isDraw(n))
        return
    n.leaders = []
    n.spines = []
    n.from = undefined
    n.to = undefined
}

function deleteLeader() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
    if (!ids.length && _ctx && _ctx.nodeId)
        ids = [_ctx.nodeId]
    var i
    var any = false
    for (i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n || isDraw(n))
            continue
        var ls = ensureLeaders(n)
        if (!ls.length) {
            stripLeaders(n)
            any = true
            continue
        }
        if (ids.length > 1) {
            stripLeaders(n)
            any = true
            continue
        }
        var li = selectedLeader
        if (li < 0 || li >= ls.length)
            li = 0
        ls.splice(li, 1)
        n.leaders = ls
        if (ls.length) {
            selectedLeader = Math.min(li, ls.length - 1)
            var L = ls[selectedLeader]
            n.spines = L.spines || []
            n.from = L.from
            n.to = L.to
        } else {
            stripLeaders(n)
            selectedLeader = 0
            selectedSpine = -1
        }
        any = true
    }
    if (any)
        bump()
}

function showLeaderHandles(n, li) {
    if (!interactive || !n || !isSelected(n.id))
        return false
    if (dragKind === "spine" && (dragLeader === li || selectedLeader === li))
        return true
    if (dragKind === "from" || dragKind === "to")
        return selectedLeader === li
    if (selectedLeader !== li)
        return false
    return selectedSpine >= 0 || selectedSeg >= 0
}

function drawMark(ctx, x, y, size, shape, fill, color) {
    var r = Math.max(2, size * 0.5)
    ctx.beginPath()
    if (shape === "square")
        ctx.rect(x - r, y - r, r * 2, r * 2)
    else
        ctx.arc(x, y, r, 0, 6.2832)
    if (fill === "hollow") {
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        ctx.stroke()
    } else {
        ctx.fillStyle = color
        ctx.fill()
    }
}

function nearestPin(item, mx, my) {
    if (!item)
        return "right"
    var p = item.mapFromItem(_ed, mx, my)
    var dl = Math.abs(p.x)
    var dr = Math.abs(item.width - p.x)
    var dt = Math.abs(p.y)
    var db = Math.abs(item.height - p.y)
    var m = Math.min(dl, dr, dt, db)
    if (m === dt) return "top"
    if (m === db) return "bottom"
    if (m === dl) return "left"
    return "right"
}

function attachNear(x, y) {
    var list = nodes || []
    var best = { type: "free", fx: xToFx(x), fy: yToFy(y) }
    var bestD = 16
    var i
    for (i = 0; i < list.length; i++) {
        var h = hotPt(list[i])
        var hd = Math.hypot(x - h.x, y - h.y)
        var lim = hotSz(list[i]) * 0.5 + 10
        if (hd < lim && hd < bestD) {
            bestD = hd
            best = { type: "hot", id: list[i].id }
        }
    }
    for (i = 0; i < list.length; i++) {
        var it = _chips.itemAt(i)
        if (!it)
            continue
        var p = it.mapFromItem(_ed, x, y)
        var dx = p.x < 0 ? -p.x : (p.x > it.width ? p.x - it.width : 0)
        var dy = p.y < 0 ? -p.y : (p.y > it.height ? p.y - it.height : 0)
        var cd = Math.hypot(dx, dy)
        if (cd < 14 && cd < bestD) {
            bestD = cd
            best = { type: "chip", id: list[i].id, pin: nearestPin(it, x, y) }
        }
    }
    return best
}

function detachEnd(which) {
    var n = nodeAt(selectedId)
    if (!n) return
    var L = currentLeader(n)
    if (!L)
        return
    var p = endPt(which === "to" ? L.to : L.from)
    var free = { type: "free", fx: xToFx(p.x), fy: yToFy(p.y) }
    if (which === "to") L.to = free
    else L.from = free
    if (selectedLeader === 0) {
        if (which === "to") n.to = free
        else n.from = free
    }
    bump()
}

function attachEndToSelf(which) {
    var n = nodeAt(selectedId)
    if (!n) return
    var L = currentLeader(n)
    if (!L)
        return
    if (which === "to") L.to = { type: "hot", id: n.id }
    else L.from = { type: "chip", id: n.id, pin: n.pin || "right" }
    if (selectedLeader === 0) {
        n.to = L.to
        n.from = L.from
    }
    bump()
}

function _clampPt(pts, i) {
    if (i < 0) return pts[0]
    if (i >= pts.length) return pts[pts.length - 1]
    return pts[i]
}

function _bezierCtrl(pts, i) {
    var p0 = _clampPt(pts, i - 1)
    var p1 = pts[i]
    var p2 = pts[i + 1]
    var p3 = _clampPt(pts, i + 2)
    return {
        c1x: p1.x + (p2.x - p0.x) / 6.0,
        c1y: p1.y + (p2.y - p0.y) / 6.0,
        c2x: p2.x - (p3.x - p1.x) / 6.0,
        c2y: p2.y - (p3.y - p1.y) / 6.0,
        x: p2.x,
        y: p2.y
    }
}

function strokeLeader(ctx, n, pts, L) {
    if (!pts || pts.length < 2) return
    if (!L)
        L = leaderList(n)[0]
    ctx.beginPath()
    ctx.moveTo(pts[0].x, pts[0].y)
    for (var j = 0; j < pts.length - 1; j++) {
        if (pts.length > 2 && segIsCurve(L, j)) {
            var c = _bezierCtrl(pts, j)
            ctx.bezierCurveTo(c.c1x, c.c1y, c.c2x, c.c2y, c.x, c.y)
        } else {
            ctx.lineTo(pts[j + 1].x, pts[j + 1].y)
        }
    }
    ctx.stroke()
}

function ensureMidSpine(n) {
    if (!n || n.kind === "draw")
        return
    if (n.spines && n.spines.length) {
        return
    }
    var L = currentLeader(n)
    if (!L)
        return
    var a = endPt(L.from)
    var b = endPt(L.to)
    if (L.spines && L.spines.length)
        return
    L.spines = [{ fx: xToFx((a.x + b.x) * 0.5), fy: yToFy((a.y + b.y) * 0.5), curve: L.curve !== false }]
    n.spines = L.spines
}

function addCurveSpine(n) {
    if (!n) return
    var L = currentLeader(n)
    if (!L)
        return
    L.curve = true
    var a = endPt(L.from)
    var b = endPt(L.to)
    var spines = L.spines || []
    if (spines.length) {
        a = Qt.point(fxToX(spines[spines.length - 1].fx), fyToY(spines[spines.length - 1].fy))
    }
    var dx = b.x - a.x
    var dy = b.y - a.y
    var len = Math.hypot(dx, dy) || 1
    var ox = -dy / len * 36
    var oy = dx / len * 36
    var mx = (a.x + b.x) * 0.5
    var my = (a.y + b.y) * 0.5
    var cx = width * 0.5
    var cy = height * 0.5
    var dPos = Math.hypot(mx + ox - cx, my + oy - cy)
    var dNeg = Math.hypot(mx - ox - cx, my - oy - cy)
    if (dPos > dNeg) {
        ox = -ox
        oy = -oy
    }
    if (!L.spines) L.spines = []
    L.spines.push({ fx: xToFx(mx + ox), fy: yToFy(my + oy), curve: true })
    n.spines = L.spines
    selectedId = n.id
    selectedSpine = L.spines.length - 1
    selectedLeader = Math.max(0, selectedLeader)
    selectedChanged()
    bump()
}

function _nearLeader(n, mx, my) {
    var ls = leaderList(n)
    var best = { leader: -1, seg: -1 }
    var bestD = 6
    var li
    for (li = 0; li < ls.length; li++) {
        var L = ls[li]
        var pts = pathPtsL(L)
        if (pts.length < 2)
            continue
        for (var j = 0; j < pts.length - 1; j++) {
            var d
            if (pts.length > 2 && segIsCurve(L, j)) {
                d = _distBezier(mx, my, pts, j)
            } else {
                d = _distSeg(mx, my, pts[j].x, pts[j].y, pts[j + 1].x, pts[j + 1].y)
            }
            if (d < bestD) {
                bestD = d
                best = { leader: li, seg: j }
            }
        }
    }
    return best
}

function _distBezier(mx, my, pts, j) {
    var c = _bezierCtrl(pts, j)
    var p1x = pts[j].x
    var p1y = pts[j].y
    var prevx = p1x
    var prevy = p1y
    var best = 1e9
    var steps = 8
    for (var s = 1; s <= steps; s++) {
        var tt = s / steps
        var u = 1 - tt
        var x = u*u*u*p1x + 3*u*u*tt*c.c1x + 3*u*tt*tt*c.c2x + tt*tt*tt*c.x
        var y = u*u*u*p1y + 3*u*u*tt*c.c1y + 3*u*tt*tt*c.c2y + tt*tt*tt*c.y
        var d = _distSeg(mx, my, prevx, prevy, x, y)
        if (d < best)
            best = d
        prevx = x
        prevy = y
    }
    return best
}

function _distSeg(px, py, x1, y1, x2, y2) {
    var dx = x2 - x1
    var dy = y2 - y1
    var len = dx * dx + dy * dy
    if (len < 1) {
        return Math.hypot(px - x1, py - y1)
    }
    var t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / len))
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
}

function clearAllSpines(id) {
    var n = nodeAt(id || selectedId)
    if (!n || isDraw(n))
        return
    var ls = ensureLeaders(n)
    var i
    for (i = 0; i < ls.length; i++)
        ls[i].spines = []
    n.spines = []
    selectedSpine = -1
    bump()
}

function addSpineAt(id, mx, my, forceCurve) {
    var n = nodeAt(id)
    if (!n) {
        return -1
    }
    if (!n.spines) {
        n.spines = []
    }
    var L = currentLeader(n)
    if (!L)
        return -1
    if (!L.spines)
        L.spines = []
    var pts = pathPtsL(L)
    var best = 0
    var bestD = 1e9
    for (var i = 0; i < pts.length - 1; i++) {
        var d = _distSeg(mx, my, pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y)
        if (d < bestD) {
            bestD = d
            best = i
        }
    }
    var spn = snapPos(mx, my, false)
    var curved = (forceCurve === true) ? true : segIsCurve(L, best)
    L.spines.splice(best, 0, { fx: xToFx(spn.x), fy: yToFy(spn.y), curve: curved })
    n.spines = L.spines
    selectedId = id
    selectedSpine = best
    selectedChanged()
    bump()
    return best
}

function deleteSpineAt(id, leader, index) {
    var n = nodeAt(id)
    if (!n || index === undefined || index < 0)
        return false
    selectedId = id
    if (leader !== undefined)
        selectedLeader = leader
    var L = currentLeader(n)
    if (!L || !L.spines || index >= L.spines.length)
        return false
    L.spines.splice(index, 1)
    n.spines = L.spines
    selectedSpine = -1
    bump()
    return true
}

function convertSelectedSpine() {
    var n = ctxTarget()
    var i = ctxSpineIndex()
    if (!n || i < 0)
        return
    selectedId = n.id
    if (_ctx)
        selectedLeader = _ctx.leader
    var L = currentLeader(n)
    if (!L || !L.spines || i >= L.spines.length)
        return
    L.spines[i].curve = !L.spines[i].curve
    n.spines = L.spines
    selectedSpine = i
    bump()
}

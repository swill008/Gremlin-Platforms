// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Hit testing: what is under the pointer, and band selection.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function hitTest(mx, my) {
    var list = nodes || []
    var i
    var n
    for (i = 0; i < list.length; i++) {
        n = list[i]
        if (isPinnable(n) && hitOverlayPin(n, mx, my))
            return { kind: "overlayPin", id: n.id, spine: -1 }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        if (!isGroup(n))
            continue
        var mi0 = memberHit(n, mx, my)
        if (mi0 < 0)
            continue
        if (groupEditId === n.id)
            return { kind: "member", id: n.id, spine: -1, member: mi0 }
        return { kind: "chip", id: n.id, spine: -1 }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        if (n.kind === "draw")
            continue
        var ls = leaderList(n)
        for (var li = 0; li < ls.length; li++) {
            var fp = endPt(ls[li].from)
            if (Math.hypot(mx - fp.x, my - fp.y) < 9) {
                return { kind: "from", id: n.id, spine: -1, leader: li }
            }
        }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        var ls2 = leaderList(n)
        for (var lj = 0; lj < ls2.length; lj++) {
            var te = ls2[lj].to || { type: "hot", id: n.id }
            var tp = endPt(te)
            if (te.type !== "hot" && Math.hypot(mx - tp.x, my - tp.y) < 9) {
                return { kind: "to", id: n.id, spine: -1, leader: lj }
            }
        }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        if (n.kind === "draw")
            continue
        var h = hotPt(n)
        if (Math.hypot(mx - h.x, my - h.y) < (hotSz(n) * 0.5 + 5)) {
            return { kind: "hot", id: n.id, spine: -1 }
        }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        var lss = leaderList(n)
        for (var lk = 0; lk < lss.length; lk++) {
            if (!showLeaderHandles(n, lk))
                continue
            var spines = lss[lk].spines || []
            for (var s = 0; s < spines.length; s++) {
                var sx = fxToX(spines[s].fx)
                var sy = fyToY(spines[s].fy)
                if (Math.hypot(mx - sx, my - sy) < 9) {
                    return { kind: "spine", id: n.id, spine: s, leader: lk }
                }
            }
        }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        if (isGroup(n) && groupEditId === n.id) {
            var mi = memberHit(n, mx, my)
            if (mi >= 0)
                return { kind: "member", id: n.id, spine: -1, member: mi }
        }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        if (isDraw(n))
            continue
        if (isGroup(n) && memberHit(n, mx, my) >= 0)
            return { kind: "chip", id: n.id, spine: -1 }
        var it = _chips.itemAt(i)
        if (!it) {
            continue
        }
        var p = it.mapFromItem(_ed, mx, my)
        if (p.x >= 0 && p.y >= 0 && p.x <= it.width && p.y <= it.height) {
            return { kind: "chip", id: list[i].id, spine: -1 }
        }
    }
    for (i = 0; i < list.length; i++) {
        n = list[i]
        if (!isDraw(n))
            continue
        var dh = hitDraw(n, mx, my)
        if (dh)
            return { kind: "draw", id: n.id, spine: -1, handle: dh }
    }
    for (i = 0; i < list.length; i++) {
        var seg = _nearLeader(list[i], mx, my)
        if (seg && seg.seg >= 0) {
            return { kind: "line", id: list[i].id, spine: -1, leader: seg.leader, seg: seg.seg }
        }
    }
    return { kind: "", id: "", spine: -1 }
}

function hitDraw(n, mx, my) {
    var i = nodeIndex(n.id)
    var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
    if (!it)
        return ""
    var p = it.mapFromItem(_ed, mx, my)
    var w = it.width
    var h = it.height
    if (tableCellHandlesOn(n)) {
        var cr = tableCurrentRect(n)
        var chs = [
            [cr.x, cr.y, "cell-nw"], [cr.x + cr.w, cr.y, "cell-ne"],
            [cr.x, cr.y + cr.h, "cell-sw"], [cr.x + cr.w, cr.y + cr.h, "cell-se"],
            [cr.x + cr.w * 0.5, cr.y, "cell-n"], [cr.x + cr.w * 0.5, cr.y + cr.h, "cell-s"],
            [cr.x, cr.y + cr.h * 0.5, "cell-w"], [cr.x + cr.w, cr.y + cr.h * 0.5, "cell-e"]
        ]
        var ct
        for (ct = 0; ct < chs.length; ct++) {
            if (Math.hypot(mx - chs[ct][0], my - chs[ct][1]) < 8)
                return chs[ct][2]
        }
    }
    if (interactive && isSelected(n.id) && !isLocked(n) && !tableCellHandlesOn(n)) {
        var hs = [
            [0, 0, "nw"], [w, 0, "ne"], [0, h, "sw"], [w, h, "se"],
            [w * 0.5, 0, "n"], [w * 0.5, h, "s"], [0, h * 0.5, "w"], [w, h * 0.5, "e"]
        ]
        var t
        for (t = 0; t < hs.length; t++) {
            if (Math.hypot(p.x - hs[t][0], p.y - hs[t][1]) < 8)
                return hs[t][2]
        }
    }
    if (isTable(n)) {
        var hitCell = tableCellAt(n, mx, my)
        if (hitCell.row >= 0 || hitCell.extra >= 0) {
            if (isLocked(n))
                return ""
            return "body"
        }
    }
    if (p.x < 0 || p.y < 0 || p.x > w || p.y > h)
        return ""
    if (isLocked(n))
        return ""
    if (n.shape === "image" || n.shape === "table" || n.shape === "text" || n.fill === "filled")
        return "body"
    var ring = Math.max(6, (n.stroke || 2) + 4)
    if (p.x <= ring || p.y <= ring || p.x >= w - ring || p.y >= h - ring)
        return "body"
    return ""
}

function memberHit(n, mx, my) {
    if (!isGroup(n))
        return -1
    var mem = n.members || []
    for (var i = mem.length - 1; i >= 0; i--) {
        var x = fxToX(n.chipFx) + groupMinX(n) + memberLocalX(n, mem[i])
        var y = fyToY(n.chipFy) + groupMinY(n) + memberLocalY(n, mem[i])
        var h = chipH(n, mem[i])
        var w = chipWGuess(n, mem[i])
        if (mx >= x && mx <= x + w && my >= y && my <= y + h)
            return i
    }
    return -1
}

function rectHitsBand(r, x0, y0, x1, y1) {
    if (!r)
        return false
    return r.x < x1 && r.x + r.w > x0 && r.y < y1 && r.y + r.h > y0
}

function tableHitsBand(n, x0, y0, x1, y1) {
    if (!isTable(n))
        return false
    if (rectHitsBand(drawGeom(n), x0, y0, x1, y1))
        return true
    var extras = n.extras || []
    var i
    for (i = 0; i < extras.length; i++) {
        if (rectHitsBand(tableExtraRect(n, i), x0, y0, x1, y1))
            return true
    }
    var r
    var c
    var rows = (n.rows && n.rows.length) ? n.rows.length : 0
    var cols = n.cols > 0 ? n.cols : 0
    for (r = 0; r < rows; r++) {
        for (c = 0; c < cols; c++) {
            if (tableCellIsFree(n, r, c) && rectHitsBand(tableCellRect(n, r, c), x0, y0, x1, y1))
                return true
        }
    }
    return false
}

function tablesUnderChips(chips) {
    var out = []
    var seen = {}
    var list = nodes || []
    var i
    var t
    for (i = 0; i < chips.length; i++) {
        var chip = chips[i]
        var b = chipBounds(chip)
        var cx = b.x + b.w * 0.5
        var cy = b.y + b.h * 0.5
        var j
        for (j = 0; j < list.length; j++) {
            t = list[j]
            if (!isTable(t) || seen[t.id])
                continue
            var g = drawGeom(t)
            var hit = cx >= g.x && cx <= g.x + g.w && cy >= g.y && cy <= g.y + g.h
            var ei
            var extras = t.extras || []
            for (ei = 0; !hit && ei < extras.length; ei++) {
                var er = tableExtraRect(t, ei)
                if (cx >= er.x && cx <= er.x + er.w && cy >= er.y && cy <= er.y + er.h)
                    hit = true
            }
            if (!hit)
                continue
            seen[t.id] = true
            out.push(t)
        }
    }
    return out
}

function selectBand(add) {
    var x0 = Math.min(bandX0, bandX1)
    var y0 = Math.min(bandY0, bandY1)
    var x1 = Math.max(bandX0, bandX1)
    var y1 = Math.max(bandY0, bandY1)
    var ids = add ? (selectedIds || []).slice() : []
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        var hit = false
        if (isTable(n)) {
            hit = tableHitsBand(n, x0, y0, x1, y1)
        } else {
            var it = _chips.itemAt(i)
            if (!it)
                continue
            var cx = it.x + it.width * 0.5
            var cy = it.y + it.height * 0.5
            hit = cx >= x0 && cx <= x1 && cy >= y0 && cy <= y1
        }
        if (hit && ids.indexOf(n.id) < 0)
            ids.push(n.id)
        if (hit && isTable(n)) {
            var pk = n.packed || []
            var p
            for (p = 0; p < pk.length; p++) {
                if (ids.indexOf(pk[p]) < 0)
                    ids.push(pk[p])
            }
            var pd = n.packedDraw || []
            for (p = 0; p < pd.length; p++) {
                if (ids.indexOf(pd[p]) < 0)
                    ids.push(pd[p])
            }
        }
        if (hit && n.packId && ids.indexOf(n.packId) < 0)
            ids.push(n.packId)
    }
    setSelection(ids)
}

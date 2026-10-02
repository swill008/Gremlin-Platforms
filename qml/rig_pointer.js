// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// What a pointer drag does to the item being dragged.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function applyPointer(mx, my, altOff) {
    if (!dragKind || dragKind === "band")
        return
    if (dragKind === "turn") {
        dragTurn(mx, my)
        return
    }
    if (dragKind.indexOf("draw-xf-") === 0) {
        dragTransform(nodeAt(selectedId), dragKind.slice(8), mx, my)
        tick++
        return
    }
    if (dragKind.indexOf("draw-pt") === 0) {
        dragPathPoint(parseInt(dragKind.slice(7), 10), mx, my)
        tick++
        return
    }
    if (dragKind === "draw-tail") {
        dragCalloutTip(nodeAt(selectedId), mx, my)
        tick++
        return
    }
    var n = nodeAt(selectedId)
    if (!n)
        return
    if (dragKind === "from" || dragKind === "to") {
        var ep2 = snapPos(mx, my, altOff)
        var fr2 = { type: "free", fx: xToFx(ep2.x), fy: yToFy(ep2.y) }
        var Ld = currentLeader(n)
        if (!Ld)
            return
        if (dragKind === "to") Ld.to = fr2
        else Ld.from = fr2
        if (selectedLeader === 0) {
            if (dragKind === "to") n.to = fr2
            else n.from = fr2
        }
    } else if (dragKind === "hot") {
        var hp = snapPos(mx, my, altOff)
        n.hotFx = xToFx(hp.x)
        n.hotFy = yToFy(hp.y)
    } else if (dragKind === "photo") {
        if (photoLocked)
            return
        var sPhoto = spaceRect()
        var dw = Math.max(1, sPhoto.w)
        var dh = Math.max(1, sPhoto.h)
        photoOffX = Math.max(-1, Math.min(1, dragOffX + (mx - photoDragX0) / dw))
        photoOffY = Math.max(-1, Math.min(1, dragOffY + (my - photoDragY0) / dh))
        return
    } else if (dragKind === "chip") {
        var cp = snapPos(mx - dragOffX, my - dragOffY, altOff)
        var fx = xToFx(cp.x)
        var fy = yToFy(cp.y)
        var dFx = fx - n.chipFx
        var dFy = fy - n.chipFy
        var pack = tablePackOf(n)
        if (!pack) {
            var ids0 = (selectedIds && selectedIds.length) ? selectedIds : [selectedId]
            var pi
            for (pi = 0; !pack && pi < ids0.length; pi++)
                pack = tablePackOf(nodeAt(ids0[pi]))
        }
        if (pack) {
            moveTablePack(pack, dFx, dFy)
        } else {
            var ids = (selectedIds && selectedIds.length) ? selectedIds : [selectedId]
            for (var i = 0; i < ids.length; i++) {
                var q = nodeAt(ids[i])
                if (!q || isLocked(q))
                    continue
                q.chipFx = clamp01(q.chipFx + dFx)
                q.chipFy = clamp01(q.chipFy + dFy)
                refreshChipPack(q)
            }
        }
    } else if (dragKind === "spine" && dragSpine >= 0) {
        var Ls = currentLeader(n)
        if (!Ls)
            return
        if (!Ls.spines) Ls.spines = []
        if (dragSpine < Ls.spines.length) {
            var sp = snapPos(mx, my, altOff)
            Ls.spines[dragSpine].fx = xToFx(sp.x)
            Ls.spines[dragSpine].fy = yToFy(sp.y)
        }
        n.spines = Ls.spines
    } else if (dragKind === "tablecell") {
        if (!isTable(n) || isLocked(n) || !tableHasTarget())
            return
        ensureTable(n)
        var cell = tableCurrentCell(n)
        if (!cell || !cell.free)
            return
        var rc0 = tableCurrentRect(n)
        var tp = snapEnt(mx - dragOffX, my - dragOffY, altOff)
        writeTablePartRect(n, cell, tp.x, tp.y, rc0.w, rc0.h)
    } else if (dragKind === "draw") {
        if (isLocked(n))
            return
        var packDraw = tablePackOf(n)
        var g0 = drawGeom(n)
        var np = snapEnt(mx - dragOffX, my - dragOffY, altOff)
        var ddx = np.x - g0.x
        var ddy = np.y - g0.y
        if (packDraw && !isTable(n)) {
            moveTablePack(packDraw, ddx / Math.max(1, spaceRect().w), ddy / Math.max(1, spaceRect().h))
            return
        }
        var around = n.around || []
        if (around.length) {
            var ai
            for (ai = 0; ai < around.length; ai++) {
                var qn = nodeAt(around[ai])
                if (!qn || isDraw(qn))
                    continue
                qn.chipFx = clamp01(qn.chipFx + ddx / Math.max(1, spaceRect().w))
                qn.chipFy = clamp01(qn.chipFy + ddy / Math.max(1, spaceRect().h))
            }
        } else {
            var oldFx = n.fx || 0
            var oldFy = n.fy || 0
            n.fx = xToFx(np.x)
            n.fy = yToFy(np.y)
            shiftIndependentParts(n, n.fx - oldFx, n.fy - oldFy)
        }
        followTablePacked(n)
        syncOverlayChips(n)
    } else if (dragKind.indexOf("cell-") === 0) {
        if (!isTable(n) || isLocked(n) || !tableHasTarget())
            return
        applyTableCellResize(n, mx, my, dragKind.slice(5), altOff)
    } else if (dragKind.indexOf("draw-") === 0) {
        if (isLocked(n))
            return
        var rzOldFx = n.fx || 0
        var rzOldFy = n.fy || 0
        applyDrawResize(n, mx, my, dragKind.slice(5), altOff)
        shiftIndependentParts(n, (n.fx || 0) - rzOldFx, (n.fy || 0) - rzOldFy)
        followTablePacked(n)
        syncOverlayChips(n)
    } else if (dragKind === "member" && n.members && dragMember >= 0 && dragMember < n.members.length) {
        var mp = snapPos(mx - dragOffX, my - dragOffY, altOff)
        var mm = n.members[dragMember]
        if (themeLayout(n)) {
            var g = themeGeom(n)
            var role = fiveWayRole(mm)
            var home = g[role] || g.center
            mm.offX = (mp.x - fxToX(n.chipFx) - home.x) / Math.max(1, spaceRect().w)
            mm.offY = (mp.y - fyToY(n.chipFy) - home.y) / Math.max(1, spaceRect().h)
        } else {
            bakeAlignToFree(n)
            mm.ox = xToFx(mp.x) - n.chipFx
            mm.oy = yToFy(mp.y) - n.chipFy
        }
    }
    if (n && (dragKind === "chip" || dragKind === "draw" || dragKind === "tablecell" || dragKind === "member"))
        updateMoveGuides(n)
    else
        clearMoveGuides()
    repaint()
}

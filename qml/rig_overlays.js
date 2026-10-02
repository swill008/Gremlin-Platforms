// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Image layers (overlays): adding, hover, pin/lock and snap points for chips.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function isOverlay(n) {
    return !!(n && n.kind === "draw" && n.shape === "image")
}

function isPinnable(n) {
    return isOverlay(n) || isTable(n) || isText(n)
}

function isLocked(n) {
    return !!(n && (n.pinned || n.locked))
}

function pinLocal() {
    return { x: -2, y: -18, w: 16, h: 16 }
}

function hitOverlayPin(n, mx, my) {
    if (!isPinnable(n) || !interactive)
        return false
    var i = nodeIndex(n.id)
    var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
    if (!it)
        return false
    var p = it.mapFromItem(_ed, mx, my)
    var r = pinLocal()
    return p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h
}

function overlayContains(n, mx, my) {
    if (!isPinnable(n))
        return false
    if (hitOverlayPin(n, mx, my))
        return true
    var i = nodeIndex(n.id)
    var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
    if (!it)
        return false
    var p = it.mapFromItem(_ed, mx, my)
    return p.x >= 0 && p.y >= 0 && p.x <= it.width && p.y <= it.height
}

function setOverlayHover(mx, my) {
    var list = nodes || []
    var id = ""
    var i
    for (i = list.length - 1; i >= 0; i--) {
        if (overlayContains(list[i], mx, my)) {
            id = list[i].id
            break
        }
    }
    if (overlayHoverId === id)
        return
    overlayHoverId = id
    bump()
}

function addOverlay(rel, fileUrl) {
    var st = _drawStyle()
    st.id = _uid("d")
    st.shape = "image"
    st.src = rel || ""
    st.srcUrl = fileUrl || ""
    st.locked = false
    st.pinned = false
    st.sockets = []
    st.fill = "filled"
    st.fx = 0.36
    st.fy = 0.28
    st.fw = 0.28
    st.fh = 0.28
    st.rot = 0
    st.opacity = 1
    insertBelowChips(st)
    setSelection([st.id])
    bump()
    return st.id
}

function pinTarget(id) {
    var n = nodeAt(id || selectedId)
    if (isDraw(n))
        return n
    var ids = selectedIds || []
    var i
    for (i = 0; i < ids.length; i++) {
        var q = nodeAt(ids[i])
        if (isTable(q))
            return q
    }
    return null
}

// Locks or unlocks an item (any kind); old layouts' "pinned" becomes locked.
function toggleLock(id) {
    var n = pinTarget(id) || nodeAt(id || selectedId)
    if (!n)
        return
    if (isLocked(n))
        delete n.locked
    else
        n.locked = true
    delete n.pinned
    plantSnap = false
    bump()
}

function beginPlantSnap() {
    var n = nodeAt(selectedId)
    if (!isOverlay(n))
        return
    plantSnap = true
    bump()
}

function addSocketAt(n, mx, my) {
    if (!isOverlay(n))
        return
    var g = drawGeom(n)
    var lx = mx
    var ly = my
    var rot = n.rot || 0
    if (rot) {
        var cx = g.x + g.w * 0.5
        var cy = g.y + g.h * 0.5
        var rad = -rot * Math.PI / 180
        var dx = mx - cx
        var dy = my - cy
        var c = Math.cos(rad)
        var s = Math.sin(rad)
        lx = cx + dx * c - dy * s
        ly = cy + dx * s + dy * c
    }
    var ux = (lx - g.x) / Math.max(1, g.w)
    var uy = (ly - g.y) / Math.max(1, g.h)
    ux = Math.max(0, Math.min(1, ux))
    uy = Math.max(0, Math.min(1, uy))
    if (!n.sockets)
        n.sockets = []
    n.sockets.push({ id: _uid("s"), ux: ux, uy: uy, chipId: "" })
    plantSnap = false
    bump()
}

function socketWorld(n, sock) {
    var g = drawGeom(n)
    var lx = g.x + (sock.ux || 0) * g.w
    var ly = g.y + (sock.uy || 0) * g.h
    var rot = n.rot || 0
    if (!rot)
        return Qt.point(lx, ly)
    var cx = g.x + g.w * 0.5
    var cy = g.y + g.h * 0.5
    var rad = rot * Math.PI / 180
    var dx = lx - cx
    var dy = ly - cy
    var c = Math.cos(rad)
    var s = Math.sin(rad)
    return Qt.point(cx + dx * c - dy * s, cy + dx * s + dy * c)
}

function syncOverlayChips(n) {
    if (!n || !n.sockets)
        return
    var i
    for (i = 0; i < n.sockets.length; i++) {
        var sock = n.sockets[i]
        if (!sock || !sock.chipId)
            continue
        var q = nodeAt(sock.chipId)
        if (!q || isDraw(q)) {
            sock.chipId = ""
            continue
        }
        var pt = socketWorld(n, sock)
        var bw = chipBounds(q)
        q.chipFx = xToFx(pt.x - bw.w * 0.5)
        q.chipFy = yToFy(pt.y - bw.h * 0.5)
    }
}

function unsnapChip(chipId) {
    var list = nodes || []
    var i, j
    for (i = 0; i < list.length; i++) {
        var ov = list[i]
        if (!ov.sockets)
            continue
        for (j = 0; j < ov.sockets.length; j++) {
            if (ov.sockets[j].chipId === chipId)
                ov.sockets[j].chipId = ""
        }
    }
}

function snapChipToSocket(chipId, mx, my) {
    if (!chipId)
        return false
    var list = nodes || []
    var best = null
    var bestD = Style.dp(28)
    var bi = -1
    var i, j
    for (i = 0; i < list.length; i++) {
        var ov = list[i]
        if (!isOverlay(ov) || !ov.sockets)
            continue
        for (j = 0; j < ov.sockets.length; j++) {
            var pt = socketWorld(ov, ov.sockets[j])
            var d = Math.hypot(mx - pt.x, my - pt.y)
            if (d < bestD) {
                bestD = d
                best = ov
                bi = j
            }
        }
    }
    if (!best)
        return false
    unsnapChip(chipId)
    best.sockets[bi].chipId = chipId
    syncOverlayChips(best)
    bump()
    return true
}

function clearSockets() {
    var n = nodeAt(selectedId)
    if (!isOverlay(n))
        return
    n.sockets = []
    bump()
}

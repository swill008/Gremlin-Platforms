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

// Only items on the plane being edited light up (S116).
function setOverlayHover(mx, my) {
    var list = nodes || []
    var id = ""
    var i
    for (i = list.length - 1; i >= 0; i--) {
        if (inEditPlane(list[i]) && overlayContains(list[i], mx, my)) {
            id = list[i].id
            break
        }
    }
    if (overlayHoverId === id)
        return
    overlayHoverId = id
    // Only a highlight: a redraw, never an undo step (07 S55a).
    repaint()
}

// The box a picture gets when added (page fractions): with its aspect
// (width / height) the same on-screen area at the picture's own shape, else
// a square. Reset Picture uses it too (D-07-RESET-PICTURE).
function freshPictureSize(aspect) {
    var fw = 0.28
    var fh = 0.28
    var a = Number(aspect || 0)
    if (a > 0) {
        var s = spaceRect()
        var ratio = Math.max(1, s.w) / Math.max(1, s.h)
        fh = Math.min(0.6, fw * ratio / a)
        fw = Math.min(0.6, fh * a / ratio)
    }
    return { fw: fw, fh: fh }
}

// opts (all optional): fx/fy, the picture's centre in page fractions (a drop
// point); aspect, its width / height, so the box fits the picture; noBump to
// add several pictures in one undo step; plane, "background" or
// "foreground" (default: the plane being edited, S62); fitFrame, fitted to
// the photo frame (Add Picture to Background…, S40).
function addOverlay(rel, fileUrl, opts) {
    opts = opts || {}
    var st = _drawStyle()
    st.id = _uid("d")
    st.shape = "image"
    st.src = rel || ""
    st.srcUrl = fileUrl || ""
    st.locked = false
    st.pinned = false
    st.sockets = []
    st.fill = "filled"
    var aspect = Number(opts.aspect || 0)
    var size = freshPictureSize(aspect)
    var fw = size.fw
    var fh = size.fh
    var cx = opts.fx === undefined ? 0.5 : clamp01(opts.fx)
    var cy = opts.fy === undefined ? 0.42 : clamp01(opts.fy)
    st.fx = Math.max(0, Math.min(1 - fw, cx - fw / 2))
    st.fy = Math.max(0, Math.min(1 - fh, cy - fh / 2))
    st.fw = fw
    st.fh = fh
    if (opts.fitFrame) {
        var fr = frameFit(aspect)
        st.fx = fr.fx
        st.fy = fr.fy
        st.fw = fr.fw
        st.fh = fr.fh
    }
    st.rot = 0
    st.opacity = 1
    insertInPlane(st, opts.plane || editPlane)
    setSelection([st.id])
    if (!opts.noBump)
        bump()
    return st.id
}

// Choose Picture… on a missing picture (07 S108): the item keeps its place,
// and with the new picture's aspect (width / height) its box takes that
// shape, keeping its width and centre, so the picture fills it (07 S140).
// With a crop, the part left showing sets the shape. One Undo step.
function repointPicture(id, rel, fileUrl, aspect) {
    var n = nodeAt(id)
    if (!n || n.shape !== "image" || !rel)
        return
    n.src = rel
    n.srcUrl = fileUrl || ""
    var a = Number(aspect || 0)
    if (a > 0 && n.fw > 0 && n.fh > 0) {
        var c = n.crop
        if (c) {
            var keepW = Math.max(0.02, 1 - (c.l || 0) - (c.r || 0))
            var keepH = Math.max(0.02, 1 - (c.t || 0) - (c.b || 0))
            a = a * keepW / keepH
        }
        var s = spaceRect()
        var ratio = Math.max(1, s.w) / Math.max(1, s.h)
        var cy = n.fy + n.fh / 2
        n.fh = n.fw * ratio / a
        n.fy = cy - n.fh / 2
    }
    bump()
}

// The photo frame (the middle photoWellFraction of the page) as page
// fractions, narrowed to a picture of width / height aspect (0: the whole
// frame), centred.
function frameFit(aspect) {
    var pad = (1 - photoWellFraction) / 2
    var fw = photoWellFraction
    var fh = photoWellFraction
    var a = Number(aspect || 0)
    if (a > 0) {
        var frameAspect = worldPageW / worldPageH
        if (a > frameAspect)
            fh = fw * frameAspect / a
        else
            fw = fh * a / frameAspect
    }
    return { fx: pad + (photoWellFraction - fw) / 2, fy: pad + (photoWellFraction - fh) / 2, fw: fw, fh: fh }
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

// The snap point on any picture (either plane, S122) within reach of
// (mx, my), as an editor point, or null: a leader end dropped there sits on it.
function socketNear(mx, my) {
    var list = nodes || []
    var best = null
    var bestD = Style.dp(12)
    for (var i = 0; i < list.length; i++) {
        var ov = list[i]
        if (!isOverlay(ov) || !ov.sockets || isHidden(ov))
            continue
        for (var j = 0; j < ov.sockets.length; j++) {
            var pt = socketWorld(ov, ov.sockets[j])
            var d = Math.hypot(mx - pt.x, my - pt.y)
            if (d < bestD) {
                bestD = d
                best = pt
            }
        }
    }
    return best
}

// The chips snapped to the picture's snap points (they follow it, P6a).
function socketChipIds(n) {
    var out = []
    var socks = (n && n.sockets) || []
    for (var i = 0; i < socks.length; i++) {
        if (socks[i] && socks[i].chipId)
            out.push(socks[i].chipId)
    }
    return out
}

function clearSockets() {
    var n = nodeAt(selectedId)
    if (!isOverlay(n))
        return
    n.sockets = []
    bump()
}

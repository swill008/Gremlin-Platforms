// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Callouts: text boxes with a pointer. The pointer's tip is a spot on the
// page (tail: {fx, fy}) or a chip (tail: {to: id}), where it follows the
// chip's edge nearest the box. Everything else is a text box's.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
.import "rig_shapes.js" as Shapes

function isCallout(n) {
    return isText(n) && !!n.tail
}

// The tip in editor pixels.
function calloutTip(n) {
    var t = n && n.tail
    if (!t)
        return null
    if (t.to) {
        var chip = nodeAt(t.to)
        if (chip && !isDraw(chip)) {
            var g = drawGeom(n)
            var cx = g.x + g.w / 2
            var cy = g.y + g.h / 2
            var b = nodeBox(chip)
            var inside = cx >= b.x && cx <= b.x + b.w && cy >= b.y && cy <= b.y + b.h
            if (inside)
                return { x: b.x + b.w / 2, y: b.y + b.h / 2 }
            return {
                x: Math.max(b.x, Math.min(b.x + b.w, cx)),
                y: Math.max(b.y, Math.min(b.y + b.h, cy))
            }
        }
    }
    return { x: fxToX(t.fx || 0), y: fyToY(t.fy || 0) }
}

// The tip in the callout's own coordinates (turned with it).
function calloutTipLocal(n, w, h) {
    var tip = calloutTip(n)
    if (!tip)
        return { x: w / 2, y: h / 2 }
    var g = drawGeom(n)
    var p = Shapes.rotatePt(tip.x - (g.x + g.w / 2), tip.y - (g.y + g.h / 2), -(n.rot || 0))
    return { x: p.x + w / 2, y: p.y + h / 2 }
}

// Box and pointer as one shape, filled and outlined like the text box.
function paintCallout(ctx, n, w, h, ox, oy) {
    var tl = calloutTipLocal(n, w, h)
    var pts = Shapes.calloutOutline(w, h, tl.x, tl.y, uiPx(18))
    // A theme gives the colours; without one, the box's own, falling back
    // to the default theme's.
    var themed = textThemeStyle(n.theme ? n : { theme: "gremlin" })
    ctx.save()
    ctx.translate(ox, oy)
    ctx.beginPath()
    ctx.moveTo(pts[0][0], pts[0][1])
    for (var i = 1; i < pts.length; i++)
        ctx.lineTo(pts[i][0], pts[i][1])
    ctx.closePath()
    var fa = (n.fillOpacity !== undefined && n.fillOpacity !== null) ? n.fillOpacity : 1
    if (fa > 0) {
        ctx.globalAlpha = fa
        ctx.fillStyle = ink(n.theme ? themed.fill : (n.color || themed.fill))
        ctx.fill()
    }
    var ba = (n.borderOpacity !== undefined && n.borderOpacity !== null) ? n.borderOpacity : 1
    if (ba > 0) {
        ctx.globalAlpha = ba
        ctx.lineJoin = "round"
        ctx.lineWidth = fixPx(n.stroke || 1)
        ctx.strokeStyle = ink(n.theme ? themed.border : (n.border || themed.border))
        ctx.stroke()
    }
    ctx.restore()
}

// Whether (mx, my) is on a selected callout's tip handle.
function onCalloutTip(n, mx, my) {
    if (!isCallout(n) || !interactive || !isSelected(n.id) || isLocked(n))
        return false
    var tip = calloutTip(n)
    return !!tip && Math.hypot(mx - tip.x, my - tip.y) < 9
}

function dragCalloutTip(n, mx, my) {
    if (!isCallout(n))
        return
    n.tail = { fx: xToFx(mx), fy: yToFy(my) }
}

// Dropping the tip on a chip attaches it there; elsewhere it stays put.
function dropCalloutTip(n, mx, my) {
    if (!isCallout(n))
        return
    var list = nodes || []
    for (var i = list.length - 1; i >= 0; i--) {
        var c = list[i]
        if (!c || isDraw(c) || isHidden(c))
            continue
        var b = nodeBox(c)
        if (mx >= b.x - 4 && mx <= b.x + b.w + 4 && my >= b.y - 4 && my <= b.y + b.h + 4) {
            n.tail = { to: c.id }
            return
        }
    }
}

function _selectedText() {
    var n = nodeAt(selectedId)
    return isText(n) ? n : null
}

// Gives the selected text box a pointer, below and left of it.
function addCalloutTail() {
    var n = _selectedText()
    if (!n || n.tail)
        return
    var g = drawGeom(n)
    n.tail = { fx: xToFx(g.x - g.w * 0.3), fy: yToFy(g.y + g.h * 2) }
    bump()
}

function removeCalloutTail() {
    var n = _selectedText()
    if (!n || !n.tail)
        return
    delete n.tail
    bump()
}

// An attached pointer stays where it points now, no longer following.
function detachCalloutTail() {
    var n = _selectedText()
    if (!n || !n.tail || !n.tail.to)
        return
    var tip = calloutTip(n)
    n.tail = { fx: xToFx(tip.x), fy: yToFy(tip.y) }
    bump()
}

// A callout beside a chip, pointing at it.
function addCalloutFor(chipId) {
    var chip = nodeAt(chipId)
    if (!chip || isDraw(chip))
        return
    var b = nodeBox(chip)
    var s = spaceRect()
    var w = uiPx(140)
    var h = uiPx(40)
    var x = b.x + b.w + uiPx(60)
    if (x + w > s.x + s.w)
        x = b.x - uiPx(60) - w
    var y = b.y - uiPx(60)
    addDrawFree("text", x, y, x + w, y + h)
    var n = nodeAt(selectedId)
    if (isText(n)) {
        // What the chip shows (its name or action); a group has no one name.
        n.text = isGroup(chip) ? "Callout" : (chipText(chip, null) || "Callout")
        n.tail = { to: chip.id }
        bump()
    }
}

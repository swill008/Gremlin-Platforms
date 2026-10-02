// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Hotspots: the mark on the photo for a chip's control. A chip's Hotspot
// section sets:
//   hotShape    round, square, diamond, triangle (pointing along the
//               leader), ring, target, crosshair, plus, x, pin, none
//   hotFill     filled, hollow, half
//   hotLine     outline width: thin, medium, thick
//   hotOpacity  0.25..1
//   hotHalo     a soft glow round it
//   hotNumber   the control's number inside
//   hotPress    the pressed colour while the control is held (hotPressColor)
//   hotPulse    a ring that grows from it on each press
//   hotLive     shown on the live map (off: only while editing)
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

var LINE_WIDTHS = { thin: 1, medium: 2, thick: 3.5 }
var PULSE_MS = 600

// Whether the control behind a chip (or any in a group) is held now.
function hotPressed(n) {
    if (!n || isDraw(n))
        return false
    if (isGroup(n)) {
        var mem = n.members || []
        for (var i = 0; i < mem.length; i++) {
            if (litOf(memberKind(n, mem[i]), mem[i].hwId))
                return true
        }
        return false
    }
    return litOf(leafKind(n.kind), n.hwId)
}

// Whether the hotspot shows at all: hidden from the Layers panel, or kept
// off the live map.
function hotShown(n) {
    if (hotHidden(n))
        return false
    if ((n.hotShape || "round") === "none")
        return false
    if (n.hotLive === false && !showChrome && !exporting)
        return false
    return true
}

// The way the last stretch of the chip's first leader runs into the
// hotspot, as a unit vector (for the triangle); straight up without one.
function _arrival(n, hot) {
    var ls = leaderList(n)
    for (var i = 0; i < ls.length; i++) {
        var pts = pathPtsL(ls[i])
        if (pts && pts.length >= 2) {
            var a = pts[pts.length - 2]
            var dx = hot.x - a.x
            var dy = hot.y - a.y
            var len = Math.hypot(dx, dy)
            if (len > 0.5)
                return { x: dx / len, y: dy / len }
        }
    }
    return { x: 0, y: 1 }
}

function _outline(ctx, shape, x, y, r, dir) {
    ctx.beginPath()
    if (shape === "square") {
        ctx.rect(x - r, y - r, r * 2, r * 2)
    } else if (shape === "diamond") {
        ctx.moveTo(x, y - r)
        ctx.lineTo(x + r, y)
        ctx.lineTo(x, y + r)
        ctx.lineTo(x - r, y)
        ctx.closePath()
    } else if (shape === "triangle") {
        // Its point on the control, its back towards the chip.
        var bx = x - dir.x * r * 1.8
        var by = y - dir.y * r * 1.8
        ctx.moveTo(x, y)
        ctx.lineTo(bx - dir.y * r, by + dir.x * r)
        ctx.lineTo(bx + dir.y * r, by - dir.x * r)
        ctx.closePath()
    } else if (shape === "pin") {
        // A map pin: its point on the control, its head above.
        var hy = y - r * 2.2
        ctx.moveTo(x, y)
        ctx.lineTo(x - r * 0.8, hy + r * 0.6)
        ctx.arc(x, hy, r, Math.PI * 0.8, Math.PI * 0.2, false)
        ctx.closePath()
    } else {
        ctx.arc(x, y, r, 0, 6.2832)
    }
}

// Paints one chip's hotspot at (x, y), size its diameter.
function paintHotspot(ctx, n, x, y, size, colour, selected) {
    var shape = n.hotShape || "round"
    var fill = n.hotFill || "filled"
    var lineW = LINE_WIDTHS[n.hotLine] || 2
    var pressed = hotPressed(n)
    var c = selected ? colour : ink(pressed && n.hotPress ? (n.hotPressColor || styleDefault("hotPressColor")) : colour)
    var r = Math.max(2, size * 0.5)
    if (n.hotNumber && !isGroup(n))
        r = Math.max(r, uiPx(8))
    var dir = _arrival(n, { x: x, y: y })
    ctx.save()
    ctx.globalAlpha = n.hotOpacity > 0 ? Math.min(1, n.hotOpacity) : 1
    ctx.lineWidth = lineW
    ctx.strokeStyle = c
    ctx.fillStyle = c
    ctx.lineCap = "round"
    if (n.hotHalo) {
        var base = ctx.globalAlpha
        ctx.globalAlpha = base * 0.25
        ctx.beginPath()
        ctx.arc(x, y, r * 2.2, 0, 6.2832)
        ctx.fill()
        ctx.globalAlpha = base * 0.15
        ctx.beginPath()
        ctx.arc(x, y, r * 3, 0, 6.2832)
        ctx.fill()
        ctx.globalAlpha = base
    }
    if (shape === "ring") {
        ctx.lineWidth = Math.max(lineW, r * 0.45)
        ctx.beginPath()
        ctx.arc(x, y, r * 0.8, 0, 6.2832)
        ctx.stroke()
    } else if (shape === "target") {
        ctx.beginPath()
        ctx.arc(x, y, r, 0, 6.2832)
        ctx.stroke()
        ctx.beginPath()
        ctx.arc(x, y, Math.max(1.5, r * 0.35), 0, 6.2832)
        ctx.fill()
    } else if (shape === "crosshair" || shape === "plus" || shape === "x") {
        if (shape === "crosshair") {
            ctx.beginPath()
            ctx.arc(x, y, r * 0.7, 0, 6.2832)
            ctx.stroke()
        }
        var k = shape === "x" ? r * 0.75 : r
        ctx.beginPath()
        if (shape === "x") {
            ctx.moveTo(x - k, y - k)
            ctx.lineTo(x + k, y + k)
            ctx.moveTo(x + k, y - k)
            ctx.lineTo(x - k, y + k)
        } else {
            ctx.moveTo(x - k, y)
            ctx.lineTo(x + k, y)
            ctx.moveTo(x, y - k)
            ctx.lineTo(x, y + k)
        }
        ctx.stroke()
    } else {
        _outline(ctx, shape, x, y, r, dir)
        if (fill === "hollow") {
            ctx.stroke()
        } else if (fill === "half") {
            ctx.stroke()
            ctx.save()
            ctx.beginPath()
            ctx.rect(x - r * 3, y - r * 4, r * 3, r * 8)
            ctx.clip()
            _outline(ctx, shape, x, y, r, dir)
            ctx.fill()
            ctx.restore()
        } else {
            ctx.fill()
        }
    }
    if (n.hotNumber && !isGroup(n) && n.hwId !== undefined) {
        var onFill = fill !== "hollow" && ["round", "square", "diamond", "pin"].indexOf(shape) >= 0
        ctx.fillStyle = onFill ? ink(styleDefault("color")) : c
        ctx.font = "bold " + Math.round(r * 1.1) + "px sans-serif"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        var ty = shape === "pin" ? y - r * 2.2 : y
        ctx.fillText(String(n.hwId), x, ty + 0.5)
    }
    // Pulse on press: a ring that grows and fades.
    var started = hotPulseAt[n.id]
    if (n.hotPulse && started) {
        var t = (Date.now() - started) / PULSE_MS
        if (t >= 0 && t < 1) {
            ctx.globalAlpha = (1 - t) * 0.8
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.arc(x, y, r + t * r * 3, 0, 6.2832)
            ctx.stroke()
        }
    }
    ctx.restore()
}

// On each live input change: note new presses of controls whose hotspot
// pulses, and keep the canvas redrawing while a pulse runs.
function hotPulseTick() {
    var list = nodes || []
    var now = Date.now()
    var next = {}
    var any = false
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        if (!n || isDraw(n) || !n.hotPulse)
            continue
        var down = hotPressed(n)
        next[n.id] = down
        if (down && !hotHeld[n.id]) {
            hotPulseAt[n.id] = now
            any = true
        }
    }
    hotHeld = next
    if (any)
        _hotPulseTimer.restart()
}

function hotPulsing() {
    var now = Date.now()
    for (var id in hotPulseAt) {
        if (hotPulseAt.hasOwnProperty(id) && now - hotPulseAt[id] < PULSE_MS)
            return true
    }
    return false
}

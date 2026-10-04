// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The print area: the part of the page that every export and print takes
// (PNG, JPG, PDF, Export Modes, Print). printArea is { fx, fy, fw, fh },
// fractions of the page (spaceRect), or null for the whole page. Alt+drag
// on an empty part of the map (or Edit > Set Print Area, then a drag)
// draws it; its frame's handles resize it and its border moves it. With a
// paper chosen in Print & Export (printAspect > 0) it keeps the paper's
// shape, so what it shows is what fills the page.

// Smallest area, in pixels on screen.
var _MIN = 12

function printAreaRect() {
    var s = spaceRect()
    var a = printArea
    if (!a || !(a.fw > 0) || !(a.fh > 0))
        return { x: s.x, y: s.y, w: s.w, h: s.h }
    return { x: s.x + a.fx * s.w, y: s.y + a.fy * s.h, w: a.fw * s.w, h: a.fh * s.h }
}

// A rectangle in the paper's shape: `edges` says which sides were dragged
// ("e", "nw", ...): the other sides stay; a side alone grows the other way
// round the middle.
function _shaped(r, edges) {
    var a = printAspect
    if (!(a > 0))
        return r
    var across = edges.indexOf("e") >= 0 || edges.indexOf("w") >= 0
    var down = edges.indexOf("n") >= 0 || edges.indexOf("s") >= 0
    var w = r.w
    var h = r.h
    if (across && !down) {
        h = w / a
    } else if (down && !across) {
        w = h * a
    } else if (w / a >= h) {
        h = w / a
    } else {
        w = h * a
    }
    var x = r.x
    var y = r.y
    if (edges.indexOf("w") >= 0)
        x = r.x + r.w - w
    else if (!across)
        x = r.x + (r.w - w) / 2
    if (edges.indexOf("n") >= 0)
        y = r.y + r.h - h
    else if (!down)
        y = r.y + (r.h - h) / 2
    return { x: x, y: y, w: w, h: h }
}

// Kept on the page: smaller if it doesn't fit (its shape kept), then moved
// in. null when too small to use.
function _onPage(r) {
    var s = spaceRect()
    var w = Math.abs(r.w)
    var h = Math.abs(r.h)
    var x = Math.min(r.x, r.x + r.w)
    var y = Math.min(r.y, r.y + r.h)
    var shrink = Math.min(1, s.w / Math.max(1, w), s.h / Math.max(1, h))
    if (shrink < 1) {
        x += (w - w * shrink) / 2
        y += (h - h * shrink) / 2
        w *= shrink
        h *= shrink
    }
    if (w < _MIN || h < _MIN)
        return null
    x = Math.max(s.x, Math.min(s.x + s.w - w, x))
    y = Math.max(s.y, Math.min(s.y + s.h - h, y))
    return { x: x, y: y, w: w, h: h }
}

function _toArea(r) {
    var s = spaceRect()
    return {
        fx: (r.x - s.x) / s.w,
        fy: (r.y - s.y) / s.h,
        fw: r.w / s.w,
        fh: r.h / s.h
    }
}

// Drawing a new area (Alt+drag, or after Set Print Area).
function beginPrintArea(x, y) {
    printAreaArm = false
    eaX0 = x
    eaY0 = y
    eaX1 = x
    eaY1 = y
}

function movePrintArea(x, y) {
    eaX1 = x
    eaY1 = y
}

// The area being drawn, as it will be kept: from where the drag started,
// in the paper's shape.
function drawnPrintRect() {
    var edges = (eaX1 < eaX0 ? "w" : "e") + (eaY1 < eaY0 ? "n" : "s")
    var r = {
        x: Math.min(eaX0, eaX1),
        y: Math.min(eaY0, eaY1),
        w: Math.abs(eaX1 - eaX0),
        h: Math.abs(eaY1 - eaY0)
    }
    return _shaped(r, edges)
}

function endPrintArea() {
    var r = _onPage(drawnPrintRect())
    if (!r)
        return
    printArea = _toArea(r)
    printAreaEdited(true)
}

// The frame dragged by a handle or its border: the new rectangle on screen,
// and which sides moved ("move" for the whole frame).
function setPrintAreaRect(x, y, w, h, edges) {
    var r = { x: x, y: y, w: w, h: h }
    if (edges && edges !== "move")
        r = _shaped(r, edges)
    r = _onPage(r)
    if (r)
        printArea = _toArea(r)
}

// A new paper or orientation: the area takes its shape round its middle,
// about as large as before; with none yet, the largest of that shape,
// centred on the page.
function reshapePrintArea() {
    var a = printAspect
    if (!(a > 0))
        return
    var s = spaceRect()
    var r
    if (!printArea) {
        var w = Math.min(s.w, s.h * a)
        r = { x: s.x + (s.w - w) / 2, y: s.y + (s.h - w / a) / 2, w: w, h: w / a }
    } else {
        var old = printAreaRect()
        var size = Math.sqrt(old.w * old.h)
        var nw = size * Math.sqrt(a)
        var nh = size / Math.sqrt(a)
        r = { x: old.x + (old.w - nw) / 2, y: old.y + (old.h - nh) / 2, w: nw, h: nh }
    }
    r = _onPage(r)
    if (!r)
        return
    printArea = _toArea(r)
    printAreaEdited(false)
}

function clearPrintArea() {
    if (!printArea)
        return
    printArea = null
    printAreaEdited(false)
}

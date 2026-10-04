// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The export area: the part of the page that every export and print takes
// (PNG, JPG, PDF, Export Modes, Print). exportArea is { fx, fy, fw, fh },
// fractions of the page (spaceRect), or null for the whole page. Alt+drag
// on an empty part of the map (or Edit > Set Export Area, then a drag)
// draws it; its frame's handles resize it and its border moves it.

// Smallest area, in pixels on screen.
var _MIN = 12

function exportAreaRect() {
    var s = spaceRect()
    var a = exportArea
    if (!a || !(a.fw > 0) || !(a.fh > 0))
        return { x: s.x, y: s.y, w: s.w, h: s.h }
    return { x: s.x + a.fx * s.w, y: s.y + a.fy * s.h, w: a.fw * s.w, h: a.fh * s.h }
}

// A rectangle on screen to the page's fractions, kept on the page.
function _toArea(x, y, w, h) {
    var s = spaceRect()
    var x0 = Math.max(s.x, Math.min(x, x + w))
    var y0 = Math.max(s.y, Math.min(y, y + h))
    var x1 = Math.min(s.x + s.w, Math.max(x, x + w))
    var y1 = Math.min(s.y + s.h, Math.max(y, y + h))
    if (x1 - x0 < _MIN || y1 - y0 < _MIN)
        return null
    return {
        fx: (x0 - s.x) / s.w,
        fy: (y0 - s.y) / s.h,
        fw: (x1 - x0) / s.w,
        fh: (y1 - y0) / s.h
    }
}

// Drawing a new area (Alt+drag, or after Set Export Area).
function beginExportArea(x, y) {
    exportAreaArm = false
    eaX0 = x
    eaY0 = y
    eaX1 = x
    eaY1 = y
}

function moveExportArea(x, y) {
    eaX1 = x
    eaY1 = y
}

function endExportArea() {
    var a = _toArea(eaX0, eaY0, eaX1 - eaX0, eaY1 - eaY0)
    if (!a)
        return
    exportArea = a
    exportAreaEdited(true)
}

// The frame dragged by a handle or its border: the new rectangle on screen.
function setExportAreaRect(x, y, w, h) {
    var a = _toArea(x, y, w, h)
    if (a)
        exportArea = a
}

function clearExportArea() {
    if (!exportArea)
        return
    exportArea = null
    exportAreaEdited(false)
}

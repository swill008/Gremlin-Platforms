// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Guides dragged out of the rulers: lines across the page that items and
// points snap to. Kept as page fractions, rulerGuidesX (vertical lines) and
// rulerGuidesY (horizontal lines), and saved with the device's view.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function _clampFrac(v) {
    return Math.max(0, Math.min(1, Number(v) || 0))
}

// axis "x": a vertical guide at a page fraction across; "y": horizontal.
function addRulerGuide(axis, frac) {
    var list = (axis === "x" ? rulerGuidesX : rulerGuidesY).slice()
    list.push(_clampFrac(frac))
    if (axis === "x")
        rulerGuidesX = list
    else
        rulerGuidesY = list
    rulerGuidesEdited()
    return list.length - 1
}

function moveRulerGuide(axis, index, frac) {
    var list = (axis === "x" ? rulerGuidesX : rulerGuidesY).slice()
    if (index < 0 || index >= list.length)
        return
    list[index] = _clampFrac(frac)
    if (axis === "x")
        rulerGuidesX = list
    else
        rulerGuidesY = list
}

function removeRulerGuide(axis, index) {
    var list = (axis === "x" ? rulerGuidesX : rulerGuidesY).slice()
    if (index < 0 || index >= list.length)
        return
    list.splice(index, 1)
    if (axis === "x")
        rulerGuidesX = list
    else
        rulerGuidesY = list
    rulerGuidesEdited()
}

function clearRulerGuides() {
    rulerGuidesX = []
    rulerGuidesY = []
    rulerGuidesEdited()
}

// The guide within a few pixels of (mx, my) as {axis, index}, or null.
function rulerGuideAt(mx, my) {
    if (!guidesOn)
        return null
    var s = spaceRect()
    if (mx < s.x - 4 || mx > s.x + s.w + 4 || my < s.y - 4 || my > s.y + s.h + 4)
        return null
    var i
    for (i = 0; i < rulerGuidesX.length; i++) {
        if (Math.abs(mx - fxToX(rulerGuidesX[i])) <= 4)
            return { axis: "x", index: i }
    }
    for (i = 0; i < rulerGuidesY.length; i++) {
        if (Math.abs(my - fyToY(rulerGuidesY[i])) <= 4)
            return { axis: "y", index: i }
    }
    return null
}

// Dragging a guide in the page; dropped off the page it goes.
function dragRulerGuide(axis, index, mx, my) {
    moveRulerGuide(axis, index, axis === "x" ? xToFx(mx) : yToFy(my))
}

function dropRulerGuide(axis, index, mx, my) {
    var s = spaceRect()
    var off = axis === "x" ? (mx < s.x || mx > s.x + s.w) : (my < s.y || my > s.y + s.h)
    // Back on its ruler counts as off the page too.
    if (face && face.rulersOn) {
        if (axis === "y" && face.viewY(my) <= face.rulerSize)
            off = true
        if (axis === "x" && face.viewX(mx) <= face.rulerSize)
            off = true
    }
    if (off)
        removeRulerGuide(axis, index)
    else
        rulerGuidesEdited()
}

// The guides in editor pixels, for snapping: {xs: [...], ys: [...]}.
function rulerGuideLines() {
    if (!guidesOn)
        return { xs: [], ys: [] }
    return {
        xs: rulerGuidesX.map(function(f) { return fxToX(f) }),
        ys: rulerGuidesY.map(function(f) { return fyToY(f) })
    }
}

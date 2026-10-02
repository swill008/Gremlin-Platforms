// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Page coordinates: world units, page fractions and editor pixels.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function spaceRect() {
    var pw = Math.max(1, worldPageW)
    var ph = Math.max(1, worldPageH)
    var scale = Math.min(width / pw, height / ph)
    var dw = pw * scale
    var dh = ph * scale
    return {
        x: (width - dw) * 0.5,
        y: (height - dh) * 0.5,
        w: dw,
        h: dh
    }
}

function innerPageRect() {
    var s = spaceRect()
    return {
        x: s.x + s.w * innerPadX,
        y: s.y + s.h * innerPadY,
        w: s.w * (innerPageW / worldPageW),
        h: s.h * (innerPageH / worldPageH)
    }
}

function clamp01(v) {
    return Math.max(0, Math.min(1, v))
}

function worldToX(wx) {
    return spaceRect().x + (wx / worldPageW) * spaceRect().w
}

function worldToY(wy) {
    return spaceRect().y + (wy / worldPageH) * spaceRect().h
}

function xToWorld(px) {
    return (px - spaceRect().x) / Math.max(1, spaceRect().w) * worldPageW
}

function yToWorld(py) {
    return (py - spaceRect().y) / Math.max(1, spaceRect().h) * worldPageH
}

function fxToX(fx) {
    var s = spaceRect()
    return s.x + (fx || 0) * s.w
}

function fyToY(fy) {
    var s = spaceRect()
    return s.y + (fy || 0) * s.h
}

function xToFx(px) {
    var s = spaceRect()
    return (px - s.x) / Math.max(1, s.w)
}

function yToFy(py) {
    var s = spaceRect()
    return (py - s.y) / Math.max(1, s.h)
}

function fwToW(fw) {
    return Math.max(8, (fw || 0) * spaceRect().w)
}

function fhToH(fh) {
    return Math.max(8, (fh || 0) * spaceRect().h)
}

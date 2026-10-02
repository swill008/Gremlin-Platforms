// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The background photo's pose (scale, offset, rotation) and its frame.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function viewCenterPage() {
    return Qt.point(xToFx(width * 0.5), yToFy(height * 0.5))
}

function clampPhotoScale(v) {
    var n = Number(v)
    if (!(n === n) || n <= 0)
        n = 1
    return Math.max(0.25, Math.min(4, n))
}

function clampPhotoOff(v) {
    var n = Number(v)
    if (!(n === n))
        n = 0
    return Math.max(-1, Math.min(1, n))
}

function applyPhotoPose(pose) {
    pose = pose || {}
    photoScale = clampPhotoScale(pose.scale)
    photoOffX = clampPhotoOff(pose.offX)
    photoOffY = clampPhotoOff(pose.offY)
    var r = Number(pose.rot)
    if (!(r === r))
        r = 0
    photoRot = r
    // Hidden and locked come only with a loaded pose; slider changes leave them.
    if (pose.hidden !== undefined)
        photoHidden = !!pose.hidden
    if (pose.locked !== undefined)
        photoLocked = !!pose.locked
    // So does the look: a loaded pose without it means none.
    if (pose.look !== undefined) {
        var look = pose.look || {}
        photoBright = _lookVal(look.bright, -1, 1)
        photoContrast = _lookVal(look.contrast, -1, 1)
        photoGrey = _lookVal(look.grey, 0, 1)
        photoFade = _lookVal(look.fade, 0, 0.9)
    }
    if (_photoWell)
        repaint()
}

function _lookVal(v, low, high) {
    var n = Number(v)
    if (!(n === n))
        n = 0
    return Math.max(low, Math.min(high, n))
}

// One of the photo's look values (Photo → Adjust photo): bright, contrast,
// grey or fade. An undo step follows when the slider rests.
function setPhotoLook(key, value) {
    if (key === "bright")
        photoBright = _lookVal(value, -1, 1)
    else if (key === "contrast")
        photoContrast = _lookVal(value, -1, 1)
    else if (key === "grey")
        photoGrey = _lookVal(value, 0, 1)
    else if (key === "fade")
        photoFade = _lookVal(value, 0, 0.9)
    notePhotoChange()
}

function resetPhotoLook() {
    photoBright = 0
    photoContrast = 0
    photoGrey = 0
    photoFade = 0
    notePhotoChange()
}

function resetPhotoPose() {
    photoScale = 1
    photoOffX = 0
    photoOffY = 0
    photoRot = 0
    movePhoto = false
    repaint()
}

function fitPhotoWell() {
    photoScale = 1
    repaint()
}

// The photo's pose as saved; hidden and locked only when on.
function photoBag() {
    var bag = {
        scale: photoScale,
        offX: photoOffX,
        offY: photoOffY,
        rot: photoRot
    }
    if (photoHidden)
        bag.hidden = true
    if (photoLocked)
        bag.locked = true
    if (photoBright)
        bag.bright = photoBright
    if (photoContrast)
        bag.contrast = photoContrast
    if (photoGrey)
        bag.grey = photoGrey
    if (photoFade)
        bag.fade = photoFade
    return bag
}

function pagePhotoRect() {
    return innerPageRect()
}

function toPhoto(mx, my) {
    return Qt.point(xToFx(mx), yToFy(my))
}

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
    if (_photoWell)
        repaint()
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

function photoBag() {
    return {
        scale: photoScale,
        offX: photoOffX,
        offY: photoOffY,
        rot: photoRot
    }
}

function pagePhotoRect() {
    return innerPageRect()
}

function toPhoto(mx, my) {
    return Qt.point(xToFx(mx), yToFy(my))
}

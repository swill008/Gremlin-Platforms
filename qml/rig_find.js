// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Press to find: while editing, pressing a control on the device selects its
// chip and brings it into view; a control not on the map is pointed out in
// the pool. Options → Button Map → Editing turns it on or off, and axes too.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

// An axis counts as pressed past this far from centre, and as let go again
// below the second value, so a resting axis that wobbles does not refire.
var AXIS_ON = 0.6
var AXIS_OFF = 0.3

// The device's controls as [{kind, hwId}]: the pool's list.
function _findControls() {
    var rows = (face && face.chipRows) ? face.chipRows : []
    var out = []
    for (var i = 0; i < rows.length; i++) {
        var r = rows[i]
        if (r && r.hwId !== undefined)
            out.push({ kind: leafKind(r.kind || "btn"), hwId: r.hwId })
    }
    return out
}

// Whether a control is pressed now; prev keeps axes pressed until they
// come back below AXIS_OFF.
function _findPressed(kind, hwId, prev) {
    if (!face)
        return false
    if (kind === "axis") {
        if (!findAxes)
            return false
        var v = Math.abs(face.hwAxis(hwId))
        return prev ? v > AXIS_OFF : v > AXIS_ON
    }
    if (kind === "hat")
        return face.hwHat(hwId) > 0.5
    return face.hwButton(hwId) > 0.5
}

// Runs on every live input change.
function findTick() {
    if (!interactive || !findOn || exporting) {
        findPrev = ({})
        return
    }
    var controls = _findControls()
    var next = {}
    var hit = null
    for (var i = 0; i < controls.length; i++) {
        var c = controls[i]
        var key = c.kind + ":" + c.hwId
        var was = !!findPrev[key]
        var now = _findPressed(c.kind, c.hwId, was)
        if (now)
            next[key] = true
        if (now && !was && !hit)
            hit = c
    }
    findPrev = next
    if (hit)
        findControl(hit.kind, hit.hwId)
}

// Selects a control's chip (its group, for a group member) and scrolls it
// into view; or says where it is when it is not on the map.
function findControl(kind, hwId) {
    var label = hardwareLabel(kind, hwId)
    var id = placedId(kind, hwId)
    if (!id) {
        showFindMessage(label + " is not on the map yet: it is in the pool.")
        findNotPlaced(label)
        return
    }
    var n = nodeAt(id)
    if (isHidden(n)) {
        showFindMessage(label + " is hidden. Show it in the Layers panel.")
        return
    }
    setSelection([id])
    var b = nodeBox(n)
    if (face && face.showEditorRect)
        face.showEditorRect(b.x, b.y, b.w, b.h)
    showFindMessage("Found " + label + ".")
    bump()
}

function showFindMessage(text) {
    findMsg = text
    _findMsgTimer.restart()
}

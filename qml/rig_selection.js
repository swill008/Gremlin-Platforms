// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Selection, nudging, delete, copy/paste/duplicate and stacking order.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function deleteSelection() {
    var n = nodeAt(selectedId)
    if (!n)
        return
    var L = currentLeader(n)
    if (!L)
        return
    if (selectedSpine >= 0 && L.spines && selectedSpine < L.spines.length) {
        L.spines.splice(selectedSpine, 1)
        n.spines = L.spines
        selectedSpine = -1
        bump()
    }
}

// Before an item leaves the map (memberIndex < 0) or a group loses one of
// its chips (memberIndex >= 0): every leader end and callout pointer aimed at
// it stays exactly where it is drawn now, as a free end, instead of jumping
// to the page's top-left corner. Ends are changed in place (they can be
// shared). Ends aimed at later chips of the group follow their new place.
function freeEndsAimedAt(id, memberIndex) {
    if (memberIndex === undefined)
        memberIndex = -1
    var seen = []
    function fix(end) {
        if (!end || end.id !== id || end.type === "free" || seen.indexOf(end) >= 0)
            return
        seen.push(end)
        if (memberIndex >= 0 && end.type === "member" && end.member > memberIndex) {
            end.member = end.member - 1
            return
        }
        if (memberIndex >= 0 && !(end.type === "member" && end.member === memberIndex))
            return
        var p = endPt(end)
        end.type = "free"
        end.fx = xToFx(p.x)
        end.fy = yToFy(p.y)
        delete end.id
        delete end.member
    }
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        if (!n || (n.id === id && memberIndex < 0))
            continue
        fix(n.from)
        fix(n.to)
        var leads = n.leaders || []
        for (var k = 0; k < leads.length; k++) {
            fix(leads[k].from)
            fix(leads[k].to)
        }
        if (memberIndex < 0 && n.tail && n.tail.to === id) {
            var tip = calloutTip(n)
            n.tail = { fx: xToFx(tip.x), fy: yToFy(tip.y) }
        }
    }
}

// Takes one item off the map without a history step; false for a group, a
// locked item or one not on the map.
function _removeNode(nid) {
    var n = nodeAt(nid)
    if (!n || isGroup(n) || isLocked(n))
        return false
    var idx = nodeIndex(nid)
    if (idx < 0)
        return false
    if (tableIsPacked(n))
        detachTablePacked(n)
    else
        detachChipFromTable(n)
    freeEndsAimedAt(nid, -1)
    var list = nodes || []
    list.splice(idx, 1)
    return true
}

function deleteChip(id) {
    var nid = id || selectedId
    if (!_removeNode(nid))
        return false
    var keep = []
    var s = selectedIds || []
    for (var i = 0; i < s.length; i++) {
        if (s[i] !== nid)
            keep.push(s[i])
    }
    groupEditId = ""
    selectedMember = -1
    setSelection(keep)
    bump()
    return true
}

// The Delete key. Deletes the most specific thing selected: a leader spine,
// a table cell, or else every selected item, as one undo step. A selected
// group is broken apart instead; groups and locked items in a wider
// selection stay (and stay selected). Returns what it did.
function deleteSelected() {
    var n = nodeAt(selectedId)
    if (n && selectedSpine >= 0) {
        var L = currentLeader(n)
        if (L && L.spines && selectedSpine < L.spines.length) {
            deleteSelection()
            return "spine"
        }
    }
    if (n && isTable(n) && tableExtra >= 0) {
        deleteThisTableCell()
        return "cell"
    }
    var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
    // One group, or a packed table anywhere in the selection: break it up.
    if ((ids.length <= 1 || packTableFromSelection()) && canUngroup()) {
        ungroupSelection()
        return "ungroup"
    }
    var kept = []
    var removed = 0
    for (var i = 0; i < ids.length; i++) {
        if (_removeNode(ids[i]))
            removed++
        else if (nodeAt(ids[i]))
            kept.push(ids[i])
    }
    if (!removed)
        return ""
    groupEditId = ""
    selectedMember = -1
    setSelection(kept)
    bump()
    return "items"
}

// --- back to the pool by dragging -----------------------------------------------

// Whether editor point (mx, my) is over the window's pool panel (poolHit,
// set by the window, takes window coordinates).
function overPool(mx, my) {
    if (typeof poolHit !== "function")
        return false
    var w = _ed.mapToItem(null, mx, my)
    return !!poolHit(w.x, w.y)
}

// What dragging the chip under the pointer onto the pool takes back: the
// selected chips and groups when it is one of them, else that one; while a
// group is being edited, the dragged member.
function returnToPool() {
    var n = nodeAt(selectedId)
    if (!n || isDraw(n))
        return false
    var mem = targetMember()
    if (groupEditId === n.id && mem) {
        if (isLocked(n))
            return false
        var list = n.members || []
        var at = list.indexOf(mem)
        if (at < 0)
            return false
        freeEndsAimedAt(n.id, at)
        list.splice(at, 1)
        selectedMember = -1
        if (!list.length)
            _removeChipNode(n)
        bump()
        return true
    }
    var ids = isSelected(n.id) && (selectedIds || []).length > 1 ? selectedIds.slice() : [n.id]
    var done = false
    for (var i = 0; i < ids.length; i++) {
        var o = nodeAt(ids[i])
        if (o && !isDraw(o) && !isLocked(o))
            done = _removeChipNode(o) || done
    }
    groupEditId = ""
    selectedMember = -1
    setSelection([])
    bump()
    return done
}

// Takes a chip or a whole group off the map; its controls show in the pool
// again.
function _removeChipNode(n) {
    var idx = nodeIndex(n.id)
    if (idx < 0)
        return false
    if (tableIsPacked(n))
        detachTablePacked(n)
    else
        detachChipFromTable(n)
    freeEndsAimedAt(n.id, -1)
    nodes.splice(idx, 1)
    return true
}

function nudge(dx, dy) {
    var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
    if (!ids.length)
        return
    var seenPack = {}
    for (var i = 0; i < ids.length; i++)
        moveNodeBy(nodeAt(ids[i]), dx, dy, seenPack)
    // A run of nudges (a held arrow key) makes one undo step when it pauses.
    repaint()
    selectedChanged()
    noteLiveEdit()
}

// Moves one item by a page fraction: a table pack once (seenPack), a shape
// drawn around chips by its chips, a drawing by its box, a chip by itself.
// Locked items stay put. Nudging and aligning both use it.
function moveNodeBy(n, dx, dy, seenPack) {
    if (!n || isLocked(n))
        return
    var pack = tablePackOf(n)
    if (pack) {
        if (!seenPack[pack.id]) {
            seenPack[pack.id] = true
            moveTablePack(pack, dx, dy)
        }
        return
    }
    if (isDraw(n)) {
        var around = n.around || []
        if (around.length) {
            var ai
            for (ai = 0; ai < around.length; ai++) {
                var qn = nodeAt(around[ai])
                if (!qn || isDraw(qn))
                    continue
                qn.chipFx = Math.max(0.01, Math.min(0.92, qn.chipFx + dx))
                qn.chipFy = Math.max(0.01, Math.min(0.92, qn.chipFy + dy))
            }
        } else {
            var oldFx = n.fx || 0
            var oldFy = n.fy || 0
            n.fx = Math.max(0, Math.min(0.98, oldFx + dx))
            n.fy = Math.max(0, Math.min(0.98, oldFy + dy))
            shiftIndependentParts(n, n.fx - oldFx, n.fy - oldFy)
        }
        followTablePacked(n)
    } else {
        n.chipFx = Math.max(0.01, Math.min(0.92, (n.chipFx || 0) + dx))
        n.chipFy = Math.max(0.01, Math.min(0.92, (n.chipFy || 0) + dy))
        refreshChipPack(n)
    }
}

function _newId(n) {
    if (isDraw(n))
        return _uid("d")
    if (isGroup(n))
        return _uid("g")
    var k = n.kind || "btn"
    return _uid(k === "btn" ? "b" : k.charAt(0))
}

function shiftClone(n, dx, dy) {
    if (isDraw(n)) {
        n.fx = (n.fx || 0) + dx
        n.fy = (n.fy || 0) + dy
    } else {
        n.chipFx = Math.max(0.01, Math.min(0.92, (n.chipFx || 0) + dx))
        n.chipFy = Math.max(0.01, Math.min(0.92, (n.chipFy || 0) + dy))
        n.hotFx = Math.max(0, Math.min(1, hotFxOf(n) + dx))
        n.hotFy = Math.max(0, Math.min(1, hotFyOf(n) + dy))
    }
    var ls = n.leaders || []
    var li
    for (li = 0; li < ls.length; li++) {
        var sp = ls[li].spines || []
        var s
        for (s = 0; s < sp.length; s++) {
            sp[s].fx = (sp[s].fx || 0) + dx
            sp[s].fy = (sp[s].fy || 0) + dy
        }
        if (ls[li].from && ls[li].from.type === "free") {
            ls[li].from.fx = (ls[li].from.fx || 0) + dx
            ls[li].from.fy = (ls[li].from.fy || 0) + dy
        }
        if (ls[li].to && ls[li].to.type === "free") {
            ls[li].to.fx = (ls[li].to.fx || 0) + dx
            ls[li].to.fy = (ls[li].to.fy || 0) + dy
        }
    }
}

function pasteNodes(src, dx, dy) {
    if (!src || !src.length)
        return
    var map = {}
    var copies = []
    var i
    for (i = 0; i < src.length; i++) {
        var c = JSON.parse(JSON.stringify(src[i]))
        var old = c.id
        c.id = _newId(c)
        map[old] = c.id
        copies.push(c)
    }
    for (i = 0; i < copies.length; i++) {
        var n = copies[i]
        shiftClone(n, dx, dy)
        if (n.around && n.around.length) {
            var a = []
            var k
            for (k = 0; k < n.around.length; k++) {
                if (map[n.around[k]])
                    a.push(map[n.around[k]])
            }
            n.around = a
        }
        var ls = n.leaders || []
        var li
        for (li = 0; li < ls.length; li++) {
            if (ls[li].from && ls[li].from.id && map[ls[li].from.id])
                ls[li].from.id = map[ls[li].from.id]
            if (ls[li].to && ls[li].to.id && map[ls[li].to.id])
                ls[li].to.id = map[ls[li].to.id]
        }
        nodes.push(n)
    }
    var ids = []
    for (i = 0; i < copies.length; i++)
        ids.push(copies[i].id)
    setSelection(ids)
    bump()
}

function duplicateSelection() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
    var src = []
    var i
    for (i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (n)
            src.push(n)
    }
    pasteNodes(src, 16 / Math.max(1, spaceRect().w), 16 / Math.max(1, spaceRect().h))
}

function copySelection() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
    var arr = []
    var i
    for (i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (n)
            arr.push(JSON.parse(JSON.stringify(n)))
    }
    clip = arr
    clipSerial = clipboardSerial
}

// Ctrl+V: a picture copied since the last chip copy (or with nothing copied
// here) is pasted as a picture layer; otherwise the copied items.
function pasteClipboard() {
    var pictureNewer = canPastePicture
        && (!(clip && clip.length) || clipboardSerial !== clipSerial)
    if (pictureNewer) {
        pastePictureRequested()
        return
    }
    pasteNodes(clip || [], 16 / Math.max(1, spaceRect().w), 16 / Math.max(1, spaceRect().h))
}

function isSelected(id) {
    if (!id)
        return false
    if (selectedId === id)
        return true
    var s = selectedIds || []
    for (var i = 0; i < s.length; i++) {
        if (s[i] === id)
            return true
    }
    return false
}

function setSelection(ids) {
    var next = ids || []
    if (JSON.stringify(next) !== JSON.stringify(selectedIds || []))
        transformMode = "resize"
    selectedIds = next
    selectedId = selectedIds.length ? selectedIds[selectedIds.length - 1] : ""
    // Crop mode ends when its picture is no longer selected.
    if (cropId && selectedIds.indexOf(cropId) < 0)
        cropId = ""
    selectedSpine = -1
    selectedChanged()
}

function toggleSelected(id) {
    var s = (selectedIds || []).slice()
    var at = s.indexOf(id)
    if (at >= 0)
        s.splice(at, 1)
    else
        s.push(id)
    setSelection(s)
}

function cancelAllActions() {
    endGroupEdit()
    drawTool = ""
    pathDraft = []
    pathHover = null
    dragKind = ""
    clearMoveGuides()
    dragSpine = -1
    dragMember = -1
    banding = false
    selectedSpine = -1
    selectedLeader = 0
    selectedSeg = -1
    setSelection([])
    movePhoto = false
    if (_ctx)
        _ctx.close()
    cropId = ""
    textPaintOn = false
    cancelRename()
    armRenameId = ""
    armRenameMember = -1
    bump()
}

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

function deleteChip(id) {
    var nid = id || selectedId
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
    var list = nodes || []
    list.splice(idx, 1)
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

function nudge(dx, dy) {
    var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
    if (!ids.length)
        return
    var seenPack = {}
    var i
    for (i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n || isLocked(n))
            continue
        var pack = tablePackOf(n)
        if (pack) {
            if (!seenPack[pack.id]) {
                seenPack[pack.id] = true
                moveTablePack(pack, dx, dy)
            }
            continue
        }
        if (isDraw(n)) {
            if (isLocked(n))
                continue
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
    bump()
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
}

function pasteClipboard() {
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
    selectedIds = ids || []
    selectedId = selectedIds.length ? selectedIds[selectedIds.length - 1] : ""
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
    if (_tableCtx)
        _tableCtx.close()
    if (_textCtx)
        _textCtx.close()
    textPaintOn = false
    cancelRename()
    armRenameId = ""
    armRenameMember = -1
    bump()
}

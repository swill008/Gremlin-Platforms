// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Layers: stacking order, hiding and locking, names, and the Layers panel's rows.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
//
// Stacking is the order of the nodes list: the last node is on top, both for
// drawing and for clicks. A node may carry hidden and locked; a chip also
// hotHidden and hotLocked for its hotspot, and each leader hidden and locked.
// A hidden item is not drawn (on the live map either) and not clicked; a
// locked one is drawn but clicks pass through it, and it is not moved,
// nudged or deleted. Locking or hiding a chip or group covers its hotspot,
// leaders and members.

// --- stacking ---------------------------------------------------------------

// Old layouts kept a zLayer (1 to 4; drawings 2 and chips 3 by default) and
// "pinned". Sort once by that layer, keeping the list order within a layer,
// and turn pinned into locked, so a layout looks as it did.
function normalizeStacking() {
    var list = nodes || []
    var keyed = []
    for (var i = 0; i < list.length; i++)
        keyed.push({ n: list[i], i: i, z: _legacyZ(list[i]) })
    keyed.sort(function(a, b) { return (a.z - b.z) || (a.i - b.i) })
    var moved = false
    for (var k = 0; k < keyed.length; k++) {
        if (keyed[k].i !== k)
            moved = true
    }
    if (moved) {
        var sorted = keyed.map(function(e) { return e.n })
        list.splice(0, list.length)
        for (var j = 0; j < sorted.length; j++)
            list.push(sorted[j])
    }
    for (var m = 0; m < list.length; m++) {
        var n = list[m]
        if (n.zLayer !== undefined)
            delete n.zLayer
        if (n.pinned !== undefined) {
            if (n.pinned)
                n.locked = true
            delete n.pinned
        }
    }
}

function _legacyZ(n) {
    if (n && n.zLayer !== undefined && n.zLayer !== null)
        return Number(n.zLayer)
    return isDraw(n) ? 2 : 3
}

// Puts a new node under the chips: shapes drawn around chips, pictures and
// tables would otherwise cover them.
function insertBelowChips(n) {
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        if (!isDraw(list[i])) {
            list.splice(i, 0, n)
            return
        }
    }
    list.push(n)
}

// The leader canvas sits just under the lowest chip, so leaders are above the
// drawings under the chips and below anything moved over them.
function leaderLayerZ() {
    tick
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        if (!isDraw(list[i]))
            return i - 0.5
    }
    return list.length
}

function _movable(ids) {
    var out = []
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (n && !isLocked(n))
            out.push(n.id)
    }
    return out
}

// Moves a node to a list index (0 is the bottom).
function moveNodeTo(id, index) {
    var list = nodes || []
    var from = nodeIndex(id)
    if (from < 0)
        return
    var n = list.splice(from, 1)[0]
    var to = Math.max(0, Math.min(list.length, index))
    list.splice(to, 0, n)
    bump()
}

function _selectedForStacking() {
    return _movable((selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : []))
}

// One step up or down past the next item that is not selected.
function bringForward() {
    var ids = _selectedForStacking()
    var list = nodes || []
    for (var i = list.length - 2; i >= 0; i--) {
        if (ids.indexOf(list[i].id) >= 0 && ids.indexOf(list[i + 1].id) < 0) {
            var t = list[i]
            list[i] = list[i + 1]
            list[i + 1] = t
        }
    }
    bump()
}

function sendBack() {
    var ids = _selectedForStacking()
    var list = nodes || []
    for (var i = 1; i < list.length; i++) {
        if (ids.indexOf(list[i].id) >= 0 && ids.indexOf(list[i - 1].id) < 0) {
            var t = list[i]
            list[i] = list[i - 1]
            list[i - 1] = t
        }
    }
    bump()
}

function bringToFront() {
    var ids = _selectedForStacking()
    var list = nodes || []
    var keep = list.filter(function(n) { return ids.indexOf(n.id) < 0 })
    var top = list.filter(function(n) { return ids.indexOf(n.id) >= 0 })
    list.splice(0, list.length)
    keep.concat(top).forEach(function(n) { list.push(n) })
    bump()
}

function sendToBack() {
    var ids = _selectedForStacking()
    var list = nodes || []
    var keep = list.filter(function(n) { return ids.indexOf(n.id) < 0 })
    var bottom = list.filter(function(n) { return ids.indexOf(n.id) >= 0 })
    list.splice(0, list.length)
    bottom.concat(keep).forEach(function(n) { list.push(n) })
    bump()
}

// --- hiding and locking --------------------------------------------------------

function isHidden(n) {
    return !!(n && n.hidden)
}

// A hotspot or leader is out of reach when it, or its chip, is hidden or locked.
function hotBlocked(n) {
    return !n || isHidden(n) || isLocked(n) || !!n.hotHidden || !!n.hotLocked
}

function hotHidden(n) {
    return !n || isHidden(n) || !!n.hotHidden
}

function leaderBlocked(n, li) {
    if (!n || isHidden(n) || isLocked(n))
        return true
    var L = leaderList(n)[li]
    return !!(L && (L.hidden || L.locked))
}

function leaderHidden(n, li) {
    if (!n || isHidden(n))
        return true
    var L = leaderList(n)[li]
    return !!(L && L.hidden)
}

// part: "" for the item, "hot" for a chip's hotspot, "leader:<n>" for a leader.
function _partTarget(n, part) {
    if (!part)
        return { obj: n, key: "" }
    if (part === "hot")
        return { obj: n, key: "hot" }
    if (part.indexOf("leader:") === 0)
        return { obj: ensureLeaders(n)[parseInt(part.slice(7), 10)], key: "" }
    return { obj: null, key: "" }
}

function _flagKey(key, flag) {
    return key ? key + flag.charAt(0).toUpperCase() + flag.slice(1) : flag
}

function layerFlag(id, part, flag) {
    var n = nodeAt(id)
    if (!n)
        return false
    var t = _partTarget(n, part)
    return !!(t.obj && t.obj[_flagKey(t.key, flag)])
}

// True when the item the part belongs to already hides or locks it.
function layerFlagInherited(id, part, flag) {
    var n = nodeAt(id)
    if (!n || !part)
        return false
    return flag === "locked" ? isLocked(n) : isHidden(n)
}

function setLayerFlag(id, part, flag, on) {
    var n = nodeAt(id)
    if (!n)
        return
    var t = _partTarget(n, part)
    if (!t.obj)
        return
    var key = _flagKey(t.key, flag)
    if (on)
        t.obj[key] = true
    else
        delete t.obj[key]
    if (!part && flag === "locked")
        delete n.pinned
    // A hidden item cannot stay selected; a locked one can, from this panel.
    if (on && !part && flag === "hidden")
        setSelection((selectedIds || []).filter(function(s) { return s !== id }))
    bump()
}

function toggleLayerFlag(id, part, flag) {
    setLayerFlag(id, part, flag, !layerFlag(id, part, flag))
}

// Ctrl+L: locks the selection, or unlocks it when all of it is locked.
function toggleLockSelection() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    if (!ids.length)
        return
    var allLocked = ids.every(function(s) { return isLocked(nodeAt(s)) })
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n)
            continue
        if (allLocked)
            delete n.locked
        else
            n.locked = true
        delete n.pinned
    }
    bump()
}

function _clearFlag(flag) {
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        delete n[flag]
        delete n[_flagKey("hot", flag)]
        if (flag === "locked")
            delete n.pinned
        var ls = isDraw(n) ? [] : leaderList(n)
        for (var k = 0; k < ls.length; k++)
            delete ls[k][flag]
    }
}

function showAll() {
    _clearFlag("hidden")
    photoHidden = false
    bump()
}

// Ctrl+Shift+L.
function unlockAll() {
    _clearFlag("locked")
    photoLocked = false
    bump()
}

// --- names -----------------------------------------------------------------------

var _KIND_NAMES = {
    rect: "Rectangle", roundrect: "Rounded rectangle", ellipse: "Ellipse", triangle: "Triangle",
    diamond: "Diamond", arrow: "Arrow", arrow2: "Double arrow", line: "Line", table: "Table"
}

// The name shown for an item: its own name, else what it is.
function layerName(n) {
    if (!n)
        return ""
    if (n.name)
        return String(n.name)
    if (isText(n)) {
        var t = String(n.text || "").replace(/\s+/g, " ").trim()
        return "Text: " + (t.length > 24 ? t.slice(0, 23) + "…" : (t || "(empty)"))
    }
    if (isOverlay(n)) {
        var src = String(n.src || "")
        return "Picture: " + (src.split("/").pop() || "picture")
    }
    if (isLine(n)) {
        var a = n.headStart === "solid" || n.headStart === "hollow"
        var b = n.headEnd === "solid" || n.headEnd === "hollow"
        return a && b ? "Double-headed arrow" : (a || b ? "Arrow" : "Line")
    }
    if (isDraw(n))
        return _KIND_NAMES[n.shape || "rect"] || "Drawing"
    if (isGroup(n))
        return "Group: " + (n.members || []).map(function(m) { return memberLabel(n, m) }).join(", ")
    return friendlyOf(n, null) || hardwareLabel(n.kind, n.hwId) || n.id
}

// Names a drawing (chips are renamed on the map, as their name is their label).
function renameLayer(id, name) {
    var n = nodeAt(id)
    if (!n || !isDraw(n))
        return
    var s = String(name || "").trim()
    if (s)
        n.name = s
    else
        delete n.name
    bump()
}

function layerType(n) {
    if (isTable(n))
        return "table"
    if (isText(n))
        return "text"
    if (isOverlay(n))
        return "picture"
    if (isLine(n))
        return "line"
    if (isDraw(n))
        return "shape"
    if (isGroup(n))
        return "group"
    return "chip"
}

var _FILTERS = {
    all: null,
    chips: ["chip", "group"],
    drawings: ["shape", "line"],
    pictures: ["picture"],
    text: ["text", "table"]
}

// The Layers panel's rows, top of the stack first, then the background photo.
// expanded maps a chip's id to true when its hotspot and leader rows show.
function layerRows(filter, expanded) {
    tick
    var types = _FILTERS[filter || "all"] || null
    var list = nodes || []
    var rows = []
    for (var i = list.length - 1; i >= 0; i--) {
        var n = list[i]
        var type = layerType(n)
        if (types && types.indexOf(type) < 0)
            continue
        var hasParts = type === "chip" || type === "group"
        var open = hasParts && !!(expanded && expanded[n.id])
        rows.push({
            id: n.id, part: "", depth: 0, type: type, name: layerName(n),
            hidden: isHidden(n), locked: isLocked(n), hiddenFrom: false, lockedFrom: false,
            selected: isSelected(n.id), canOpen: hasParts, open: open, index: i, renamable: isDraw(n)
        })
        if (!open)
            continue
        rows.push({
            id: n.id, part: "hot", depth: 1, type: "hotspot", name: "Hotspot",
            hidden: !!n.hotHidden, locked: !!n.hotLocked, hiddenFrom: isHidden(n), lockedFrom: isLocked(n),
            selected: false, canOpen: false, open: false, index: i, renamable: false
        })
        var ls = leaderList(n)
        for (var k = 0; k < ls.length; k++) {
            rows.push({
                id: n.id, part: "leader:" + k, depth: 1, type: "leader", name: "Leader " + (k + 1),
                hidden: !!ls[k].hidden, locked: !!ls[k].locked, hiddenFrom: isHidden(n), lockedFrom: isLocked(n),
                selected: false, canOpen: false, open: false, index: i, renamable: false
            })
        }
    }
    if (!types) {
        rows.push({
            id: "", part: "photo", depth: 0, type: "photo", name: "Background photo",
            hidden: photoHidden, locked: photoLocked, hiddenFrom: false, lockedFrom: false,
            selected: false, canOpen: false, open: false, index: -1, renamable: false
        })
    }
    return rows
}

function setPhotoFlag(flag, on) {
    if (flag === "hidden")
        photoHidden = !!on
    else
        photoLocked = !!on
    if (photoLocked)
        movePhoto = false
    bump()
}

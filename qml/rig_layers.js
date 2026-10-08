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
// and turn pinned into locked, so a layout looks as it did. A layout without
// any zLayer is already in stacking order (the list order) and is not sorted:
// sorting it put every drawing under every chip each time the map was opened
// or saved, undoing Bring to Front and Layers-panel moves.
function normalizeStacking() {
    var list = nodes || []
    var legacy = false
    for (var l = 0; l < list.length; l++) {
        if (list[l] && list[l].zLayer !== undefined && list[l].zLayer !== null)
            legacy = true
    }
    var keyed = []
    for (var i = 0; i < list.length; i++)
        keyed.push({ n: list[i], i: i, z: _legacyZ(list[i]) })
    if (legacy)
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
    if (_setLayerFlag(id, part, flag, on))
        bump()
}

// Several at once ({ id, part } each, Hide Selected): one undo step.
function setLayerFlags(targets, flag, on) {
    var any = false
    for (var i = 0; i < targets.length; i++)
        any = _setLayerFlag(targets[i].id, targets[i].part, flag, on) || any
    if (any)
        bump()
}

function _setLayerFlag(id, part, flag, on) {
    var n = nodeAt(id)
    if (!n)
        return false
    var t = _partTarget(n, part)
    if (!t.obj)
        return false
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
    return true
}

function toggleLayerFlag(id, part, flag) {
    setLayerFlag(id, part, flag, !layerFlag(id, part, flag))
}

// Layers panel Delete (its trash icon and right-click menu): a chip or group
// goes back to the pool, a leader is removed, a hotspot is hidden (a chip
// always keeps its hotspot's place), a picture, drawing, text box or table is
// removed. The photo and locked items are not deleted. One undo step.
function canDeleteLayer(id, part) {
    // A group member's row (a search result) is not its own item.
    if (part === "photo" || !id || String(part || "").indexOf("member:") === 0)
        return false
    var n = nodeAt(id)
    if (!n || isLocked(n))
        return false
    // A locked hotspot or leader stays too.
    if (part && layerFlag(id, part, "locked"))
        return false
    if (part === "hot")
        return !layerFlag(id, "hot", "hidden")
    return true
}

function deleteLayer(id, part) {
    if (!canDeleteLayer(id, part))
        return false
    var n = nodeAt(id)
    if (part === "hot") {
        setLayerFlag(id, "hot", "hidden", true)
        return true
    }
    if (part && part.indexOf("leader:") === 0) {
        setSelection([id])
        selectedId = id
        selectedLeader = parseInt(part.slice(7), 10) || 0
        deleteLeader()
        return true
    }
    if (isGroup(n)) {
        // Open for editing, returnToPool() would remove only its selected
        // member: the row stands for the whole group.
        if (groupEditId === id) {
            groupEditId = ""
            selectedMember = -1
        }
        setSelection([id])
        selectedId = id
        returnToPool()
        return true
    }
    deleteChip(id)
    return true
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
    diamond: "Diamond", arrow: "Arrow", arrow2: "Double arrow", line: "Line", path: "Path", table: "Table"
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
    return oneLine(friendlyOf(n, null)) || hardwareLabel(n.kind, n.hwId) || n.id
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

// Each row's kind as its Layers-panel toggle names it (07 S102); a group
// member counts as a group's row.
var _KIND_WORDS = {
    chip: "Chips", group: "Groups", member: "Groups", hotspot: "Hotspots", leader: "Leaders",
    shape: "Shapes", line: "Lines", picture: "Pictures", text: "Text", table: "Tables", photo: "Photo"
}

// The panel's filter as { kinds, query, active }. A string is the old
// single-choice kind ("all", "chips", ...) and keeps working as before.
function _layerFilter(state) {
    if (state === undefined || state === null || typeof state === "string") {
        var types = _FILTERS[state || "all"] || null
        return { kinds: types || [], query: "", active: false, legacy: true }
    }
    var kinds = (state.kinds || []).map(function(k) { return String(k) })
    var query = String(state.query || "").trim().toLowerCase()
    return { kinds: kinds, query: query, active: kinds.length > 0 || query.length > 0, legacy: false }
}

function _kindOn(f, type) {
    if (!f.kinds.length)
        return true
    // A group member shows under the Chips toggle as well as Groups.
    if (type === "member")
        return f.kinds.indexOf("group") >= 0 || f.kinds.indexOf("chip") >= 0
    return f.kinds.indexOf(type) >= 0
}

// Matches the search on the row's name, its control (even when renamed),
// what the chip shows and the kind of row (07 S102).
function _textOn(f, type, name, extra) {
    if (!f.query)
        return true
    var hay = [name, type === "member" ? "" : type, _KIND_WORDS[type] || ""].concat(extra || [])
    for (var i = 0; i < hay.length; i++) {
        if (String(hay[i] || "").toLowerCase().indexOf(f.query) >= 0)
            return true
    }
    return false
}

function _rowMatches(f, type, name, extra) {
    return _kindOn(f, type) && _textOn(f, type, name, extra)
}

// A chip's or member's control and the text it shows.
function _chipExtra(n, mem) {
    var kind = mem ? memberKind(n, mem) : n.kind
    var hwId = mem ? mem.hwId : n.hwId
    var out = [chipText(n, mem), friendlyOf(n, mem)]
    if (hwId !== undefined && hwId !== null)
        out.push(hardwareLabel(kind, hwId))
    return out
}

// One item's rows: the item, then its hotspot, leaders and (as search
// results only) group members. all: every row, for counting; otherwise the
// rows the panel shows, with match and heading set.
function _itemRows(f, n, i, expanded, all) {
    var type = layerType(n)
    var hasParts = type === "chip" || type === "group"
    var open = hasParts && !!(expanded && expanded[n.id])
    var name = layerName(n)
    var extra = type === "chip" ? _chipExtra(n, null) : []
    var head = {
        id: n.id, part: "", depth: 0, type: type, name: name,
        hidden: isHidden(n), locked: isLocked(n), hiddenFrom: false, lockedFrom: false,
        selected: isSelected(n.id), canOpen: hasParts, open: open, index: i, renamable: isDraw(n),
        match: _rowMatches(f, type, name, extra), heading: false
    }
    var parts = []
    if (hasParts) {
        parts.push({
            id: n.id, part: "hot", depth: 1, type: "hotspot", name: "Hotspot",
            hidden: !!n.hotHidden, locked: !!n.hotLocked, hiddenFrom: isHidden(n), lockedFrom: isLocked(n),
            selected: false, canOpen: false, open: false, index: i, renamable: false,
            match: _rowMatches(f, "hotspot", "Hotspot", []), heading: false
        })
        var ls = leaderList(n)
        for (var k = 0; k < ls.length; k++) {
            var ln = "Leader " + (k + 1)
            parts.push({
                id: n.id, part: "leader:" + k, depth: 1, type: "leader", name: ln,
                hidden: !!ls[k].hidden, locked: !!ls[k].locked, hiddenFrom: isHidden(n), lockedFrom: isLocked(n),
                selected: false, canOpen: false, open: false, index: i, renamable: false,
                match: _rowMatches(f, "leader", ln, []), heading: false
            })
        }
    }
    var members = type === "group" ? (n.members || []) : []
    var memRows = []
    for (var m = 0; m < members.length; m++) {
        var mn = memberLabel(n, members[m])
        memRows.push({
            id: n.id, part: "member:" + m, depth: 1, type: "member", name: mn,
            hidden: false, locked: false, hiddenFrom: isHidden(n), lockedFrom: isLocked(n),
            selected: false, canOpen: false, open: false, index: i, renamable: false,
            match: _rowMatches(f, "member", mn, _chipExtra(n, members[m])), heading: false
        })
    }
    if (all)
        return [head].concat(parts, memRows)
    if (!f.active) {
        // No filter: the rows as before the search (members have no rows).
        head.match = true
        if (!open)
            return [head]
        parts.forEach(function(p) { p.match = true })
        return [head].concat(parts)
    }
    // A filter: matching parts show even under a closed chip; an open chip
    // that matches shows all its parts. A member shows only as a match.
    var shown = []
    var childHit = false
    for (var p = 0; p < parts.length; p++) {
        if (parts[p].match || (open && head.match)) {
            shown.push(parts[p])
            childHit = childHit || parts[p].match
        }
    }
    for (var q = 0; q < memRows.length; q++) {
        if (memRows[q].match) {
            shown.push(memRows[q])
            childHit = true
        }
    }
    if (!head.match && !childHit)
        return []
    head.heading = !head.match
    return [head].concat(shown)
}

function _photoRow(f) {
    return {
        id: "", part: "photo", depth: 0, type: "photo", name: "Background photo",
        hidden: photoHidden, locked: photoLocked, hiddenFrom: false, lockedFrom: false,
        selected: false, canOpen: false, open: false, index: -1, renamable: false,
        match: !f.active || _rowMatches(f, "photo", "Background photo", []), heading: false
    }
}

// The Layers panel's rows, top of the stack first, then the background photo.
// expanded maps a chip's id to true when its hotspot and leader rows show.
// state is the panel's filter, { kinds, query } (07 S102), or an old kind
// name ("all", "chips", ...). Each row has match (it passes the filter) and
// heading (shown only for a matching hotspot, leader or member under it; the
// panel dims it). With no filter every row matches.
function layerRows(state, expanded) {
    tick
    var f = _layerFilter(state)
    var list = nodes || []
    var rows = []
    for (var i = list.length - 1; i >= 0; i--) {
        var n = list[i]
        if (f.legacy && f.kinds.length && f.kinds.indexOf(layerType(n)) < 0)
            continue
        rows = rows.concat(_itemRows(f, n, i, expanded, false))
    }
    var photo = _photoRow(f)
    if (f.legacy ? !f.kinds.length : photo.match)
        rows.push(photo)
    return rows
}

// The panel's "12 of 148": every row there is (open or not, hotspots,
// leaders, group members and the photo) and how many pass the filter.
function layerCounts(state) {
    tick
    var f = _layerFilter(state)
    var list = nodes || []
    var all = []
    for (var i = list.length - 1; i >= 0; i--)
        all = all.concat(_itemRows(f, list[i], i, null, true))
    all.push(_photoRow(f))
    var matches = 0
    for (var r = 0; r < all.length; r++) {
        if (!f.active || all[r].match)
            matches++
    }
    return { matches: matches, total: all.length }
}

// Enter in the search box: selects every match on the map (a hotspot,
// leader or member selects its chip or group; not the photo, nor a hidden
// item) and brings the first into view. Selecting is not an edit: no undo
// step. Returns how many items were selected.
function selectLayerMatches(state) {
    var rows = layerRows(state, null)
    var ids = []
    for (var i = 0; i < rows.length; i++) {
        var r = rows[i]
        if (!r.match || !r.id || ids.indexOf(r.id) >= 0 || isHidden(nodeAt(r.id)))
            continue
        ids.push(r.id)
    }
    if (!ids.length)
        return 0
    setSelection(ids)
    var b = nodeBox(nodeAt(ids[0]))
    if (face && face.showEditorRect)
        face.showEditorRect(b.x, b.y, b.w, b.h)
    repaint()
    selectedChanged()
    return ids.length
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

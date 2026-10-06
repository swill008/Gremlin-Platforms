// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Groups and 5-way formats: member layout, alignment, grouping and ungrouping.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function groupAlignH(n) {
    var a = n && n.alignH ? String(n.alignH) : "left"
    if (a === "center" || a === "right" || a === "free")
        return a
    return "left"
}

function setAlignH(mode) {
    var n = nodeAt(selectedId)
    if (!isGroup(n))
        return
    if (mode === "free")
        bakeAlignToFree(n)
    else
        n.alignH = (mode === "left" || mode === "right") ? mode : "center"
    bump()
}

function bakeAlignToFree(n) {
    if (!isGroup(n) || groupAlignH(n) === "free")
        return
    var mem = n.members || []
    var ew = Math.max(1, spaceRect().w)
    var eh = Math.max(1, spaceRect().h)
    for (var i = 0; i < mem.length; i++) {
        mem[i].ox = memberLocalX(n, mem[i]) / ew
        mem[i].oy = memberLocalY(n, mem[i]) / eh
    }
    n.alignH = "free"
}

function memberIndexOf(n, mem) {
    var mems = (n && n.members) ? n.members : []
    for (var i = 0; i < mems.length; i++) {
        if (mems[i] === mem)
            return i
    }
    return 0
}

function stackPitch(n) {
    return chipH(n) + 2
}

function memberLocalX(n, mem) {
    var a = groupAlignH(n)
    if (!themeLayout(n) && a === "center") {
        var w = chipWGuess(n, mem)
        return Math.max(0, (groupSpanW(n) - w) * 0.5)
    }
    if (!themeLayout(n) && a === "right") {
        var wr = chipWGuess(n, mem)
        return Math.max(0, groupSpanW(n) - wr)
    }
    if (!themeLayout(n) && a === "left")
        return 0
    return memberHomeX(n, mem) - groupMinX(n)
}

function memberLocalY(n, mem) {
    if (!themeLayout(n) && groupAlignH(n) !== "free")
        return captionH(n) + memberIndexOf(n, mem) * stackPitch(n)
    return memberHomeY(n, mem) - groupMinY(n)
}

function memberHomeX(n, mem) {
    if (themeLayout(n)) {
        var g = themeGeom(n)
        var r = fiveWayRole(mem)
        return (g[r] || g.center).x + (mem.offX || 0) * Math.max(1, spaceRect().w)
    }
    var ew = Math.max(1, spaceRect().w)
    var a = groupAlignH(n)
    var w = chipWGuess(n, mem)
    if (a === "center" || a === "right" || a === "left")
        return 0
    return (mem.ox || 0) * ew
}

function memberHomeY(n, mem) {
    var cap = captionH(n)
    if (themeLayout(n)) {
        var g = themeGeom(n)
        var r = fiveWayRole(mem)
        return (g[r] || g.center).y + (mem.offY || 0) * Math.max(1, spaceRect().h)
    }
    if (groupAlignH(n) !== "free")
        return cap + memberIndexOf(n, mem) * stackPitch(n)
    return (mem.oy || 0) * Math.max(1, spaceRect().h)
}

function groupMinX(n) {
    var mem = (n && n.members) ? n.members : []
    if (!mem.length)
        return 0
    if (themeLayout(n) || groupAlignH(n) === "free") {
        var minx = 1e9
        var i
        for (i = 0; i < mem.length; i++)
            minx = Math.min(minx, memberHomeX(n, mem[i]))
        return minx < 1e8 ? minx : 0
    }
    return 0
}

function groupMinY(n) {
    var mem = (n && n.members) ? n.members : []
    if (!mem.length)
        return 0
    if (themeLayout(n) || groupAlignH(n) === "free") {
        var miny = 1e9
        var i
        for (i = 0; i < mem.length; i++)
            miny = Math.min(miny, memberHomeY(n, mem[i]))
        return miny < 1e8 ? miny : 0
    }
    return 0
}

function groupSpanW(n) {
    var mem = (n && n.members) ? n.members : []
    if (!mem.length)
        return 40
    if (groupAlignH(n) !== "free" && !themeLayout(n)) {
        var maxw = 8
        var i
        for (i = 0; i < mem.length; i++)
            maxw = Math.max(maxw, chipWGuess(n, mem[i]))
        return maxw
    }
    var minx = groupMinX(n)
    var maxx = minx
    var j
    for (j = 0; j < mem.length; j++)
        maxx = Math.max(maxx, memberHomeX(n, mem[j]) + chipWGuess(n, mem[j]))
    return Math.max(8, maxx - minx)
}

function groupSpanH(n) {
    var mem = (n && n.members) ? n.members : []
    if (!mem.length)
        return 20
    if (groupAlignH(n) !== "free" && !themeLayout(n))
        return Math.max(8, captionH(n) + mem.length * stackPitch(n) - 2)
    var miny = groupMinY(n)
    var maxy = miny
    var i
    for (i = 0; i < mem.length; i++)
        maxy = Math.max(maxy, memberHomeY(n, mem[i]) + chipH(n, mem[i]))
    return Math.max(8, maxy - miny)
}

function isGroup(n) {
    if (!n)
        return false
    var k = n.kind
    if (k === "plus" || k === "pair" || k === "axis_stack" || k === "stack")
        return true
    return !!(n.members && n.members.length)
}

function isFiveWay(n) {
    if (!isGroup(n) || n.kind === "axis_stack")
        return false
    var mem = n.members || []
    if (mem.length !== 5)
        return false
    var roles = {}
    var ids = []
    var i
    for (i = 0; i < mem.length; i++) {
        if (mem[i].role)
            roles[String(mem[i].role).toLowerCase()] = true
        ids.push(mem[i].hwId)
    }
    if (roles.up && roles.down && roles.left && roles.right && (roles.center || roles.push))
        return true
    ids.sort(function (a, b) { return a - b })
    return (ids[0] === 6 && ids[4] === 10) || (ids[0] === 11 && ids[4] === 15) || (ids[0] === 16 && ids[4] === 20)
}

function fiveWayFormat(n) {
    var f = n && n.format ? String(n.format) : ""
    if (f === "plus" || f === "mini" || f === "card" || f === "radial")
        return f
    return ""
}

function memberHasOverride(mem) {
    if (!mem)
        return false
    var keys = ["chipShape", "chipSize", "circleSize", "chipFill", "fontSize", "color", "border", "textColor",
                "hlColor", "hlBorder", "hlText", "offX", "offY"]
    var i
    for (i = 0; i < keys.length; i++) {
        var v = mem[keys[i]]
        if (v !== undefined && v !== null && v !== "")
            return true
    }
    return false
}

function clearGroupFormat() {
    var n = ctxTarget() || nodeAt(selectedId)
    if (!n || !isGroup(n))
        return
    selectedId = n.id
    var mem = n.members || []
    var keys = ["chipShape", "chipSize", "circleSize", "chipFill", "fontSize", "color", "border", "textColor",
                "hlColor", "hlBorder", "hlText", "offX", "offY"]
    var i
    var k
    for (i = 0; i < mem.length; i++) {
        for (k = 0; k < keys.length; k++)
            delete mem[i][keys[k]]
    }
    if (isFiveWay(n)) {
        clearThemeMemberLayout(n)
        delete n.format
        if (n.leaders && n.leaders.length > 1)
            n.leaders = [n.leaders[0]]
    }
    bump()
}

function fiveWayRole(mem) {
    var r = String((mem && mem.role) || "").toLowerCase()
    if (r === "push")
        return "center"
    return r
}

function fiveWayCaption(n) {
    var id = n && n.id ? String(n.id) : ""
    if (id === "p610")
        return "Head 5-way"
    if (id === "p1115")
        return "Top-right 5-way"
    if (id === "p1620")
        return "Wheel 5-way"
    return "5-way"
}

function captionH(n) {
    var f = fiveWayFormat(n)
    if (f === "card" || f === "plus" || f === "mini")
        return Math.max(14, ((n && n.fontSize) || 10) + 4)
    return 0
}

function themeLayout(n) {
    var f = fiveWayFormat(n)
    return f === "plus" || f === "mini" || f === "radial"
}

function ensureFiveWayRoles(n) {
    var mem = n.members || []
    var i
    var ok = mem.length === 5
    for (i = 0; i < mem.length; i++) {
        var r = fiveWayRole(mem[i])
        if (!(r === "up" || r === "down" || r === "left" || r === "right" || r === "center"))
            ok = false
    }
    if (ok)
        return
    var ids = []
    for (i = 0; i < mem.length; i++)
        ids.push(mem[i].hwId)
    var min = ids.length ? Math.min.apply(null, ids) : 0
    var map = {}
    if (min === 6 || min === 11 || min === 16) {
        map[min] = "up"
        map[min + 1] = "right"
        map[min + 2] = "down"
        map[min + 3] = "left"
        map[min + 4] = "center"
    }
    var fallback = ["up", "left", "center", "right", "down"]
    for (i = 0; i < mem.length; i++) {
        if (map[mem[i].hwId])
            mem[i].role = map[mem[i].hwId]
        else if (!mem[i].role)
            mem[i].role = fallback[i] || "center"
    }
}

function roleWord(r) {
    if (r === "up") return "Up"
    if (r === "down") return "Down"
    if (r === "left") return "Left"
    if (r === "right") return "Right"
    if (r === "center") return "Push"
    return ""
}

function systemName(n, mem) {
    if (mem)
        return hardwareLabel(memberKind(n, mem), mem.hwId)
    if (!n)
        return ""
    return hardwareLabel(n.kind, n.hwId)
}

function memberHasCustomName(n, mem) {
    if (!mem)
        return false
    return isUserFriendly(memberKind(n, mem), mem.hwId, mem.friendly)
}

function memberLabel(n, mem) {
    return friendlyOf(n, mem)
}

function memByRole(n, role) {
    var mem = (n && n.members) ? n.members : []
    var i
    for (i = 0; i < mem.length; i++) {
        if (fiveWayRole(mem[i]) === role)
            return mem[i]
    }
    return null
}

function themeGap(n) {
    return Math.max(8, 4 * 2 + 2)
}

function themeGeom(n) {
    function bw(role) {
        var m = memByRole(n, role)
        return m ? chipWGuess(n, m) : 24
    }
    function bh(role) {
        var m = memByRole(n, role)
        return chipH(n, m)
    }
    var h = chipH(n, null)
    var wu = bw("up")
    var wl = bw("left")
    var wc = bw("center")
    var wr = bw("right")
    var wd = bw("down")
    var G = themeGap(n)
    var cap = captionH(n)
    var leftX = 0
    var pushX = wl + G
    var rightX = pushX + wc + G
    var pushC = pushX + wc * 0.5
    var upX = pushC - wu * 0.5
    var downX = pushC - wd * 0.5
    var minx = Math.min(0, upX, downX)
    var shift = minx < 0 ? -minx : 0
    leftX += shift
    pushX += shift
    rightX += shift
    upX += shift
    downX += shift
    var hu = bh("up")
    var hl = bh("left")
    var hc = bh("center")
    var hr = bh("right")
    var hd = bh("down")
    var rowH = Math.max(hl, hc, hr)
    var upY = cap
    var rowY = cap + hu + G
    var downY = rowY + rowH + G
    var maxx = Math.max(leftX + wl, pushX + wc, rightX + wr, upX + wu, downX + wd)
    return {
        up: { x: upX, y: upY },
        left: { x: leftX, y: rowY + (rowH - hl) * 0.5 },
        center: { x: pushX, y: rowY + (rowH - hc) * 0.5 },
        right: { x: rightX, y: rowY + (rowH - hr) * 0.5 },
        down: { x: downX, y: downY },
        w: Math.max(8, maxx),
        h: downY + hd
    }
}

function themeCell(n) {
    var g = themeGeom(n)
    return { w: g.w, h: chipH(n), gap: themeGap(n) }
}

function clearThemeMemberLayout(n) {
    var mem = n && n.members ? n.members : []
    var keys = ["chipShape", "chipSize", "circleSize", "chipFill", "fontSize", "color", "border", "textColor",
                "hlColor", "hlBorder", "hlText", "offX", "offY"]
    var i, k
    for (i = 0; i < mem.length; i++) {
        for (k = 0; k < keys.length; k++)
            delete mem[i][keys[k]]
    }
}

function applyFiveWayFormat(fmt) {
    var id = selectedId || groupEditId
    var n = nodeAt(id)
    if (!isFiveWay(n))
        return
    if (fmt !== "plus" && fmt !== "mini" && fmt !== "card" && fmt !== "radial")
        return
    ensureFiveWayRoles(n)
    clearThemeMemberLayout(n)
    n.format = fmt
    if (fmt === "radial") {
        n.leaders = buildRadialLeaders(n)
    } else if (n.leaders && n.leaders.length > 1) {
        n.leaders = [n.leaders[0]]
    }
    bump()
}

function resetFiveWayFormat() {
    var id = selectedId || groupEditId
    var n = nodeAt(id)
    if (!isFiveWay(n))
        return
    clearThemeMemberLayout(n)
    delete n.format
    if (n.leaders && n.leaders.length > 1)
        n.leaders = [n.leaders[0]]
    bump()
}

function buildRadialLeaders(n) {
    var mem = n.members || []
    var out = []
    var i
    for (i = 0; i < mem.length; i++) {
        out.push({
            id: n.id + "_R" + i,
            from: { type: "member", id: n.id, member: i, pin: "right" },
            to: { type: "hot", id: n.id },
            spines: [],
            curve: false
        })
    }
    return out
}

function beginGroupEdit(id) {
    var n = nodeAt(id || selectedId)
    if (!isGroup(n))
        return
    if (!themeLayout(n))
        ensureMemberOffsets(n)
    groupEditId = n.id
    selectedMember = 0
    setSelection([n.id])
    bump()
}

function endGroupEdit() {
    groupEditId = ""
    selectedMember = -1
    dragMember = -1
    if (dragKind === "member")
        dragKind = ""
    bump()
}

function ensureMemberOffsets(n) {
    var mem = n.members || []
    var i
    var any = false
    for (i = 0; i < mem.length; i++) {
        if (mem[i].ox !== undefined || mem[i].oy !== undefined) {
            any = true
            break
        }
    }
    if (any) {
        for (i = 0; i < mem.length; i++) {
            if (mem[i].ox === undefined) mem[i].ox = 0
            if (mem[i].oy === undefined) mem[i].oy = 0
        }
        return
    }
    // Default column. Do not keep a 5-way cross. ox/oy only used in free layout.
    var eh = Math.max(1, spaceRect().h)
    var pitch = stackPitch(n) / eh
    for (i = 0; i < mem.length; i++) {
        mem[i].ox = 0
        mem[i].oy = i * pitch
    }
}

function demoteSpecialKinds() {
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        if (!n)
            continue
        if (n.kind === "plus" || n.kind === "pair")
            n.kind = "stack"
    }
}

// What groupSelection can do with the selection: two or more chips, or one
// table with chips or text. Drawings alone can't be grouped (the menu offered
// it, then nothing happened).
function canGroup() {
    var ids = selectedIds || []
    if (ids.length < 2)
        return false
    var chips = 0
    var tables = 0
    var texts = 0
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n)
            continue
        if (isTable(n))
            tables++
        else if (isText(n))
            texts++
        else if (!isDraw(n))
            chips++
    }
    if (tables === 1)
        return chips + texts > 0
    return tables === 0 && chips >= 2
}

function canUngroup() {
    if (packTableFromSelection())
        return true
    var n = nodeAt(selectedId) || ctxTarget()
    return isGroup(n)
}

// Break Group, paste and the like make several ids in one millisecond, where
// the clock and a random number alone can repeat; the count cannot.
var _uidCount = 0

function _uid(prefix) {
    _uidCount++
    return prefix + "_" + Date.now().toString(36) + Math.floor(Math.random() * 1000) + "_" + _uidCount.toString(36)
}

function _styleOf(n) {
    return {
        color: n.color || "#18181B",
        border: n.border || "#3F3F46",
        textColor: n.textColor || "#E4E4E7",
        highlight: n.highlight !== false,
        hlColor: n.hlColor || "#14532D",
        hlBorder: n.hlBorder || "#22C55E",
        hlText: n.hlText || "#BBF7D0",
        fontSize: n.fontSize || 10,
        pin: n.pin || "right",
        curve: n.curve !== false,
        chipSize: n.chipSize || 18,
        chipShape: n.chipShape || "round",
        chipFill: n.chipFill || "filled",
        hotSize: n.hotSize || 9,
        hotShape: n.hotShape || "round",
        hotFill: n.hotFill || "filled"
    }
}

// Where a group member is drawn, in page fractions (its chip's top left,
// the same point a loose chip's chipFx/chipFy names).
function memberPageFx(n, mem) {
    return xToFx(fxToX(n.chipFx) + groupMinX(n) + memberLocalX(n, mem))
}

function memberPageFy(n, mem) {
    return yToFy(fyToY(n.chipFy) + groupMinY(n) + memberLocalY(n, mem))
}

// The chips a selected item brings to a new group, each where it is drawn
// now (fx/fy), so grouping never moves anything.
function _partsFrom(n) {
    var out = []
    if (!n)
        return out
    if (isGroup(n)) {
        var mem = n.members || []
        for (var i = 0; i < mem.length; i++)
            out.push({ hwId: mem[i].hwId, kind: memberKind(n, mem[i]), role: mem[i].role || "", src: n, friendly: mem[i].friendly || "",
                       fx: memberPageFx(n, mem[i]), fy: memberPageFy(n, mem[i]) })
    } else {
        out.push({ hwId: n.hwId, kind: n.kind || "btn", role: "", src: n, friendly: n.friendly || "",
                   fx: n.chipFx || 0, fy: n.chipFy || 0 })
    }
    return out
}

function groupSelection() {
    var ids = selectedIds || []
    if (ids.length < 2)
        return
    packWarn = ""
    var tables = []
    var chipNodes = []
    var textNodes = []
    var i
    var n
    for (i = 0; i < ids.length; i++) {
        n = nodeAt(ids[i])
        if (!n)
            continue
        if (isTable(n))
            tables.push(n)
        else if (isText(n))
            textNodes.push(n)
        else if (!isDraw(n))
            chipNodes.push(n)
    }
    if (!tables.length && chipNodes.length) {
        var inferred = tablesUnderChips(chipNodes)
        if (inferred.length > 1) {
            packWarn = "Chips sit on more than one table."
            bump()
            return
        }
        if (inferred.length === 1)
            tables = inferred
    }
    if (tables.length > 1) {
        packWarn = "Group one table at a time."
        bump()
        return
    }
    if (tables.length === 1) {
        if (!chipNodes.length && !textNodes.length) {
            packWarn = "Select chips or text with the table to pack."
            bump()
            return
        }
        var table = tables[0]
        for (i = 0; i < chipNodes.length; i++)
            attachChipToTable(table, chipNodes[i])
        for (i = 0; i < textNodes.length; i++)
            attachDrawToTable(table, textNodes[i])
        var keep = [table.id]
        for (i = 0; i < chipNodes.length; i++)
            keep.push(chipNodes[i].id)
        for (i = 0; i < textNodes.length; i++)
            keep.push(textNodes[i].id)
        setSelection(keep)
        bump()
        return
    }
    var parts = []
    var chipIds = []
    for (i = 0; i < ids.length; i++) {
        var chunkN = nodeAt(ids[i])
        if (!chunkN || isDraw(chunkN))
            continue
        chipIds.push(ids[i])
        var chunk = _partsFrom(chunkN)
        for (var p = 0; p < chunk.length; p++)
            parts.push(chunk[p])
    }
    if (parts.length < 2)
        return
    var axisN = 0
    for (i = 0; i < parts.length; i++) {
        if (parts[i].kind === "axis")
            axisN++
    }
    var kind = "stack"
    if (axisN === parts.length)
        kind = "axis_stack"
    var first = nodeAt(chipIds[0])
    var st = _styleOf(first)
    var hx = 0
    var hy = 0
    for (i = 0; i < chipIds.length; i++) {
        n = nodeAt(chipIds[i])
        hx += hotFxOf(n)
        hy += hotFyOf(n)
    }
    var c = chipIds.length
    var hx0 = hx / c
    var hy0 = hy / c
    // The group's anchor: the members' top-left corner, so ox/oy stay small.
    var ox0 = 1e9
    var oy0 = 1e9
    for (i = 0; i < parts.length; i++) {
        ox0 = Math.min(ox0, parts[i].fx)
        oy0 = Math.min(oy0, parts[i].fy)
    }
    // Reading order: top to bottom, then left to right.
    parts.sort(function(a, b) {
        var dy = a.fy - b.fy
        return dy !== 0 ? dy : (a.fx - b.fx)
    })
    var members = []
    for (i = 0; i < parts.length; i++)
        members.push({
            hwId: parts[i].hwId,
            kind: leafKind(parts[i].kind),
            role: parts[i].role || ("m" + i),
            ox: parts[i].fx - ox0,
            oy: parts[i].fy - oy0,
            friendly: carryFriendly(parts[i].friendly, carryFriendly(parts[i].src && parts[i].src.friendly, defaultFriendly(parts[i].kind, parts[i].hwId)))
        })
    var g = {
        id: _uid("g"), kind: kind, members: members,
        hotFx: hx0, hotFy: hy0, chipFx: ox0, chipFy: oy0,
        // "free": members stay exactly where they were placed by hand.
        pin: st.pin, spines: [], curve: st.curve, alignH: "free",
        color: st.color, border: st.border, textColor: st.textColor,
        highlight: st.highlight, hlColor: st.hlColor, hlBorder: st.hlBorder,
        hlText: st.hlText, fontSize: st.fontSize, label: "", chipSize: st.chipSize, chipShape: st.chipShape, chipFill: st.chipFill, hotSize: st.hotSize, hotShape: st.hotShape, hotFill: st.hotFill
    }
    g.from = { type: "chip", id: g.id, pin: g.pin }
    g.to = { type: "hot", id: g.id }
    g.leaders = [{
        id: g.id + "_L0",
        from: g.from,
        to: g.to,
        spines: [],
        curve: st.curve !== false
    }]
    var drop = {}
    for (i = 0; i < chipIds.length; i++)
        drop[chipIds[i]] = true
    var list = nodes || []
    for (i = list.length - 1; i >= 0; i--) {
        if (drop[list[i].id])
            list.splice(i, 1)
    }
    var oi, sj
    for (oi = 0; oi < list.length; oi++) {
        if (!list[oi].sockets)
            continue
        for (sj = 0; sj < list[oi].sockets.length; sj++) {
            if (drop[list[oi].sockets[sj].chipId])
                list[oi].sockets[sj].chipId = ""
        }
    }
    list.push(g)
    setSelection([g.id])
    bump()
}

function ungroupSelection() {
    var packed = packTableFromSelection()
    if (packed) {
        detachTablePacked(packed)
        bump()
        return
    }
    var n = nodeAt(selectedId)
    if (!isGroup(n))
        n = ctxTarget()
    if (!isGroup(n))
        return
    var mem = n.members || []
    if (!mem.length)
        return
    var st = _styleOf(n)
    var created = []
    var i
    // Break Group leaves everything as it is: each chip where it is drawn and
    // looking as it does in the group (its own style where it has one, the
    // group's otherwise). Each chip gets the group's hotspot.
    var looks = ["color", "border", "textColor", "highlight", "hlColor", "hlBorder", "hlText",
                 "fontSize", "chipSize", "circleSize", "chipShape", "chipFill"]
    for (i = 0; i < mem.length; i++) {
        var kindOf = memberKind(n, mem[i])
        var chip = {
            id: _uid(kindOf === "btn" ? "b" : kindOf.charAt(0)), kind: kindOf, hwId: mem[i].hwId,
            prefix: kindOf === "axis" ? "A" : "",
            label: "",
            friendly: carryFriendly(mem[i].friendly, defaultFriendly(kindOf, mem[i].hwId)),
            hotFx: hotFxOf(n), hotFy: hotFyOf(n),
            chipFx: memberPageFx(n, mem[i]),
            chipFy: memberPageFy(n, mem[i]),
            pin: st.pin, spines: [], curve: st.curve,
            hotSize: st.hotSize, hotShape: st.hotShape, hotFill: st.hotFill
        }
        for (var k = 0; k < looks.length; k++) {
            var look = styleVal(n, mem[i], looks[k], st[looks[k]])
            if (look !== undefined)
                chip[looks[k]] = look
        }
        created.push(chip)
    }
    var list = nodes || []
    var idx = nodeIndex(n.id)
    if (idx < 0)
        return
    // Leaders and callouts aimed at the group stay where they are drawn.
    freeEndsAimedAt(n.id, -1)
    list.splice(idx, 1)
    for (i = 0; i < created.length; i++)
        list.splice(idx + i, 0, created[i])
    groupEditId = ""
    selectedMember = -1
    setSelection([])
    bump()
}

function setGroupKind(kind) {
    var n = nodeAt(selectedId)
    if (!isGroup(n) || !kind)
        return
    n.kind = kind === "plus" ? "stack" : kind
    bump()
}

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Chips: lookup, names, placing from the pool, size and renaming.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function nodeAt(id) {
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        if (list[i].id === id) {
            return list[i]
        }
    }
    return null
}

function nodeIndex(id) {
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        if (list[i].id === id) {
            return i
        }
    }
    return -1
}

function destOf(kind, hwId) {
    tick
    if (!face) {
        return "—"
    }
    if (kind === "axis" || kind === "axis_stack") {
        return face.labelAxis(hwId)
    }
    if (kind === "hat") {
        return face.labelHat(hwId)
    }
    return face.labelBtn(hwId)
}

// Kind of one chip in a group: its own kind when saved. Files saved before
// members carried a kind fall back to the group: an axis stack holds axes,
// any other group buttons.
function memberKind(n, mem) {
    var own = mem && mem.kind ? String(mem.kind) : ""
    if (own === "axis" || own === "hat")
        return own
    if (own === "btn" || own === "button")
        return "btn"
    return (n && n.kind === "axis_stack") ? "axis" : "btn"
}

function leafKind(kind) {
    if (kind === "axis_stack")
        return "axis"
    if (kind === "plus" || kind === "pair" || kind === "stack")
        return "btn"
    return kind || "btn"
}

function physicalName(kind, hwId) {
    var k = leafKind(kind) + ":" + hwId
    return physNames[k] || ""
}

function hardwareLabel(kind, hwId) {
    var lk = leafKind(kind)
    if (lk === "axis")
        return "Axis " + hwId
    if (lk === "hat")
        return "Hat " + hwId
    return "Button " + hwId
}

function defaultFriendly(kind, hwId) {
    return hardwareLabel(kind, hwId)
}

function isClearedFriendly(v) {
    return v === "" || (typeof v === "string" && !String(v).trim().length)
}

function isUserFriendly(kind, hwId, v) {
    if (v === undefined || v === null || isClearedFriendly(v))
        return false
    var t = String(v).trim()
    if (!t.length)
        return false
    if (t === hardwareLabel(kind, hwId))
        return false
    if (t === physicalName(kind, hwId))
        return false
    return true
}

function carryFriendly(v, fallback) {
    if (isClearedFriendly(v))
        return ""
    if (v !== undefined && v !== null && String(v).length)
        return v
    return fallback
}

function friendlyOf(n, mem) {
    if (mem) {
        var lk = memberKind(n, mem)
        if (isUserFriendly(lk, mem.hwId, mem.friendly))
            return String(mem.friendly).trim()
        return hardwareLabel(lk, mem.hwId)
    }
    if (!n)
        return ""
    if (isGroup(n)) {
        if (n.friendly && !isClearedFriendly(n.friendly) && n.friendly !== n.id)
            return n.friendly
        if (n.label && String(n.label).length)
            return n.label
        return n.id
    }
    if (isDraw(n))
        return (n.friendly && String(n.friendly).length) ? n.friendly : "Draw"
    if (isUserFriendly(n.kind, n.hwId, n.friendly))
        return String(n.friendly).trim()
    if (n.label && String(n.label).length && isUserFriendly(n.kind, n.hwId, n.label))
        return String(n.label).trim()
    return hardwareLabel(n.kind, n.hwId)
}

function fullNameOf(kind, hwId) {
    var lk = leafKind(kind)
    var idn = lk === "axis" ? ("Axis " + hwId) : (lk === "hat" ? ("Hat " + hwId) : ("Button " + hwId))
    var phys = physicalName(lk, hwId)
    var dest = destOf(lk, hwId)
    var s = idn
    if (phys.length)
        s += " · " + phys
    if (dest && dest !== "—")
        s += " → " + dest
    return s
}

// What a chip shows (Options → Button Map → Labels): its name, what the
// control does in the profile (actionLabels, filled by the window for the
// chosen mode), or both. Renaming always edits the name.
function chipText(n, mem) {
    var name = mem ? memberLabel(n, mem) : friendlyOf(n, null)
    if (chipTextMode !== "Action" && chipTextMode !== "Name and action")
        return name
    var kind = mem ? memberKind(n, mem) : leafKind(n.kind)
    var hwId = mem ? mem.hwId : n.hwId
    var act = (actionLabels && actionLabels[kind + ":" + hwId]) || ""
    if (chipTextMode === "Name and action")
        return act.length ? name + ": " + act : name
    if (act.length)
        return act
    if (unboundText === "Blank")
        return ""
    if (unboundText === "Dash")
        return "—"
    return name
}

function placedId(kind, hwId) {
    var want = leafKind(kind) + ":" + hwId
    var list = nodes || []
    for (var i = 0; i < list.length; i++) {
        var n = list[i]
        if (isGroup(n)) {
            var mem = n.members || []
            for (var j = 0; j < mem.length; j++) {
                if (memberKind(n, mem[j]) + ":" + mem[j].hwId === want)
                    return n.id
            }
        } else if (leafKind(n.kind) + ":" + n.hwId === want) {
            return n.id
        }
    }
    return ""
}

function catalog() {
    tick
    var rows = (face && face.chipRows) ? face.chipRows : []
    var seen = {}
    var items = []
    var i
    for (i = 0; i < rows.length; i++) {
        var row = rows[i]
        if (!row)
            continue
        var kind = row.kind || "btn"
        var hwId = row.hwId
        var key = kind + ":" + hwId
        if (seen[key])
            continue
        seen[key] = true
        var pid = placedId(kind, hwId)
        var lk = leafKind(kind)
        var hwName = lk === "axis" ? ("Axis " + hwId) : (lk === "hat" ? ("Hat " + hwId) : ("Button " + hwId))
        items.push({
            kind: kind,
            hwId: hwId,
            key: key,
            friendly: defaultFriendly(kind, hwId),
            hwName: hwName,
            dest: row.dest || destOf(lk, hwId),
            fullName: row.dest || fullNameOf(kind, hwId),
            placed: pid.length > 0,
            placedId: pid
        })
    }
    return items
}

function hotFxOf(n) {
    if (!n)
        return 0.5
    if (n.hotFx !== undefined && n.hotFx === n.hotFx)
        return n.hotFx
    if (n.chipFx !== undefined && n.chipFx === n.chipFx)
        return n.chipFx
    return 0.5
}

function hotFyOf(n) {
    if (!n)
        return 0.5
    if (n.hotFy !== undefined && n.hotFy === n.hotFy)
        return n.hotFy
    if (n.chipFy !== undefined && n.chipFy === n.chipFy)
        return n.chipFy
    return 0.5
}

// chipOnly (Button Map Options → Chip only): the chip on its own, with no
// leader and its hotspot hidden; both can be added from its menu later.
function addChiplet(kind, hwId, wx, wy, chipOnly) {
    kind = leafKind(kind)
    hwId = parseInt(hwId, 10)
    if (!(hwId > 0))
        return
    var existing = placedId(kind, hwId)
    if (existing) {
        setSelection([existing])
        bump()
        return
    }
    var fx
    var fy
    if (wx !== undefined && wy !== undefined && wx !== null && wy !== null) {
        fx = xToFx(wx)
        fy = yToFy(wy)
    } else {
        var c = viewCenterPage()
        fx = c.x
        fy = c.y
    }
    fx = Math.max(0.04, Math.min(0.92, fx))
    fy = Math.max(0.04, Math.min(0.94, fy))
    var st = _styleOf({})
    var n = {
        id: _uid(kind === "btn" ? "b" : kind.charAt(0)),
        kind: kind,
        hwId: hwId,
        prefix: kind === "axis" ? "A" : (kind === "hat" ? "H" : ""),
        label: "",
        friendly: defaultFriendly(kind, hwId),
        hotFx: fx,
        hotFy: fy,
        chipFx: fx,
        chipFy: fy,
        pin: fx < 0.5 ? "right" : "left",
        spines: [],
        curve: st.curve,
        color: st.color,
        border: st.border,
        textColor: st.textColor,
        highlight: st.highlight,
        hlColor: st.hlColor,
        hlBorder: st.hlBorder,
        hlText: st.hlText,
        fontSize: st.fontSize,
        chipSize: st.chipSize,
        chipShape: st.chipShape,
        chipFill: st.chipFill,
        hotSize: st.hotSize,
        hotShape: st.hotShape,
        hotFill: st.hotFill
    }
    if (chipOnly) {
        n.leaders = []
        n.hotHidden = true
    }
    var list = nodes || []
    list.push(n)
    setSelection([n.id])
    bump()
}

function ensureFriendly(n) {
    if (!n)
        return
    if (isGroup(n)) {
        var mem = n.members || []
        for (var i = 0; i < mem.length; i++) {
            if (mem[i].friendly === undefined || mem[i].friendly === null)
                mem[i].friendly = defaultFriendly(memberKind(n, mem[i]), mem[i].hwId)
        }
        if (n.friendly === undefined || n.friendly === null)
            n.friendly = n.label && n.label.length ? n.label : n.id
    } else if (isDraw(n)) {
        if (n.friendly === undefined || n.friendly === null)
            n.friendly = "Draw"
    } else if (n.friendly === undefined || n.friendly === null) {
        n.friendly = (n.label && n.label.length) ? n.label : defaultFriendly(n.kind, n.hwId)
    }
}

function litOf(kind, hwId) {
    tick
    if (!face) {
        return false
    }
    if (kind === "axis" || kind === "axis_stack") {
        return Math.abs(face.hwAxis(hwId)) > 0.12
    }
    if (kind === "hat") {
        return face.hwHat(hwId) > 0.5
    }
    return face.hwButton(hwId) > 0.5
}

function chipXY(n) {
    if (!n)
        return Qt.point(0, 0)
    return Qt.point(fxToX(n.chipFx), fyToY(n.chipFy))
}

function pinPt(n, item, side) {
    if (!item) {
        return chipXY(n)
    }
    var pin = side || (n ? n.pin : "right") || "right"
    var x = pin === "right" ? item.width : (pin === "left" ? 0 : item.width * 0.5)
    var y = pin === "top" ? 0 : (pin === "bottom" ? item.height : item.height * 0.5)
    return item.mapToItem(_ed, x, y)
}

function chipH(n, mem) {
    var sz = styleVal(n, mem, "chipSize", 18)
    var fs = styleVal(n, mem, "fontSize", 10)
    return uiPx(Math.max(sz, fs + 8))
}

function chipR(n, h, mem) {
    return styleVal(n, mem, "chipShape", "round") === "square" ? 0 : Math.max(2, h * 0.5)
}

function chipIsHollow(n, mem) {
    return styleVal(n, mem, "chipFill", "filled") === "hollow"
}

function hotSz(n) {
    return uiPx((n && n.hotSize) ? n.hotSize : 9)
}

function chipBounds(n) {
    if (!n)
        return { x: 0, y: 0, w: 40, h: 20 }
    var i = nodeIndex(n.id)
    var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
    if (it && it.width > 1)
        return { x: it.x, y: it.y, w: it.width, h: it.height }
    return {
        x: fxToX(n.chipFx || 0),
        y: fyToY(n.chipFy || 0),
        w: 80,
        h: chipH(n)
    }
}

function hoverLabelAt(mx, my) {
    var list = nodes || []
    var i
    for (i = list.length - 1; i >= 0; i--) {
        var n = list[i]
        if (!n || isDraw(n))
            continue
        if (isGroup(n)) {
            var mi = memberHit(n, mx, my)
            if (mi >= 0 && n.members && n.members[mi])
                return systemName(n, n.members[mi])
            continue
        }
        var it = _chips.itemAt(i)
        if (!it)
            continue
        var p = it.mapFromItem(_ed, mx, my)
        if (p.x >= 0 && p.y >= 0 && p.x <= it.width && p.y <= it.height)
            return systemName(n, null)
    }
    return ""
}

function setChipTip(mx, my) {
    hoverTipX = mx
    hoverTipY = my
    if (dragKind || banding || renameId)
        hoverHwLabel = ""
    else
        hoverHwLabel = hoverLabelAt(mx, my)
}

function chipScreenRect(n, mem) {
    if (!n)
        return Qt.rect(0, 0, 40, 20)
    if (isTable(n) && tableHasTarget()) {
        var tr = tableCurrentRect(n)
        return Qt.rect(tr.x, tr.y, tr.w, tr.h)
    }
    if (isText(n) || isDraw(n)) {
        var dg = drawGeom(n)
        return Qt.rect(dg.x, dg.y, dg.w, dg.h)
    }
    if (isGroup(n) && mem) {
        return Qt.rect(
            fxToX(n.chipFx) + groupMinX(n) + memberLocalX(n, mem),
            fyToY(n.chipFy) + groupMinY(n) + memberLocalY(n, mem),
            Math.max(24, chipWGuess(n, mem)),
            chipH(n, mem)
        )
    }
    return Qt.rect(
        fxToX(n.chipFx),
        fyToY(n.chipFy),
        Math.max(24, chipWGuess(n, null)),
        chipH(n, null)
    )
}

function beginRename(id, memberIndex) {
    var n = nodeAt(id)
    if (!n || isDraw(n))
        return
    var mem = null
    if (isGroup(n) && memberIndex >= 0 && n.members && memberIndex < n.members.length)
        mem = n.members[memberIndex]
    renameId = id
    renameMember = mem ? memberIndex : -1
    renameDraft = mem ? memberLabel(n, mem) : friendlyOf(n, null)
    dragKind = ""
    Qt.callLater(function () {
        if (_nameEdit) {
            _nameEdit.forceActiveFocus()
            _nameEdit.selectAll()
        }
    })
    bump()
}

function commitRename() {
    if (!renameId)
        return
    var n = nodeAt(renameId)
    if (!n) {
        cancelRename()
        return
    }
    var t = String(renameDraft || "").trim()
    if (isText(n)) {
        n.text = t
        fitTextBox(n)
    } else if (isTable(n) && tableHasTarget()) {
        ensureTable(n)
        if (tableExtra >= 0) {
            var ex = tableExtraAt(n, tableExtra)
            if (ex)
                ex.text = t
        } else if (n.rows[tableRow] && n.rows[tableRow].cells && n.rows[tableRow].cells[tableCol]) {
            n.rows[tableRow].cells[tableCol].text = t
        }
    } else if (isGroup(n) && renameMember >= 0 && n.members && renameMember < n.members.length) {
        n.members[renameMember].friendly = t
    } else {
        n.friendly = t
    }
    cancelRename()
    bump()
}

function cancelRename() {
    renameId = ""
    renameMember = -1
    renameDraft = ""
}

function chipWGuess(n, mem) {
    var fs = styleVal(n, mem, "fontSize", 10)
    var sz = styleVal(n, mem, "chipSize", 18)
    var s = mem ? memberLabel(n, mem) : friendlyOf(n, null)
    var pad = Math.max(10, sz * 0.55)
    if (fiveWayFormat(n) === "mini" && !memberHasCustomName(n, mem))
        return uiPx(Math.max(18, fs + 10))
    return uiPx(String(s).length * fs * 0.50 + pad)
}

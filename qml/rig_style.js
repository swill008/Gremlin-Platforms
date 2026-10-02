// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Chip, hotspot and leader styling: style keys, defaults and applying a field to the selection.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
.import "rig_shapes.js" as Shapes

// A colour as drawn: while exporting a light page for printing, with its
// lightness turned over (dark fills light, light text dark); otherwise as is.
function ink(c) {
    if (!exporting || !printLight)
        return c
    return Shapes.invertLightness(String(c))
}

function isStyleKey(key) {
    return key === "chipShape" || key === "chipSize" || key === "chipFill" || key === "fontSize"
        || key === "color" || key === "border" || key === "textColor" || key === "highlight"
        || key === "hlColor" || key === "hlBorder" || key === "hlText"
}

function targetMember() {
    var n = nodeAt(selectedId)
    if (!n || !isGroup(n) || groupEditId !== n.id || selectedMember < 0)
        return null
    var mem = n.members || []
    if (selectedMember >= mem.length)
        return null
    return mem[selectedMember]
}

function styleVal(n, mem, key, fallback) {
    if (mem && mem[key] !== undefined && mem[key] !== null && mem[key] !== "")
        return mem[key]
    if (n && n[key] !== undefined && n[key] !== null && n[key] !== "")
        return n[key]
    return fallback
}

function applyField(key, val) {
    var mem = targetMember()
    if (mem && isStyleKey(key)) {
        mem[key] = val
        bump()
        return
    }
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (n) {
            n[key] = val
            if (isText(n) && (key === "color" || key === "border" || key === "textColor"))
                delete n.theme
            if (isText(n) && (key === "wrap" || key === "fontSize" || key === "bold"))
                fitTextBox(n)
        }
    }
    bump()
}

function fieldEq(key, val, fallback) {
    var n = nodeAt(selectedId)
    var mem = targetMember()
    var cur = styleVal(n, mem, key, undefined)
    if (cur === undefined || cur === null || cur === "")
        return val === fallback
    return cur === val
}

function styleDefault(key) {
    if (key === "color") return "#18181B"
    if (key === "border") return "#3F3F46"
    if (key === "textColor") return "#E4E4E7"
    if (key === "hlColor") return "#14532D"
    if (key === "hlBorder") return "#22C55E"
    if (key === "hlText") return "#BBF7D0"
    if (key === "leaderColor") return "#A1A1AA"
    if (key === "hotColor") return "#F4F4F5"
    if (key === "hotPressColor") return styleDefault("hlBorder")
    return ""
}

function pickColor(field) {
    var n = nodeAt(selectedId)
    var mem = (field === "leaderColor" || field === "hotColor" || field === "hotPressColor") ? null : targetMember()
    colorPickRequested(field, styleVal(n, mem, field, styleDefault(field)))
}

function uiPx(px) {
    var v = (px || 0) * uiScale
    return v < 1 ? 1 : v
}

function leaderWidthOf(n) {
    var w = n && n.leaderWidth
    if (!(w > 0))
        w = 1.1
    w = Math.max(0.5, Math.min(4, w))
    return Math.max(0.6, w * uiScale)
}

function resetMemberStyle() {
    var mem = targetMember()
    if (!mem)
        return
    var keys = ["chipShape", "chipSize", "chipFill", "fontSize", "color", "border", "textColor", "hlColor", "hlBorder", "hlText", "offX", "offY"]
    var i
    for (i = 0; i < keys.length; i++)
        delete mem[keys[i]]
    bump()
}

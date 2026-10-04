// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Saved styles: a chip's, shape's, line's or text box's look kept under a
// name (Options → Button Map → Library lists them) and put on other items of
// the same kind from the right-click menu.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

var _FIELDS = {
    chip: ["chipShape", "chipSize", "circleSize", "chipFill", "fontSize", "color", "border", "textColor",
           "textAlign", "alignRowsApart", "rowAlign1", "rowAlign2",
           "highlight", "hlColor", "hlBorder", "hlText", "hotSize", "hotShape", "hotFill",
           "hotColor", "hotLine", "hotOpacity", "hotHalo", "hotNumber", "hotPress", "hotPressColor",
           "hotPulse", "hotLive", "leaderColor", "leaderWidth"],
    shape: ["fill", "color", "border", "stroke", "dash", "opacity"],
    line: ["border", "stroke", "dash", "opacity", "headStart", "headEnd"]
}

// "chip", "shape", "line", "text", or "" for what has no style to save
// (pictures, tables).
function styleKindOf(n) {
    if (!n)
        return ""
    if (!isDraw(n))
        return "chip"
    if (isText(n))
        return "text"
    if (isLine(n) || isPath(n))
        return "line"
    if (isTable(n) || isOverlay(n))
        return ""
    return "shape"
}

function _fieldNames(kind) {
    return kind === "text" ? textFormatKeys() : (_FIELDS[kind] || [])
}

// The look of an item: the style fields it has set.
function styleFieldsOf(n) {
    var keys = _fieldNames(styleKindOf(n))
    var out = {}
    for (var i = 0; i < keys.length; i++) {
        var v = n[keys[i]]
        if (v !== undefined && v !== null && v !== "")
            out[keys[i]] = v
    }
    return out
}

// Asks the window for a name to save the item's look under.
function saveStyleOf(id) {
    var n = nodeAt(id)
    var kind = styleKindOf(n)
    if (!kind)
        return
    saveStyleRequested(kind, JSON.stringify(styleFieldsOf(n)))
}

// Puts a saved look on every selected item of its kind, as one undo step.
function applySavedStyle(style) {
    if (!style || !style.fields)
        return
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!n || isLocked(n) || styleKindOf(n) !== style.kind)
            continue
        var ends = isLine(n) ? lineEndsAt(n) : null
        var pts = isPath(n) ? pathPointsAt(n) : null
        for (var key in style.fields) {
            if (style.fields.hasOwnProperty(key))
                n[key] = style.fields[key]
        }
        // A line or path is re-fitted round its points for the new width.
        if (ends)
            setLineEnds(n, ends.ax, ends.ay, ends.bx, ends.by)
        if (pts)
            setPathPoints(n, pts)
        if (isText(n))
            fitTextBox(n)
    }
    bump()
}

// The saved looks for one kind of item.
function stylesFor(kind) {
    return (savedStyles || []).filter(function(s) { return s.kind === kind })
}

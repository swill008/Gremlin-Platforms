// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The Device Mapping Editor's Insert, Arrange and Format menus (07 S134).
// Imported by the window as RigCommands. The menu bar has no right-click
// target, so every command acts on the editor's selection (ed.selectedId /
// ed.selectedIds) through the same editor functions the right-click menu
// (rig_menu.js) calls, and is greyed out where that menu would not offer it.
//
// list(ed)       -> [{ id, menu, sub, text, key, hintOnly }] in menu order.
//                   sub names a submenu ("" for none). hintOnly: the window
//                   already has a Shortcut for that key, so only the hint is
//                   shown. ed is optional (the rotate step in the text).
// enabled(ed, id) -> bool
// whyDisabled(ed, id) -> string: why a greyed row can't be used now ("" when
//                   there is no reason to give), shown as its tooltip (S121).
// run(ed, id)     -> runs it, then noteRun
//
// The Edit commands (07 S136 S137) have ids too, so they can be favourites
// and repeated, but are not in list(): the window's Edit menu is written by
// hand.
// info(id) / info(ed, id) -> { id, text, key } (null for an unknown id): the
//                   label Favourites and Repeat show.
// applies(ed, id) -> bool: usable on the current selection (a favourite shows
//                   only then).
// noteRun(ed, id) -> remembers the last command for Repeat (not NO_REPEAT).
// repeatLabel(ed) -> 'Repeat "Rotate +90°"', "" when nothing to repeat.
// canRepeat(ed)   -> bool: the last command applies now.
// repeat(ed)      -> runs the last command again.

// --- the selection -----------------------------------------------------------

function _ids(ed) {
    var ids = ed.selectedIds || []
    return ids.length ? ids : (ed.selectedId ? [ed.selectedId] : [])
}

function _node(ed) {
    return ed.selectedId ? ed.nodeAt(ed.selectedId) : null
}

function _multi(ed) {
    return (ed.selectedIds || []).length > 1 && ed.isSelected(ed.selectedId)
}

// Lock and Hide act on the whole selection when several are selected.
function _arrangeIds(ed) {
    return _multi(ed) ? ed.selectedIds.slice() : (ed.selectedId ? [ed.selectedId] : [])
}

// The table cell the menus act on still exists in the selected table (a
// stale row, column or extra cell from another table or an undo doesn't).
function _tableTargetOk(ed) {
    return typeof ed.tableTargetValid === "function" ? !!ed.tableTargetValid() : ed.tableHasTarget()
}

// The target is set but no longer exists.
function _tableTargetStale(ed) {
    var set = ed.tableExtra >= 0 || ed.tableRow >= 0 || ed.tableCol >= 0
    return set && !_tableTargetOk(ed)
}

// What kind of item one node is, as rig_menu's _multiKind (a group is a
// chip there).
function _kindOf(ed, n) {
    if (!ed.isDraw(n))
        return "chip"
    if (ed.isTable(n))
        return "table"
    if (ed.isText(n))
        return "text"
    if (ed.isOverlay(n))
        return "image"
    if (ed.isLine(n))
        return "line"
    if (ed.isPath(n))
        return "path"
    return "shape"
}

// The kind the selection's rows come from: one item's kind (group for a
// group), the shared kind of several, "mixed" for a mix, "" for nothing.
function _selKind(ed) {
    var n = _node(ed)
    if (!n)
        return ""
    if (!_multi(ed))
        return ed.isGroup(n) ? "group" : _kindOf(ed, n)
    var kinds = {}
    var ids = ed.selectedIds
    for (var i = 0; i < ids.length; i++) {
        var m = ed.nodeAt(ids[i])
        if (m)
            kinds[_kindOf(ed, m)] = true
    }
    var list = Object.keys(kinds)
    return list.length === 1 ? list[0] : "mixed"
}

// One item selected (not several), of these kinds.
function _single(ed, kinds) {
    if (_multi(ed))
        return false
    var k = _selKind(ed)
    return k !== "" && kinds.indexOf(k) >= 0
}

// Chips and groups: what the chip, group and leader menus offer.
function _chipLike(ed) {
    var k = _selKind(ed)
    return k === "chip" || k === "group"
}

function _rotateStep(ed) {
    return (ed && ed.rotateSnap) ? ed.rotateSnap : 15
}

// --- the commands --------------------------------------------------------------

// Draw tools, as the canvas menu's Draw rows.
var _SHAPES = [["rect", "Rectangle"], ["roundrect", "Rounded"], ["ellipse", "Ellipse"],
               ["triangle", "Triangle"], ["diamond", "Diamond"], ["arrow", "Arrow"],
               ["arrow2", "Double arrow"]]
var _LINES = [["line", "Line"], ["arrowline", "Arrow"], ["path", "Path"], ["pen", "Freehand"]]
var _BOXES = [["text", "Text box"], ["callout", "Callout"], ["table", "Table"]]
var _AROUND = [["rect", "Rectangle"], ["roundrect", "Rounded"], ["ellipse", "Ellipse"],
               ["triangle", "Triangle"], ["diamond", "Diamond"]]

var _ALIGN = [["left", "Left"], ["center", "Center"], ["right", "Right"],
              ["top", "Top"], ["middle", "Middle"], ["bottom", "Bottom"]]

var _PLACE = [["left", "Far Left"], ["center", "Center"], ["right", "Far Right"],
              ["top", "Top"], ["middle", "Middle"], ["bottom", "Bottom"]]

function _c(id, menu, sub, text, key, hintOnly) {
    return { id: id, menu: menu, sub: sub || "", text: text, key: key || "", hintOnly: !!hintOnly }
}

// The order users see (user 2026-10-11: "as user friendly and efficient as
// can be"): each menu's groups, "-" a separator; a "sub/-" id a separator
// inside that submenu. Ids not named here keep their place at the end.
var _ORDER = {
    Insert: ["@Shape", "@Line", "@Text", "-", "importPicture", "-",
             "@Shape Around Selection", "-", "stopDrawing"],
    Arrange: ["bringToFront", "bringForward", "sendBackward", "sendToBack", "-",
              "moveToBackground", "moveToForeground", "-",
              "@Align", "@Distribute", "-",
              "flipH", "flipV", "rotatePlus", "rotateMinus", "-",
              "resetShape", "editPoints", "crop", "resetCrop", "resetPicture", "@Snap Points", "-",
              "group", "breakGroup", "editGroup", "doneGroup", "-",
              "lock", "unlockAll", "hide", "-", "rename"],
    Format: ["editText", "-", "copyFormat", "pasteFormat", "clearFormatting", "saveStyle", "-",
             "@Colors", "-", "@Table", "@Table Cell"]
}
// Separators inside submenus, after the named ids.
var _SUB_SEPS = { "Colors": ["color.text", "color.hlText"],
                  "Table": ["table.spawnCell", "table.idCol"] }

function _ordered(items) {
    var out = []
    var used = {}
    var menus = ["Insert", "Arrange", "Leader", "Format"]
    for (var m = 0; m < menus.length; m++) {
        var name = menus[m]
        var mine = items.filter(function(c) { return c.menu === name })
        var order = _ORDER[name]
        if (!order) {
            mine.forEach(function(c) { out.push(c) })
            continue
        }
        for (var k = 0; k < order.length; k++) {
            var key = order[k]
            if (key === "-") {
                out.push(_c("-", name, "", ""))
            } else if (key.charAt(0) === "@") {
                var sub = key.substring(1)
                var seps = _SUB_SEPS[sub] || []
                mine.forEach(function(c) {
                    if (c.sub !== sub || used[c.id])
                        return
                    out.push(c)
                    used[c.id] = true
                    if (seps.indexOf(c.id) >= 0)
                        out.push(_c("-", name, sub, ""))
                })
            } else {
                mine.forEach(function(c) {
                    if (c.id === key && !used[c.id]) {
                        out.push(c)
                        used[c.id] = true
                    }
                })
            }
        }
        mine.forEach(function(c) { if (!used[c.id] && c.id !== "-") out.push(c) })
    }
    return out
}

// On/off commands: whether a tick shows beside them (07 S134). Undefined
// for every other command.
var CHECKABLE = { "crop": true, "table.idCol": true }

function checked(ed, id) {
    if (!ed || !CHECKABLE[id])
        return false
    var n = ed.nodeAt ? ed.nodeAt(ed.selectedId) : null
    if (id === "crop")
        return !!n && ed.cropId === n.id
    if (id === "table.idCol")
        return !!n && !!n.idCol
    return false
}

// The Edit menu's commands (menu "Edit"), outside list().
var _EDIT = [["edit.cut", "Cut", "Ctrl+X"], ["edit.copy", "Copy", "Ctrl+C"],
             ["edit.paste", "Paste", "Ctrl+V"], ["edit.duplicate", "Duplicate", "Ctrl+D"],
             ["edit.delete", "Delete", "Delete"], ["edit.selectAll", "Select All", "Ctrl+A"]]

function list(ed) {
    var step = _rotateStep(ed)
    var out = []
    var i
    // Insert
    for (i = 0; i < _SHAPES.length; i++)
        out.push(_c("draw." + _SHAPES[i][0], "Insert", "Shape", _SHAPES[i][1]))
    for (i = 0; i < _LINES.length; i++)
        out.push(_c("draw." + _LINES[i][0], "Insert", "Line", _LINES[i][1]))
    for (i = 0; i < _BOXES.length; i++)
        out.push(_c("draw." + _BOXES[i][0], "Insert", "Text", _BOXES[i][1]))
    for (i = 0; i < _AROUND.length; i++)
        out.push(_c("around." + _AROUND[i][0], "Insert", "Shape Around Selection", _AROUND[i][1]))
    // Its own Esc Shortcut, on only while a draw tool is active, so Esc
    // stops drawing wherever the keyboard is (G45) and never meets the
    // window's Esc that leaves Background mode (that one waits for no tool).
    out.push(_c("stopDrawing", "Insert", "", "Stop Drawing", "Esc"))
    out.push(_c("importPicture", "Insert", "", "Import Picture…"))
    out.push(_c("table.rowAbove", "Format", "Table", "Insert Row Above"))
    out.push(_c("table.rowBelow", "Format", "Table", "Add Row Below"))
    out.push(_c("table.colLeft", "Format", "Table", "Insert Column Left"))
    out.push(_c("table.colRight", "Format", "Table", "Add Column Right"))
    out.push(_c("table.spawnCell", "Format", "Table", "Spawn Empty Cell"))
    out.push(_c("table.idCol", "Format", "Table", "ID Column"))
    out.push(_c("table.deleteRow", "Format", "Table", "Delete This Row"))
    out.push(_c("table.deleteCol", "Format", "Table", "Delete This Column"))
    out.push(_c("table.deleteCell", "Format", "Table", "Delete This Cell"))
    out.push(_c("table.delete", "Format", "Table", "Delete Table"))
    // Arrange
    out.push(_c("bringToFront", "Arrange", "", "Bring to Front", "Ctrl+Shift+]"))
    out.push(_c("bringForward", "Arrange", "", "Bring Forward", "Ctrl+]"))
    out.push(_c("sendBackward", "Arrange", "", "Send Backward", "Ctrl+["))
    out.push(_c("sendToBack", "Arrange", "", "Send to Back", "Ctrl+Shift+["))
    // One key for both: the window's Ctrl+Shift+B moves to the other plane.
    out.push(_c("moveToBackground", "Arrange", "", "Move to Background", "Ctrl+Shift+B", true))
    out.push(_c("moveToForeground", "Arrange", "", "Move to Foreground", "Ctrl+Shift+B", true))
    out.push(_c("flipH", "Arrange", "", "Flip Horizontally", "Shift+H"))
    out.push(_c("flipV", "Arrange", "", "Flip Vertically", "Shift+V"))
    out.push(_c("rotatePlus", "Arrange", "", "Rotate +" + step + "°", "Ctrl+Alt+Right"))
    out.push(_c("rotateMinus", "Arrange", "", "Rotate −" + step + "°", "Ctrl+Alt+Left"))
    for (i = 0; i < _ALIGN.length; i++)
        out.push(_c("align." + _ALIGN[i][0], "Arrange", "Align", _ALIGN[i][1]))
    out.push(_c("distribute.h", "Arrange", "Distribute", "Across"))
    out.push(_c("distribute.v", "Arrange", "Distribute", "Down"))
    out.push(_c("editPoints", "Arrange", "", "Edit Points"))
    out.push(_c("resetShape", "Arrange", "", "Reset Shape"))
    out.push(_c("crop", "Arrange", "", "Crop"))
    out.push(_c("resetCrop", "Arrange", "", "Reset Crop"))
    out.push(_c("resetPicture", "Arrange", "", "Reset Picture"))
    out.push(_c("snap.add", "Arrange", "Snap Points", "Add Snap Point"))
    out.push(_c("snap.clear", "Arrange", "Snap Points", "Clear Snap Points"))
    out.push(_c("group", "Arrange", "", "Group Selected", "Ctrl+G", true))
    out.push(_c("breakGroup", "Arrange", "", "Break Group", "Ctrl+Shift+G", true))
    out.push(_c("editGroup", "Arrange", "", "Edit Group"))
    out.push(_c("doneGroup", "Arrange", "", "Done Editing Group"))
    out.push(_c("lock", "Arrange", "", "Lock / Unlock", "Ctrl+L", true))
    out.push(_c("unlockAll", "Arrange", "", "Unlock All", "Ctrl+Shift+L", true))
    out.push(_c("hide", "Arrange", "", "Hide", "Ctrl+Shift+H"))
    out.push(_c("rename", "Arrange", "", "Rename", "F2"))
    // Leader (07 S134, user 2026-10-11: leaders and callouts in a menu of
    // their own). A "-" id is a separator between its groups.
    out.push(_c("addLeader", "Leader", "", "Add Leader"))
    out.push(_c("addCallout", "Leader", "", "Add Callout"))
    out.push(_c("addPointer", "Leader", "", "Add Pointer"))
    out.push(_c("addStraightSpine", "Leader", "", "Add Straight Spine"))
    out.push(_c("addCurvedSpine", "Leader", "", "Add Curved Spine"))
    out.push(_c("-", "Leader", "", ""))
    out.push(_c("ends.detachChip", "Leader", "", "Detach Chip End"))
    out.push(_c("ends.detachHot", "Leader", "", "Detach Hotspot End"))
    out.push(_c("ends.toChip", "Leader", "", "Reconnect to This Chip"))
    out.push(_c("ends.toHot", "Leader", "", "Reconnect to This Hotspot"))
    out.push(_c("ends.branch", "Leader", "", "Branch from This End"))
    out.push(_c("ends.clearSpines", "Leader", "", "Clear All Spines"))
    out.push(_c("ends.deleteLeader", "Leader", "", "Delete Leader"))
    out.push(_c("-", "Leader", "", ""))
    out.push(_c("callout.detach", "Leader", "", "Detach from Chip"))
    out.push(_c("callout.remove", "Leader", "", "Remove Pointer"))
    out.push(_c("detachFromChips", "Leader", "", "Detach from Chips"))
    // Format
    out.push(_c("copyFormat", "Format", "", "Copy Format", "Ctrl+Alt+C"))
    out.push(_c("pasteFormat", "Format", "", "Paste Format", "Ctrl+Alt+V"))
    out.push(_c("clearFormatting", "Format", "", "Clear Formatting"))
    out.push(_c("saveStyle", "Format", "", "Save This Style…"))
    out.push(_c("color.fill", "Format", "Colors", "Fill Color…"))
    out.push(_c("color.outline", "Format", "Colors", "Outline Color…"))
    out.push(_c("color.text", "Format", "Colors", "Text Color…"))
    out.push(_c("color.hlFill", "Format", "Colors", "Pressed Fill…"))
    out.push(_c("color.hlOutline", "Format", "Colors", "Pressed Outline…"))
    out.push(_c("color.hlText", "Format", "Colors", "Pressed Text…"))
    out.push(_c("color.hot", "Format", "Colors", "Hotspot Color…"))
    out.push(_c("color.hotPress", "Format", "Colors", "Hotspot Pressed Color…"))
    out.push(_c("color.leader", "Format", "Colors", "Leader Color…"))
    out.push(_c("editText", "Format", "", "Edit Text…", "Return"))
    out.push(_c("cell.free", "Format", "Table Cell", "Free Position"))
    out.push(_c("cell.independent", "Format", "Table Cell", "Independent of Table"))
    for (i = 0; i < _PLACE.length; i++)
        out.push(_c("cell.place." + _PLACE[i][0], "Format", "Table Cell", "Place " + _PLACE[i][1]))
    return _ordered(out)
}

// --- enabled -------------------------------------------------------------------

// A picture turned, flipped, cropped or skewed (rig_menu _pictureShaped).
function _pictureShaped(n) {
    return !!(n && ((n.rot || 0) % 360 || n.flipH || n.flipV || n.crop || n.skew))
}

function _canResetShape(ed, n) {
    if (_multi(ed) || !ed.transformModesFor(n).length)
        return false
    var shaped = ed.hasShaping(n) || (ed.isOverlay(n) && _pictureShaped(n))
    return shaped && !ed.isLocked(n)
}

function _hasChips(ed) {
    var ids = ed.selectedIds || []
    for (var i = 0; i < ids.length; i++) {
        if (!ed.isDraw(ed.nodeAt(ids[i])))
            return true
    }
    return false
}

// Fill, Outline and Text colours: chips and groups, or the drawings whose
// menu has that colour.
var _DRAW_COLOR_KINDS = {
    "color.fill": ["shape", "text", "closedPath"],
    "color.outline": ["shape", "text", "line", "path", "closedPath"],
    "color.text": ["text"]
}

function _drawColorKind(ed) {
    var k = _selKind(ed)
    if (k === "path") {
        // Every selected path closed: its Fill row shows.
        var ids = _ids(ed)
        var closed = ids.every(function(id) { var p = ed.nodeAt(id); return !!(p && p.closed) })
        return closed ? "closedPath" : "path"
    }
    return k
}

function enabled(ed, id) {
    if (!ed || !ed.interactive)
        return false
    if (id.indexOf("edit.") === 0)
        return _editEnabled(ed, id)
    var n = _node(ed)
    var k = _selKind(ed)
    if (id.indexOf("draw.") === 0 || id === "importPicture")
        return true
    if (id.indexOf("around.") === 0)
        return _hasChips(ed)
    if (id.indexOf("cell.") === 0)
        return _single(ed, ["table"]) && _tableTargetOk(ed)
    if (id.indexOf("align.") === 0)
        return ed.canAlign()
    if (id.indexOf("distribute.") === 0)
        return ed.canDistribute()
    if (id === "table.delete")
        return k === "table"
    if (id.indexOf("table.") === 0) {
        if (!_single(ed, ["table"]))
            return false
        if (id === "table.deleteRow")
            return !!(n.rows && n.rows.length > 1) && !_tableTargetStale(ed)
        if (id === "table.deleteCol")
            return n.cols > 1 && !_tableTargetStale(ed)
        if (id === "table.deleteCell")
            return ed.tableExtra >= 0 && _tableTargetOk(ed)
        return true
    }
    if (id === "callout.remove")
        return _single(ed, ["text"]) && ed.isCallout(n)
    if (id === "callout.detach")
        return _single(ed, ["text"]) && ed.isCallout(n) && !!(n.tail && n.tail.to)
    if (id.indexOf("ends.") === 0) {
        if (!_single(ed, ["chip", "group"]))
            return false
        if (id === "ends.deleteLeader")
            return ed.leaderList(n).length > 0
        return true
    }
    if (id.indexOf("color.") === 0) {
        if (id === "color.hot" || id === "color.hotPress" || id === "color.leader"
                || id === "color.hlFill" || id === "color.hlOutline" || id === "color.hlText")
            return _chipLike(ed)
        if (_chipLike(ed))
            return true
        return (_DRAW_COLOR_KINDS[id] || []).indexOf(_drawColorKind(ed)) >= 0
    }
    switch (id) {
    case "stopDrawing":
        return ed.drawTool.length > 0
    case "addCallout":
        return _single(ed, ["chip"])
    case "addLeader":
    case "addStraightSpine":
    case "addCurvedSpine":
        return _chipLike(ed)
    case "addPointer":
        return _single(ed, ["text"]) && !ed.isCallout(n)
    case "bringToFront":
    case "bringForward":
    case "sendBackward":
    case "sendToBack":
    case "hide":
    case "lock":
        return !!n
    case "moveToBackground":
        return !!n && ed.planeMoveItems(_arrangeIds(ed))[0].enabled
    case "moveToForeground":
        return !!n && ed.planeMoveItems(_arrangeIds(ed))[1].enabled
    case "flipH":
    case "flipV":
        return !_multi(ed) && ed.isFlippable(n)
    case "rotatePlus":
    case "rotateMinus":
        return (!_multi(ed) && ed.isRotatable(n)) || ed.canTurnTogether()
    case "resetShape":
        return !!n && _canResetShape(ed, n)
    case "editPoints":
        return !_multi(ed) && ed.transformModesFor(n).length > 0 && ed.canEditPoints(n) && !ed.isLocked(n)
    case "crop":
        return _single(ed, ["image"]) && !ed.isLocked(n)
    case "snap.add":
        return _single(ed, ["image"])
    case "snap.clear":
        return _single(ed, ["image"]) && !!(n.sockets && n.sockets.length)
    case "detachFromChips":
        return !!(n && n.around && n.around.length)
    case "resetCrop":
        return _single(ed, ["image"]) && !!n.crop && !ed.isLocked(n)
    case "resetPicture":
        return (ed.selectedIds || []).some(function(i) { return ed.canResetPicture(i) })
    case "group":
        return ed.canGroup()
    case "breakGroup":
        return ed.canUngroup() || ed.isGroup(n)
    case "editGroup":
        return !_multi(ed) && ed.isGroup(n)
    case "doneGroup":
        return ed.groupEditId !== ""
    case "unlockAll":
        return true
    case "rename":
        return _single(ed, ["chip", "group"])
    case "copyFormat":
        return k === "text"
    case "pasteFormat":
        return k === "text" && !!ed.textFormatClip
    case "clearFormatting":
        return k === "text"
    case "saveStyle":
        return k !== "group" && k !== "mixed" && ed.styleKindOf(n) !== ""
    case "editText":
        return _single(ed, ["text"])
    }
    return false
}

// The right-click menu's own reason (rig_menu.js planeMoveItems' tip), so the
// menu bar and the right-click menu say the same words.
function whyDisabled(ed, id) {
    if (!ed || !ed.interactive || enabled(ed, id))
        return ""
    if (id === "moveToBackground" || id === "moveToForeground") {
        if (!_node(ed))
            return ""
        var items = ed.planeMoveItems(_arrangeIds(ed))
        return String(items[id === "moveToBackground" ? 0 : 1].tip || "")
    }
    return ""
}

// As the window's Edit menu rows.
function _editEnabled(ed, id) {
    switch (id) {
    case "edit.cut":
    case "edit.copy":
    case "edit.duplicate":
    case "edit.delete":
        return !!ed.selectedId
    case "edit.paste":
        // Copied items, or a picture on the clipboard (as the right-click
        // menu's Paste).
        return !!((ed.copiedNodes && ed.copiedNodes.length) || ed.canPastePicture)
    case "edit.selectAll":
        return true
    }
    return false
}

// --- run -----------------------------------------------------------------------

// Rename, as the chip menu's: the group member being edited, else the chip.
function _rename(ed) {
    var n = _node(ed)
    if (!n)
        return
    var mem = ed.targetMember()
    var mi = -1
    if (mem && n.members) {
        for (var i = 0; i < n.members.length; i++) {
            if (n.members[i] === mem) {
                mi = i
                break
            }
        }
    }
    ed.beginRename(n.id, mi)
}

function _rotate(ed, sign) {
    var step = _rotateStep(ed) * sign
    var n = _node(ed)
    if (!_multi(ed) && ed.isRotatable(n)) {
        ed.setRotation(((n && n.rot) ? n.rot : 0) + step)
        return
    }
    if (ed.canTurnTogether())
        ed.turnSelectionBy(step)
}

// Every item on the edited plane that a band drag could take (not hidden,
// not locked), as the window's Edit > Select All.
function _selectAll(ed) {
    if (typeof ed.selectAll === "function") {
        ed.selectAll()
        return
    }
    var ids = []
    var nodes = ed.nodes || []
    for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i]
        if (!n || ed.isHidden(n) || ed.isLocked(n) || !ed.inEditPlane(n))
            continue
        if (ids.indexOf(n.id) < 0)
            ids.push(n.id)
        if (n.packId && ids.indexOf(n.packId) < 0)
            ids.push(n.packId)
    }
    ed.setSelection(ids)
}

function _edit(ed, id) {
    switch (id) {
    case "edit.cut":
        ed.cutSelection()
        break
    case "edit.copy":
        ed.copySelection()
        break
    case "edit.paste":
        ed.pasteClipboard()
        break
    case "edit.duplicate":
        ed.duplicateSelection()
        break
    case "edit.delete":
        ed.deleteSelected()
        break
    case "edit.selectAll":
        _selectAll(ed)
        break
    }
}

function _color(ed, id) {
    var chipField = {
        "color.fill": "color", "color.outline": "border", "color.text": "textColor",
        "color.hlFill": "hlColor", "color.hlOutline": "hlBorder", "color.hlText": "hlText",
        "color.hot": "hotColor", "color.hotPress": "hotPressColor", "color.leader": "leaderColor"
    }[id]
    if (_chipLike(ed)) {
        ed.pickColor(chipField)
        return
    }
    var drawField = { "color.fill": "color", "color.outline": "border", "color.text": "textColor" }[id]
    if (drawField)
        ed.requestDrawColor(drawField)
}

function _exec(ed, id) {
    var n = _node(ed)
    if (id.indexOf("edit.") === 0) {
        _edit(ed, id)
        return
    }
    if (id.indexOf("draw.") === 0) {
        ed.setDrawTool(id.substring(5))
        return
    }
    if (id.indexOf("around.") === 0) {
        ed.addDrawAround(id.substring(7))
        return
    }
    if (id.indexOf("cell.place.") === 0) {
        ed.placeTableCell(id.substring(11))
        return
    }
    if (id.indexOf("color.") === 0) {
        _color(ed, id)
        return
    }
    if (id.indexOf("align.") === 0) {
        ed.alignSelection(id.substring(6))
        return
    }
    if (id.indexOf("distribute.") === 0) {
        ed.distributeSelection(id.substring(11))
        return
    }
    switch (id) {
    case "stopDrawing":
        // What Esc on the map does (RigPointerArea): a rename ends, else
        // everything under way stops (the tool, a path draft, a drag).
        if (ed.renameId) {
            ed.cancelRename()
        } else {
            ed.cancelAllActions()
            ed.closeMenu()
        }
        break
    case "importPicture":
        ed.overlayImportRequested()
        break
    case "addCallout":
        ed.addCalloutFor(n.id)
        break
    case "addLeader":
        ed.addLeader()
        break
    case "addPointer":
        ed.addCalloutTail()
        break
    case "addStraightSpine":
        ed.ensureMidSpine(n)
        ed.bump()
        break
    case "addCurvedSpine":
        ed.addCurveSpine(n)
        break
    case "table.rowAbove":
        ed.addTableRow(false)
        break
    case "table.rowBelow":
        ed.addTableRow(true)
        break
    case "table.colLeft":
        ed.addTableCol(false)
        break
    case "table.colRight":
        ed.addTableCol(true)
        break
    case "table.spawnCell":
        ed.spawnEmptyCell()
        break
    case "table.deleteRow":
        ed.deleteTableRow()
        break
    case "table.deleteCol":
        ed.deleteTableCol()
        break
    case "table.deleteCell":
        ed.deleteThisTableCell()
        break
    case "table.idCol":
        ed.toggleTableIdCol()
        break
    case "table.delete":
        ed.deleteTable()
        break
    case "callout.detach":
        ed.detachCalloutTail()
        break
    case "callout.remove":
        ed.removeCalloutTail()
        break
    case "editPoints":
        ed.convertToPath()
        break
    case "crop":
        ed.toggleCrop()
        break
    case "snap.add":
        ed.beginPlantSnap()
        break
    case "snap.clear":
        ed.clearSockets()
        break
    case "detachFromChips":
        ed.detachFromChips()
        break
    case "bringToFront":
        ed.bringToFront()
        break
    case "bringForward":
        ed.bringForward()
        break
    case "sendBackward":
        ed.sendBack()
        break
    case "sendToBack":
        ed.sendToBack()
        break
    case "moveToBackground":
        ed.planeMoveItems(_arrangeIds(ed))[0].run()
        break
    case "moveToForeground":
        ed.planeMoveItems(_arrangeIds(ed))[1].run()
        break
    case "flipH":
        ed.flipSelection("h")
        break
    case "flipV":
        ed.flipSelection("v")
        break
    case "rotatePlus":
        _rotate(ed, 1)
        break
    case "rotateMinus":
        _rotate(ed, -1)
        break
    case "resetShape":
        ed.resetShape(ed.selectedId)
        break
    case "resetCrop":
        ed.resetCrop()
        break
    case "resetPicture":
        ed.resetPicture()
        break
    case "group":
        ed.groupSelection()
        break
    case "breakGroup":
        ed.ungroupSelection()
        break
    case "editGroup":
        ed.beginGroupEdit(ed.selectedId)
        break
    case "doneGroup":
        ed.endGroupEdit()
        break
    case "lock":
        if (_multi(ed))
            ed.toggleLockSelection()
        else
            ed.toggleLock(ed.selectedId)
        break
    case "unlockAll":
        ed.unlockAll()
        break
    case "hide":
        ed.setLayerFlags(_arrangeIds(ed).map(function(s) { return { id: s, part: "" } }), "hidden", true)
        break
    case "rename":
        _rename(ed)
        break
    case "ends.detachChip":
        ed.detachEnd("from")
        break
    case "ends.detachHot":
        ed.detachEnd("to")
        break
    case "ends.toChip":
        ed.attachEndToSelf("from")
        break
    case "ends.toHot":
        ed.attachEndToSelf("to")
        break
    case "ends.branch":
        ed.addBranch()
        break
    case "ends.clearSpines":
        ed.clearAllSpines(ed.selectedId)
        break
    case "ends.deleteLeader":
        ed.deleteLeader()
        break
    case "copyFormat":
        ed.copyTextFormat()
        break
    case "pasteFormat":
        // The text menu's Paint format: puts the copied format on the
        // selection and keeps painting.
        ed.applyTextFormat()
        ed.textPaintOn = true
        ed.bump()
        break
    case "clearFormatting":
        ed.clearTextFormat()
        break
    case "saveStyle":
        ed.saveStyleOf(n.id)
        break
    case "editText":
        ed.beginTextRename(n.id)
        break
    case "cell.free":
        ed.toggleTableCellFree()
        break
    case "cell.independent":
        var c = ed.tableCurrentCell(n)
        ed.setTableCellIndependent(!(c && c.independent))
        break
    }
}

function run(ed, id) {
    if (!enabled(ed, id))
        return
    _exec(ed, id)
    noteRun(ed, id)
}

// --- favourites and repeat (07 S136 S137) -----------------------------------------

// Not repeated: they change nothing (Undo, Redo and view commands have no id).
var NO_REPEAT = { "edit.copy": true, "edit.selectAll": true, "stopDrawing": true }

// info(id) or info(ed, id); ed gives the rotate step in the text.
function info(a, b) {
    var ed = typeof a === "string" ? b : a
    var id = typeof a === "string" ? a : b
    if (!id || id === "-")
        return null
    for (var i = 0; i < _EDIT.length; i++) {
        if (_EDIT[i][0] === id)
            return { id: id, text: _EDIT[i][1], key: _EDIT[i][2] }
    }
    var all = list(ed)
    for (var j = 0; j < all.length; j++) {
        if (all[j].id === id)
            return { id: id, text: all[j].text, key: all[j].key }
    }
    return null
}

function applies(ed, id) {
    return !!id && enabled(ed, id)
}

function noteRun(ed, id) {
    if (!ed || !id || NO_REPEAT[id] || !info(ed, id))
        return
    ed.lastCommandId = id
}

function repeatLabel(ed) {
    var c = ed ? info(ed, ed.lastCommandId || "") : null
    return c ? 'Repeat "' + c.text + '"' : ""
}

function canRepeat(ed) {
    return !!ed && !!ed.lastCommandId && !!info(ed, ed.lastCommandId) && enabled(ed, ed.lastCommandId)
}

function repeat(ed) {
    if (canRepeat(ed))
        run(ed, ed.lastCommandId)
}

// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// What the right-click menu offers for what was clicked.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
//
// menuModel() returns { kind, title, quick: [items], sections: [{ key, title,
// items }] }. An item is one of
//   { kind: "action", text, enabled, run() }            closes the menu
//   { kind: "toggle", text, checked, enabled, run() }    stays open
//   { kind: "choice", text, options: [{ text, value, checked }], enabled,
//     run(value) }                                       stays open
//   { kind: "number", text, value, min, max, suffix, enabled, run(value) }
//                                                        stays open
// The shared ContextMenu (Gremlin.Menus) draws it; only what applies to the
// target is listed. menuModel() adds Undo and Redo beside the title.

function _act(text, run, enabled, hint) {
    return { kind: "action", text: text, run: run, enabled: enabled === undefined ? true : !!enabled,
             hint: hint || "" }
}

// Copy and Paste, the same as Ctrl+C / Ctrl+V: Copy for what was clicked,
// Paste for copied items or a picture on the clipboard.
function _copyPaste(withCopy) {
    var out = []
    if (withCopy)
        out.push(_act("Copy", copySelection, true, "Ctrl+C"))
    out.push(_act("Paste", pasteClipboard, !!((clip && clip.length) || canPastePicture), "Ctrl+V"))
    return out
}

function _tog(text, checked, run, enabled) {
    return { kind: "toggle", text: text, checked: !!checked, run: run, enabled: enabled === undefined ? true : !!enabled }
}

// A row of values; isOn(value) says which is current.
function _pick(text, values, labels, isOn, run, enabled) {
    var options = []
    for (var i = 0; i < values.length; i++)
        options.push({ text: labels ? labels[i] : "" + values[i], value: values[i], checked: !!isOn(values[i]) })
    return { kind: "choice", text: text, options: options, run: run, enabled: enabled === undefined ? true : !!enabled }
}

// A value typed into a box and applied with Enter; the menu stays open.
function _num(text, value, min, max, suffix, run, enabled) {
    return { kind: "number", text: text, value: value, min: min, max: max, suffix: suffix || "",
             run: run, enabled: enabled === undefined ? true : !!enabled }
}

function _field(key, fallback) {
    return function(v) { return fieldEq(key, v, fallback) }
}

function _set(key) {
    return function(v) { applyField(key, v) }
}

function _setDraw(key) {
    return function(v) { applyDrawField(key, v) }
}

function _sect(key, title, items) {
    // Rows that do not apply here are passed as null and left out.
    return { key: key, title: title, items: (items || []).filter(function(i) { return !!i }) }
}

function _menuIds() {
    return (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
}

function _selectionHasChips() {
    var ids = selectedIds || []
    for (var i = 0; i < ids.length; i++) {
        if (!isDraw(nodeAt(ids[i])))
            return true
    }
    return false
}

// What the menu is about: chip, group, leader, shape, line, image, text,
// table, multi (several selected) or canvas.
function menuKind() {
    var n = _ctx.nodeId ? nodeAt(_ctx.nodeId) : null
    if (!n)
        return "canvas"
    var k = _ctx.kind || ""
    if ((selectedIds || []).length > 1 && isSelected(n.id))
        return "multi"
    if (k === "spine" || k === "line" || k === "from" || k === "to")
        return "leader"
    if (k === "hot" && !isGroup(n))
        return "hotspot"
    if (isTable(n))
        return "table"
    if (isText(n))
        return "text"
    if (isOverlay(n))
        return "image"
    if (isLine(n))
        return "line"
    if (isPath(n))
        return "path"
    if (isDraw(n))
        return "shape"
    if (isGroup(n))
        return "group"
    return "chip"
}

var _SHAPE_NAMES = {
    rect: "Rectangle", roundrect: "Rounded rectangle", ellipse: "Ellipse",
    triangle: "Triangle", diamond: "Diamond", arrow: "Arrow", arrow2: "Double arrow",
    line: "Line", path: "Path", text: "Text box", table: "Table", image: "Picture"
}

function _hasHead(style) {
    return style === "solid" || style === "hollow"
}

function menuTitle(kind) {
    var n = _ctx.nodeId ? nodeAt(_ctx.nodeId) : null
    if (kind === "canvas")
        return "Canvas"
    if (kind === "multi")
        return (selectedIds || []).length + " selected"
    if (!n)
        return ""
    if (isDraw(n)) {
        var a = _hasHead(n.headStart)
        var b = _hasHead(n.headEnd)
        if (isLine(n) && a !== b)
            return "Arrow"
        if (isLine(n) && a)
            return "Double-headed arrow"
        return _SHAPE_NAMES[n.shape || "rect"] || "Drawing"
    }
    var mem = targetMember()
    if (mem)
        return roleWord(fiveWayRole(mem)) || memberLabel(n, mem)
    var name = friendlyOf(n, mem) || n.id
    if (kind === "hotspot")
        return name + " · hotspot"
    return kind === "leader" ? name + " · leader" : name
}

// --- Hide and Lock (the Layers panel's eye and lock, from the menu) ------------

var _LAYER_WORDS = {
    chip: "Chip", group: "Group", shape: "Shape", line: "Line", path: "Path",
    image: "Picture", text: "Text Box", table: "Table", hotspot: "Hotspot", leader: "Leader"
}

// Hide and Lock for what was right-clicked: the item, its hotspot or the
// leader clicked; several selected items all at once. Unhide or unlock from
// the Layers panel (a hidden or locked item cannot be clicked on the map).
function _hideLock(kind) {
    var id = _ctx.nodeId
    if (!id || kind === "canvas")
        return []
    var targets = []
    if (kind === "multi") {
        targets = (selectedIds || []).map(function(s) { return { id: s, part: "" } })
    } else {
        var part = kind === "hotspot" ? "hot"
            : (kind === "leader" ? "leader:" + Math.max(0, _ctx.leader || 0) : "")
        targets = [{ id: id, part: part }]
    }
    var word = kind === "multi" ? "Selected" : (_LAYER_WORDS[kind] || "Item")
    function all(flag) {
        return targets.length > 0 && targets.every(function(t) { return layerFlag(t.id, t.part, flag) })
    }
    function flip(flag) {
        var on = !all(flag)
        return function() { setLayerFlags(targets, flag, on) }
    }
    return [_tog("Hide " + word, all("hidden"), flip("hidden")),
            _tog("Lock " + word, all("locked"), flip("locked"))]
}

// --- chips, groups and leaders -------------------------------------------

function _renameChip() {
    var n = nodeAt(selectedId)
    if (!n)
        return
    var mem = targetMember()
    var mi = -1
    if (mem && n.members) {
        for (var i = 0; i < n.members.length; i++) {
            if (n.members[i] === mem) {
                mi = i
                break
            }
        }
    }
    beginRename(n.id, mi)
}

function _chipStyle() {
    var n = nodeAt(selectedId)
    return _sect("style", "Chip Style", [
        _pick("Font Size", [8, 9, 10, 11, 12, 14, 16, 18, 20, 22], null, _field("fontSize", 10), _set("fontSize")),
        _pick("Size", [12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 42, 48], null, _field("chipSize", 18), _set("chipSize")),
        _pick("Shape", ["round", "square", "circle"], ["Round", "Square", "Circle"], _field("chipShape", "round"), _set("chipShape")),
        // A circle sizes itself to its label (Auto) unless a size is chosen.
        _field("chipShape", "round")("circle")
            ? _pick("Circle Size", [0, 20, 24, 28, 32, 36, 42, 48, 56, 64, 72],
                    ["Auto", "20", "24", "28", "32", "36", "42", "48", "56", "64", "72"],
                    _field("circleSize", 0), _set("circleSize"))
            : null,
        _pick("Fill", ["filled", "hollow"], ["Filled", "Hollow"], _field("chipFill", "filled"), _set("chipFill")),
        _tog("Highlight on press", !n || n.highlight !== false,
             function() { var c = nodeAt(selectedId); applyField("highlight", !(c && c.highlight !== false)) }),
        _act("Reset This Cell", resetMemberStyle, targetMember() !== null)
    ])
}

function _chipColours() {
    function pick(field) { return function() { pickColor(field) } }
    return _sect("colours", "Colors", [
        _act("Fill Color…", pick("color")),
        _act("Outline Color…", pick("border")),
        _act("Text Color…", pick("textColor")),
        _act("Pressed Fill…", pick("hlColor")),
        _act("Pressed Outline…", pick("hlBorder")),
        _act("Pressed Text…", pick("hlText"))
    ])
}

function _hotspot() {
    var n = nodeAt(selectedId)
    function flip(key, dflt) {
        return _tog(_HOT_TOGGLES[key], n ? (n[key] === undefined ? dflt : !!n[key]) : dflt, function() {
            var t = nodeAt(selectedId)
            var on = t ? (t[key] === undefined ? dflt : !!t[key]) : dflt
            applyField(key, !on)
        })
    }
    return _sect("hotspot", "Hotspot", [
        _hideHotspot(),
        _pick("Size", [4, 6, 8, 9, 10, 12, 14, 16, 20, 24, 28], null, _field("hotSize", 9), _set("hotSize")),
        _pick("Shape",
              ["round", "square", "diamond", "triangle", "ring", "target", "crosshair", "plus", "x", "pin", "none"],
              ["Round", "Square", "Diamond", "Triangle", "Ring", "Target", "Crosshair", "Plus", "X", "Pin", "None"],
              _field("hotShape", "round"), _set("hotShape")),
        _pick("Fill", ["filled", "hollow", "half"], ["Filled", "Hollow", "Half"], _field("hotFill", "filled"), _set("hotFill")),
        _pick("Line", ["thin", "medium", "thick"], ["Thin", "Medium", "Thick"], _field("hotLine", "medium"), _set("hotLine")),
        _pick("Opacity", [0.25, 0.5, 0.75, 1], ["25%", "50%", "75%", "100%"], _field("hotOpacity", 1), _set("hotOpacity")),
        flip("hotHalo", false),
        flip("hotNumber", false),
        flip("hotPress", false),
        flip("hotPulse", false),
        flip("hotLive", true),
        _act("Hotspot Color…", function() { pickColor("hotColor") }),
        _act("Pressed Color…", function() { pickColor("hotPressColor") })
    ])
}

// Hide Hotspot: the same switch as the hotspot's eye in the Layers panel
// (hotHidden); the shape and its settings stay, so showing it again brings
// the same hotspot back. With several chips selected, it hides them all, or
// shows them all when all are hidden.
function _hideHotspot() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
    var allHidden = ids.length > 0 && ids.every(function(id) { return layerFlag(id, "hot", "hidden") })
    return _tog("Hide Hotspot", allHidden, function() {
        setLayerFlags(ids.map(function(id) { return { id: id, part: "hot" } }), "hidden", !allHidden)
    }, ids.length > 0)
}

var _HOT_TOGGLES = {
    hotHalo: "Halo", hotNumber: "Number", hotPress: "Highlight on press",
    hotPulse: "Pulse on press", hotLive: "Show on live map"
}

function _leaderCount() {
    var ids = _menuIds()
    var count = 0
    for (var i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (n && !isDraw(n) && leaderList(n).length)
            count++
    }
    return count
}

function _deleteLeaderItem() {
    return _act((selectedIds || []).length > 1 ? "Delete leaders" : "Delete leader", deleteLeader, _leaderCount() > 0)
}

function _leader() {
    var n = nodeAt(selectedId)
    var widths = [8, 11, 15, 20, 25, 30, 40]
    var labels = widths.map(function(w) { return (w / 10).toFixed(1) })
    var seg = _ctx.seg
    var leader = _ctx.leader
    function setSeg(curved) {
        selectedLeader = leader
        selectedSeg = seg
        setSegCurve(currentLeader(nodeAt(selectedId)), Math.max(0, seg), curved)
    }
    return _sect("leader", "Leader", [
        _act("Leader Color…", function() { pickColor("leaderColor") }),
        _pick("Weight", widths, labels, function(w) { return Math.round(leaderWidthOf(n) * 10) === w },
              function(w) { applyField("leaderWidth", w / 10) }),
        _act("Add Straight Spine", function() { ensureMidSpine(nodeAt(selectedId)); bump() }),
        _act("Add Curved Spine", function() { addCurveSpine(nodeAt(selectedId)) }),
        _act("Convert Spine", convertSelectedSpine, ctxHasSelectedSpine()),
        _pick("This Segment", [true, false], ["Curved", "Straight"], function() { return false },
              function(v) { setSeg(v) }),
        _pick("All Segments", [true, false], ["Curved", "Straight"], function() { return false },
              function(v) { setAllSegCurve(v) }),
        _act("Add Leader", addLeader),
        _act("Branch from This End", function() { selectedLeader = leader; addBranch() }),
        _act("Clear All Spines", function() { clearAllSpines(selectedId) }, !!(n && !isDraw(n))),
        _act("Delete Spine", function() { selectedLeader = leader; deleteSelection() }, selectedSpine >= 0),
        _deleteLeaderItem()
    ])
}

function _leaderEnds() {
    return _sect("ends", "Leader Ends", [
        _act("Detach Chip End", function() { detachEnd("from") }),
        _act("Detach Hotspot End", function() { detachEnd("to") }),
        _act("Reconnect to This Chip", function() { attachEndToSelf("from") }),
        _act("Reconnect to This Hotspot", function() { attachEndToSelf("to") })
    ])
}

function _group() {
    var n = ctxTarget()
    return _sect("group", "Group", [
        _act("Group Selected", groupSelection, canGroup()),
        _act("Break Group", ungroupSelection, canUngroup() || isGroup(n)),
        _act("Edit Group", function() { beginGroupEdit(_ctx.nodeId) }, isGroup(n)),
        _act("Done Editing Group", endGroupEdit, groupEditId !== "")
    ])
}

function _format() {
    var n = ctxTarget()
    if (!isFiveWay(n) && !ctxHasTheme())
        return null
    return _sect("format", "Style", [
        // Named card is no longer offered (it becomes a dropped shape); maps
        // that already use it keep showing it, and Clear Format removes it.
        _pick("Format", ["plus", "mini", "radial"], ["Plus", "Mini hat", "Radial"],
              function(f) { return fiveWayFormat(ctxTarget()) === f }, applyFiveWayFormat, isFiveWay(n)),
        _act("Clear Format", clearGroupFormat, ctxHasGroupFormat())
    ])
}

function _align() {
    var n = ctxTarget()
    if (!isGroup(n))
        return null
    return _sect("align", "Align Members", [
        _pick("Align", ["left", "center", "right", "free"], ["Left", "Center", "Right", "Free"],
              function(a) { return groupAlignH(ctxTarget()) === a }, setAlignH)
    ])
}

var _AROUND = ["rect", "roundrect", "ellipse", "triangle", "diamond"]
var _AROUND_LABELS = ["Rectangle", "Rounded", "Ellipse", "Triangle", "Diamond"]

function _around() {
    if (!_selectionHasChips())
        return null
    return _sect("around", "Shape Around Selection", [
        _pick("Shape", _AROUND, _AROUND_LABELS, function() { return false }, addDrawAround)
    ])
}

// --- drawings --------------------------------------------------------------

var _SHAPES = ["rect", "roundrect", "ellipse", "triangle", "diamond", "arrow", "arrow2"]
var _SHAPE_LABELS = ["Rectangle", "Rounded", "Ellipse", "Triangle", "Diamond", "Arrow", "Double arrow"]

function _opacity(key, label) {
    return _pick(label || "Opacity", [0.25, 0.5, 0.75, 1], ["25%", "50%", "75%", "100%"], _field(key, 1), _set(key))
}

function _outline() {
    return _pick("Outline", ["", "dash", "dot"], ["Solid", "Dashed", "Dotted"], _field("dash", ""), _setDraw("dash"))
}

function _width() {
    return _pick("Width", [1, 2, 3, 4, 6], null, _field("stroke", 2), _setDraw("stroke"))
}

// Rotate and flip: an angle to type, quarter turns, 15 degree steps, and the
// two flips. A line only flips; it turns by dragging its ends.
function _rotate() {
    var n = nodeAt(selectedId)
    var items = []
    if (isRotatable(n)) {
        var rot = n && n.rot ? n.rot : 0
        var by = function(step) {
            return function() {
                var t = nodeAt(selectedId)
                setRotation(((t && t.rot) ? t.rot : 0) + step)
            }
        }
        items.push(_num("Angle", Math.round(rot * 10) / 10, 0, 360, "°", setRotation))
        items.push(_pick("Turn to", [0, 90, 180, 270], ["0°", "90°", "180°", "270°"],
                         function(v) { return Math.abs(rot - v) < 0.05 }, setRotation))
        var step = rotateSnap || 15
        items.push(_act("Rotate −" + step + "°", by(-step)))
        items.push(_act("Rotate +" + step + "°", by(step)))
    }
    if (isFlippable(n)) {
        items.push(_act("Flip Horizontally", function() { flipSelection("h") }))
        items.push(_act("Flip Vertically", function() { flipSelection("v") }))
    }
    if (!items.length)
        return null
    var title = isRotatable(n) ? (isFlippable(n) ? "Rotate and Flip" : "Rotate") : "Flip"
    return _sect("rotate", title, items)
}

// Transform: which handles the drawing shows, Edit points and Reset shape.
function _transform() {
    var n = nodeAt(selectedId)
    var modes = transformModesFor(n)
    if (!modes.length)
        return null
    var labels = modes.map(function(m) { return { resize: "Resize", shape: "Shape", tips: "Tips", skew: "Skew", bend: "Bend" }[m] })
    var items = [
        _pick("Handles", modes, labels, function(m) { return transformMode === m }, setTransformMode, !isLocked(n))
    ]
    if (canEditPoints(n))
        items.push(_act("Edit Points", convertToPath, !isLocked(n)))
    items.push(_act("Reset Shape", resetShape, hasShaping(n) && !isLocked(n)))
    return _sect("transform", "Transform", items)
}

// Locked items ignore clicks on the map; the Layers panel unlocks them.
// What Arrange's Lock and Hide act on: the whole selection when several
// items are selected, else the item.
function _arrangeIds() {
    var ids = selectedIds || []
    return ids.length > 1 && isSelected(selectedId) ? ids.slice() : [selectedId]
}

function _lockItem() {
    var n = nodeAt(selectedId)
    var ids = _arrangeIds()
    if (ids.length > 1) {
        var all = ids.every(function(s) { return isLocked(nodeAt(s)) })
        return _tog("Lock", all, toggleLockSelection, !!n)
    }
    return _tog("Lock", isLocked(n), function() { toggleLock(selectedId) }, !!n)
}

function _hideItems() {
    setLayerFlags(_arrangeIds().map(function(s) { return { id: s, part: "" } }), "hidden", true)
}

function _detachFromChips() {
    var g = drawGeom(nodeAt(selectedId))
    var n = nodeAt(selectedId)
    if (!n)
        return
    n.around = []
    n.fx = xToFx(g.x)
    n.fy = yToFy(g.y)
    n.fw = g.w / Math.max(1, spaceRect().w)
    n.fh = g.h / Math.max(1, spaceRect().h)
    bump()
}

function _arrange(extra) {
    var n = nodeAt(selectedId)
    var items = [
        _act("Bring to Front", bringToFront),
        _act("Bring Forward", bringForward),
        _act("Send Back", sendBack),
        _act("Send to Back", sendToBack),
        _lockItem(),
        _act("Hide", _hideItems)
    ]
    if (n && n.around && n.around.length)
        items.push(_act("Detach from Chips", _detachFromChips))
    return _sect("arrange", "Arrange", items.concat(extra || []))
}

function _shapeSections() {
    var n = nodeAt(selectedId)
    var style = [
        _pick("Fill", ["filled", "hollow"], ["Filled", "Hollow"], _field("fill", "hollow"), _set("fill")),
        _act("Fill Color…", function() { requestDrawColor("color") }),
        _act("Outline Color…", function() { requestDrawColor("border") }),
        _width(),
        _outline(),
        _opacity("opacity")
    ]
    if (n && n.around && n.around.length)
        style.push(_pick("Padding", [4, 8, 12, 16, 24, 32], null, _field("pad", 8), _set("pad")))
    return [
        _sect("shape", "Shape", [
            _pick("Shape", _SHAPES, _SHAPE_LABELS, _field("shape", "rect"), _set("shape"))
        ]),
        _sect("style", "Fill and Outline", style),
        _transform(),
        _rotate(),
        _arrange()
    ]
}

function _lineSections() {
    var heads = ["none", "solid", "hollow"]
    var headLabels = ["None", "Solid", "Hollow"]
    return [
        _sect("heads", "Arrowheads", [
            _pick("Start", heads, headLabels, _field("headStart", "none"), _setDraw("headStart")),
            _pick("End", heads, headLabels, _field("headEnd", "none"), _setDraw("headEnd")),
            _act("Swap Heads", swapLineHeads)
        ]),
        _sect("style", "Line", [
            _act("Color…", function() { requestDrawColor("border") }),
            _width(),
            _outline(),
            _opacity("opacity")
        ]),
        _rotate(),
        _arrange()
    ]
}

function _pathSections() {
    var n = nodeAt(selectedId)
    var heads = ["none", "solid", "hollow"]
    var headLabels = ["None", "Solid", "Hollow"]
    var closed = !!(n && n.closed)
    var out = [
        _sect("path", "Path", [
            _tog("Closed", closed, togglePathClosed, !!(n && (n.pts || []).length >= 3)),
            _tog("Smooth", !!(n && n.smooth), togglePathSmooth)
        ]),
        _sect("style", "Line", [
            _act("Color…", function() { requestDrawColor("border") }),
            _width(),
            _outline(),
            _opacity("opacity")
        ])
    ]
    if (closed) {
        out.push(_sect("fill", "Fill", [
            _pick("Fill", ["filled", "hollow"], ["Filled", "Hollow"], _field("fill", "hollow"), _set("fill")),
            _act("Fill Color…", function() { requestDrawColor("color") })
        ]))
    } else {
        out.push(_sect("heads", "Arrowheads", [
            _pick("Start", heads, headLabels, _field("headStart", "none"), _setDraw("headStart")),
            _pick("End", heads, headLabels, _field("headEnd", "none"), _setDraw("headEnd"))
        ]))
    }
    out.push(_rotate())
    out.push(_arrange())
    return out
}

function _imageSections() {
    var n = nodeAt(selectedId)
    return [
        _sect("image", "Picture", [
            _tog("Crop", cropId === selectedId, toggleCrop, !isLocked(n)),
            _act("Reset Crop", resetCrop, !!(n && n.crop) && !isLocked(n)),
            _act(plantSnap ? "Click the picture to place a snap point…" : "Add snap point", beginPlantSnap),
            _act("Clear Snap Points", clearSockets, !!(n && n.sockets && n.sockets.length)),
            _opacity("opacity")
        ]),
        _transform(),
        _rotate(),
        _arrange()
    ]
}

function _textSections() {
    var n = nodeAt(selectedId)
    var sizes = [[72, 20], [96, 24], [128, 32], [176, 40], [240, 48], [280, 28]]
    var sizeLabels = ["Caption", "Small", "Medium", "Large", "Title", "Wide"]
    var themes = ["gremlin", "hollow", "sheet"]
    var themeLabels = ["Dark", "Hollow", "Sheet"]
    var opac = [0, 0.25, 0.5, 0.75, 1]
    var opacLabels = ["0%", "25%", "50%", "75%", "100%"]
    return [
        _sect("text", "Text", [
            _pick("Font", [8, 10, 12, 14, 16, 18, 24], null,
                  function(v) { var t = nodeAt(selectedId); return t && t.fontSize ? t.fontSize === v : v === 12 },
                  _set("fontSize")),
            _tog("Bold", !!(n && n.bold), function() { var t = nodeAt(selectedId); applyField("bold", !(t && t.bold)) }),
            _tog("Word wrap", !n || n.wrap !== false,
                 function() { var t = nodeAt(selectedId); applyField("wrap", !(t && t.wrap !== false)) }),
            _tog("Scale font with box", !!(n && n.scaleFont),
                 function() { var t = nodeAt(selectedId); applyField("scaleFont", !(t && t.scaleFont)) }),
            _pick("Across", ["left", "center", "right"], ["Left", "Center", "Right"], _field("align", "center"), _set("align")),
            _pick("Down", ["top", "middle", "bottom"], ["Top", "Middle", "Bottom"], _field("valign", "middle"), _set("valign"))
        ]),
        _sect("box", "Box", [
            _pick("Size", [0, 1, 2, 3, 4, 5], sizeLabels,
                  function(i) { return textBoxSizeEq(sizes[i][0], sizes[i][1]) },
                  function(i) { applyTextBoxSize(sizes[i][0], sizes[i][1]) }),
            _pick("Theme", themes, themeLabels,
                  function(t) { var b = nodeAt(selectedId); return (b && b.theme ? b.theme : "gremlin") === t },
                  applyTextTheme),
            _act("Text Color…", function() { requestDrawColor("textColor") }),
            _act("Fill Color…", function() { requestDrawColor("color") }),
            _act("Outline Color…", function() { requestDrawColor("border") }),
            _pick("Fill Opacity", opac, opacLabels, _field("fillOpacity", 1), _set("fillOpacity")),
            _pick("Outline Opacity", opac, opacLabels, _field("borderOpacity", 1), _set("borderOpacity"))
        ]),
        _sect("format", "Copy and Paint Format", [
            _act("Copy Format", copyTextFormat),
            _tog("Paint format", textPaintOn, function() {
                if (!textFormatClip)
                    return
                applyTextFormat()
                textPaintOn = true
                bump()
            }, !!textFormatClip),
            _act("Clear Formatting", clearTextFormat),
            _act("Copy Text", copyTextPlain)
        ]),
        _sect("pointer", "Pointer", isCallout(n) ? [
            _act("Detach from Chip", detachCalloutTail, !!(n.tail && n.tail.to)),
            _act("Remove Pointer", removeCalloutTail)
        ] : [
            _act("Add Pointer", addCalloutTail)
        ]),
        _transform(),
        _rotate(),
        _arrange()
    ]
}

function _tableSections() {
    var n = nodeAt(selectedId)
    var cell = tableCurrentCell(n)
    var hasCell = tableHasTarget()
    return [
        _sect("rows", "Rows and Columns", [
            _act("Insert Row Above", function() { addTableRow(false) }),
            _act("Delete This Row", deleteTableRow, !!(n && n.rows && n.rows.length > 1)),
            _act("Insert Column Left", function() { addTableCol(false) }),
            _act("Delete This Column", deleteTableCol, !!(n && n.cols > 1)),
            _tog("ID column", !!(n && n.idCol), toggleTableIdCol)
        ]),
        _sect("cell", "Cell", [
            _tog("Free position", !!(cell && cell.free), toggleTableCellFree, hasCell),
            _tog("Independent of table", !!(cell && cell.independent),
                 function() { var c = tableCurrentCell(nodeAt(selectedId)); setTableCellIndependent(!(c && c.independent)) },
                 hasCell),
            _act("Spawn Empty Cell", spawnEmptyCell),
            _act("Delete This Cell", deleteThisTableCell, tableExtra >= 0),
            _pick("Place Across", ["left", "center", "right"], ["Far left", "Center", "Far right"],
                  function() { return false }, placeTableCell, hasCell),
            _pick("Place Down", ["top", "middle", "bottom"], ["Top", "Middle", "Bottom"],
                  function() { return false }, placeTableCell, hasCell)
        ]),
        _sect("look", "Look", [
            _pick("Theme", ["gremlin", "hollow", "sheet"], ["Dark", "Hollow", "Sheet"],
                  function(t) { return (n && n.theme ? n.theme : "gremlin") === t }, setTableTheme),
            _pick("Font Size", [8, 10, 12, 14, 16], null,
                  function(v) { return n && n.fontSize ? n.fontSize === v : v === 10 }, setTableFont)
        ]),
        _arrange([
            _act("Break Group", ungroupSelection, canUngroup()),
            _act("Delete Table", deleteTable)
        ])
    ]
}

// --- canvas ------------------------------------------------------------------

function _canvasSections() {
    var tools = ["rect", "roundrect", "ellipse", "triangle", "diamond", "arrow", "arrow2"]
    var draw = [
        _pick("Shape", tools, _SHAPE_LABELS, function(t) { return drawTool === t }, setDrawTool),
        _pick("Line", ["line", "arrowline", "path", "pen"], ["Line", "Arrow", "Path", "Freehand"], function(t) { return drawTool === t }, setDrawTool),
        _pick("Box", ["text", "callout", "table"], ["Text box", "Callout", "Table"], function(t) { return drawTool === t }, setDrawTool),
        _act("Import Picture…", function() { overlayImportRequested() }),
        _act("Paste Picture", function() { pastePictureRequested() }, canPastePicture),
        _act("Stop Drawing", function() { drawTool = "" }, drawTool.length > 0)
    ]
    var out = [_sect("draw", "Draw", draw)]
    var around = _around()
    if (around)
        out.push(around)
    if (canGroup())
        out.push(_group())
    return out
}

// Lining up several items; the menu stays open to try another.
function _alignSection() {
    var none = function() { return false }
    return _sect("align-many", "Align and Distribute", [
        _pick("Across", ["left", "center", "right"], ["Left", "Center", "Right"], none, alignSelection, canAlign()),
        _pick("Down", ["top", "middle", "bottom"], ["Top", "Middle", "Bottom"], none, alignSelection, canAlign()),
        _pick("Space Out", ["h", "v"], ["Across", "Down"], none, distributeSelection, canDistribute())
    ])
}

// Several items turned together about the middle of the selection.
function _turnSection() {
    if (!canTurnTogether())
        return null
    var step = rotateSnap || 15
    var none = function() { return false }
    return _sect("turn-many", (selectedIds || []).length === 1 ? "Turn group" : "Turn together", [
        _pick("Turn by", [-step, step, -90, 90, 180],
              ["−" + step + "°", "+" + step + "°", "−90°", "+90°", "180°"], none, turnSelectionBy)
    ])
}

// Saved looks for this kind of item, and saving this one's.
function _savedStyles() {
    var n = nodeAt(_ctx.nodeId || selectedId)
    var kind = styleKindOf(n)
    if (!kind)
        return null
    var id = n.id
    var items = [_act("Save This Style…", function() { saveStyleOf(id) })]
    var list = stylesFor(kind)
    for (var i = 0; i < list.length && i < 12; i++) {
        (function(style) {
            items.push(_act("Apply " + style.name, function() { applySavedStyle(style) }))
        })(list[i])
    }
    return _sect("saved-styles", "Saved Styles", items)
}

// --- the menu ----------------------------------------------------------------

function _compact(list) {
    return list.filter(function(s) { return !!s })
}

function menuModel() {
    var kind = menuKind()
    var quick = []
    var sections = []
    if (kind === "chip") {
        quick = [_act("Rename", _renameChip), _act("Add Callout", function() { addCalloutFor(_ctx.nodeId) }), _act("Delete Chip", deleteChip)]
        sections = [_chipStyle(), _chipColours(), _savedStyles(), _hotspot(), _leader(), _leaderEnds(), _group(), _format(), _around(), _arrange()]
    } else if (kind === "group") {
        quick = groupEditId !== ""
            ? [_act("Done Editing Group", endGroupEdit), _act("Break Group", ungroupSelection)]
            : [_act("Edit Group", function() { beginGroupEdit(_ctx.nodeId) }), _act("Break Group", ungroupSelection)]
        sections = [_format(), _align(), _turnSection(), _chipStyle(), _chipColours(), _hotspot(), _leader(), _leaderEnds(), _around(), _arrange()]
    } else if (kind === "hotspot") {
        quick = []
        sections = [_hotspot()]
    } else if (kind === "leader") {
        quick = [_act("Add Leader", addLeader), _deleteLeaderItem()]
        if (selectedSpine >= 0)
            quick.unshift(_act("Delete Spine", function() { selectedLeader = _ctx.leader; deleteSelection() }))
        sections = [_leader(), _leaderEnds(), _chipStyle(), _chipColours(), _hotspot()]
    } else if (kind === "shape" || kind === "line" || kind === "image" || kind === "path") {
        quick = [_act("Duplicate", duplicateSelection), _act("Delete", deleteChip)]
        sections = kind === "shape" ? _shapeSections()
            : (kind === "line" ? _lineSections() : (kind === "path" ? _pathSections() : _imageSections()))
        if (kind !== "image")
            sections.splice(sections.length - 2, 0, _savedStyles())
    } else if (kind === "text") {
        quick = [
            _act("Edit Text…", function() { var t = nodeAt(selectedId); if (isText(t)) beginTextRename(t.id) }),
            _act("Duplicate", duplicateSelection),
            _act("Delete Text Box", deleteChip)
        ]
        sections = _textSections()
        sections.splice(sections.length - 2, 0, _savedStyles())
    } else if (kind === "table") {
        quick = [_act("Add Row Below", function() { addTableRow(true) }), _act("Add Column Right", function() { addTableCol(true) })]
        sections = _tableSections()
    } else if (kind === "multi") {
        quick = [_act("Group Selected", groupSelection, canGroup()), _act("Duplicate", duplicateSelection), _act("Delete", function() { deleteSelected() })]
        var first = nodeAt(_ctx.nodeId)
        sections = [_alignSection(), _turnSection(), _savedStyles()].concat(isDraw(first) ? (isLine(first) ? _lineSections() : _shapeSections())
                                 : [_chipStyle(), _chipColours(), _hotspot(), _leader(), _around()])
    } else {
        quick = quick.concat(_copyPaste(false))
        if (drawTool.length)
            quick.push(_act("Stop Drawing", function() { drawTool = "" }))
        sections = _canvasSections()
    }
    // Copy and Paste on everything that can be copied (a leader or hotspot
    // belongs to its chip: copy the chip).
    if (kind !== "canvas" && kind !== "leader" && kind !== "hotspot" && kind !== "")
        quick = quick.concat(_copyPaste(true))
    quick = quick.concat(_hideLock(kind))
    return {
        kind: kind, title: menuTitle(kind), quick: quick, sections: _compact(sections),
        // Beside the title.
        header: [
            { label: "Undo", enabled: canUndo, run: undo },
            { label: "Redo", enabled: canRedo, run: redo }
        ]
    }
}

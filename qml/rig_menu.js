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
// RigContextMenu.qml draws it; only what applies to the target is listed.

function _act(text, run, enabled) {
    return { kind: "action", text: text, run: run, enabled: enabled === undefined ? true : !!enabled }
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
    return { key: key, title: title, items: items }
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
    if (isTable(n))
        return "table"
    if (isText(n))
        return "text"
    if (isOverlay(n))
        return "image"
    if (isLine(n))
        return "line"
    if (isDraw(n))
        return "shape"
    if (isGroup(n))
        return "group"
    return "chip"
}

var _SHAPE_NAMES = {
    rect: "Rectangle", roundrect: "Rounded rectangle", ellipse: "Ellipse",
    triangle: "Triangle", diamond: "Diamond", arrow: "Arrow", arrow2: "Double arrow",
    line: "Line", text: "Text box", table: "Table", image: "Picture"
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
    return kind === "leader" ? name + " · leader" : name
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
    return _sect("style", "Chip style", [
        _pick("Font size", [8, 9, 10, 11, 12, 14, 16, 18, 20, 22], null, _field("fontSize", 10), _set("fontSize")),
        _pick("Size", [12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 42, 48], null, _field("chipSize", 18), _set("chipSize")),
        _pick("Shape", ["round", "square"], ["Round", "Square"], _field("chipShape", "round"), _set("chipShape")),
        _pick("Fill", ["filled", "hollow"], ["Filled", "Hollow"], _field("chipFill", "filled"), _set("chipFill")),
        _tog("Highlight on press", !n || n.highlight !== false,
             function() { var c = nodeAt(selectedId); applyField("highlight", !(c && c.highlight !== false)) }),
        _act("Reset this cell", resetMemberStyle, targetMember() !== null)
    ])
}

function _chipColours() {
    function pick(field) { return function() { pickColor(field) } }
    return _sect("colours", "Colours", [
        _act("Fill colour…", pick("color")),
        _act("Outline colour…", pick("border")),
        _act("Text colour…", pick("textColor")),
        _act("Pressed fill…", pick("hlColor")),
        _act("Pressed outline…", pick("hlBorder")),
        _act("Pressed text…", pick("hlText"))
    ])
}

function _hotspot() {
    return _sect("hotspot", "Hotspot", [
        _pick("Size", [4, 6, 8, 9, 10, 12, 14, 16, 20, 24, 28], null, _field("hotSize", 9), _set("hotSize")),
        _pick("Shape", ["round", "square"], ["Round", "Square"], _field("hotShape", "round"), _set("hotShape")),
        _pick("Fill", ["filled", "hollow"], ["Filled", "Hollow"], _field("hotFill", "filled"), _set("hotFill")),
        _act("Hotspot colour…", function() { pickColor("hotColor") })
    ])
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
        _act("Leader colour…", function() { pickColor("leaderColor") }),
        _pick("Weight", widths, labels, function(w) { return Math.round(leaderWidthOf(n) * 10) === w },
              function(w) { applyField("leaderWidth", w / 10) }),
        _act("Add straight spine", function() { ensureMidSpine(nodeAt(selectedId)); bump() }),
        _act("Add curved spine", function() { addCurveSpine(nodeAt(selectedId)) }),
        _act("Convert spine", convertSelectedSpine, ctxHasSelectedSpine()),
        _pick("This segment", [true, false], ["Curved", "Straight"], function() { return false },
              function(v) { setSeg(v) }),
        _pick("All segments", [true, false], ["Curved", "Straight"], function() { return false },
              function(v) { setAllSegCurve(v) }),
        _act("Add leader", addLeader),
        _act("Branch from this end", function() { selectedLeader = leader; addBranch() }),
        _act("Clear all spines", function() { clearAllSpines(selectedId) }, !!(n && !isDraw(n))),
        _act("Delete spine", function() { selectedLeader = leader; deleteSelection() }, selectedSpine >= 0),
        _deleteLeaderItem()
    ])
}

function _leaderEnds() {
    return _sect("ends", "Leader ends", [
        _act("Detach chip end", function() { detachEnd("from") }),
        _act("Detach hotspot end", function() { detachEnd("to") }),
        _act("Reconnect to this chip", function() { attachEndToSelf("from") }),
        _act("Reconnect to this hotspot", function() { attachEndToSelf("to") })
    ])
}

function _group() {
    var n = ctxTarget()
    return _sect("group", "Group", [
        _act("Group selected", groupSelection, canGroup()),
        _act("Break group", ungroupSelection, canUngroup() || isGroup(n)),
        _act("Edit group", function() { beginGroupEdit(_ctx.nodeId) }, isGroup(n)),
        _act("Done editing group", endGroupEdit, groupEditId !== "")
    ])
}

function _format() {
    var n = ctxTarget()
    if (!isFiveWay(n) && !ctxHasTheme())
        return null
    return _sect("format", "5-way format", [
        _pick("Style", ["plus", "mini", "card", "radial"], ["Plus", "Mini hat", "Named card", "Radial"],
              function(f) { return fiveWayFormat(ctxTarget()) === f }, applyFiveWayFormat, isFiveWay(n)),
        _act("Clear format", clearGroupFormat, ctxHasGroupFormat())
    ])
}

function _align() {
    var n = ctxTarget()
    if (!isGroup(n))
        return null
    return _sect("align", "Align members", [
        _pick("Align", ["left", "center", "right", "free"], ["Left", "Centre", "Right", "Free"],
              function(a) { return groupAlignH(ctxTarget()) === a }, setAlignH)
    ])
}

var _AROUND = ["rect", "roundrect", "ellipse", "triangle", "diamond"]
var _AROUND_LABELS = ["Rectangle", "Rounded", "Ellipse", "Triangle", "Diamond"]

function _around() {
    if (!_selectionHasChips())
        return null
    return _sect("around", "Shape around selection", [
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
        items.push(_act("Flip horizontally", function() { flipSelection("h") }))
        items.push(_act("Flip vertically", function() { flipSelection("v") }))
    }
    if (!items.length)
        return null
    var title = isRotatable(n) ? (isFlippable(n) ? "Rotate and flip" : "Rotate") : "Flip"
    return _sect("rotate", title, items)
}

// Locked items ignore clicks on the map; the Layers panel unlocks them.
function _lockItem() {
    var n = nodeAt(selectedId)
    return _tog("Lock", isLocked(n), function() { toggleLock(selectedId) }, !!n)
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
        _act("Bring to front", bringToFront),
        _act("Bring forward", bringForward),
        _act("Send back", sendBack),
        _act("Send to back", sendToBack),
        _lockItem(),
        _act("Hide", function() { setLayerFlag(selectedId, "", "hidden", true) })
    ]
    if (n && n.around && n.around.length)
        items.push(_act("Detach from chips", _detachFromChips))
    return _sect("arrange", "Arrange", items.concat(extra || []))
}

function _shapeSections() {
    var n = nodeAt(selectedId)
    var style = [
        _pick("Fill", ["filled", "hollow"], ["Filled", "Hollow"], _field("fill", "hollow"), _set("fill")),
        _act("Fill colour…", function() { requestDrawColor("color") }),
        _act("Outline colour…", function() { requestDrawColor("border") }),
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
        _sect("style", "Fill and outline", style),
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
            _act("Swap heads", swapLineHeads)
        ]),
        _sect("style", "Line", [
            _act("Colour…", function() { requestDrawColor("border") }),
            _width(),
            _outline(),
            _opacity("opacity")
        ]),
        _rotate(),
        _arrange()
    ]
}

function _imageSections() {
    var n = nodeAt(selectedId)
    return [
        _sect("image", "Picture", [
            _tog("Crop", cropId === selectedId, toggleCrop, !isLocked(n)),
            _act("Reset crop", resetCrop, !!(n && n.crop) && !isLocked(n)),
            _act(plantSnap ? "Click the picture to place a snap point…" : "Add snap point", beginPlantSnap),
            _act("Clear snap points", clearSockets, !!(n && n.sockets && n.sockets.length)),
            _opacity("opacity")
        ]),
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
            _pick("Across", ["left", "center", "right"], ["Left", "Centre", "Right"], _field("align", "center"), _set("align")),
            _pick("Down", ["top", "middle", "bottom"], ["Top", "Middle", "Bottom"], _field("valign", "middle"), _set("valign"))
        ]),
        _sect("box", "Box", [
            _pick("Size", [0, 1, 2, 3, 4, 5], sizeLabels,
                  function(i) { return textBoxSizeEq(sizes[i][0], sizes[i][1]) },
                  function(i) { applyTextBoxSize(sizes[i][0], sizes[i][1]) }),
            _pick("Theme", themes, themeLabels,
                  function(t) { var b = nodeAt(selectedId); return (b && b.theme ? b.theme : "gremlin") === t },
                  applyTextTheme),
            _act("Text colour…", function() { requestDrawColor("textColor") }),
            _act("Fill colour…", function() { requestDrawColor("color") }),
            _act("Outline colour…", function() { requestDrawColor("border") }),
            _pick("Fill opacity", opac, opacLabels, _field("fillOpacity", 1), _set("fillOpacity")),
            _pick("Outline opacity", opac, opacLabels, _field("borderOpacity", 1), _set("borderOpacity"))
        ]),
        _sect("format", "Copy and paint format", [
            _act("Copy format", copyTextFormat),
            _tog("Paint format", textPaintOn, function() {
                if (!textFormatClip)
                    return
                applyTextFormat()
                textPaintOn = true
                bump()
            }, !!textFormatClip),
            _act("Clear formatting", clearTextFormat),
            _act("Copy text", copyTextPlain)
        ]),
        _rotate(),
        _arrange()
    ]
}

function _tableSections() {
    var n = nodeAt(selectedId)
    var cell = tableCurrentCell(n)
    var hasCell = tableHasTarget()
    return [
        _sect("rows", "Rows and columns", [
            _act("Insert row above", function() { addTableRow(false) }),
            _act("Delete this row", deleteTableRow, !!(n && n.rows && n.rows.length > 1)),
            _act("Insert column left", function() { addTableCol(false) }),
            _act("Delete this column", deleteTableCol, !!(n && n.cols > 1)),
            _tog("ID column", !!(n && n.idCol), toggleTableIdCol)
        ]),
        _sect("cell", "Cell", [
            _tog("Free position", !!(cell && cell.free), toggleTableCellFree, hasCell),
            _tog("Independent of table", !!(cell && cell.independent),
                 function() { var c = tableCurrentCell(nodeAt(selectedId)); setTableCellIndependent(!(c && c.independent)) },
                 hasCell),
            _act("Spawn empty cell", spawnEmptyCell),
            _act("Delete this cell", deleteThisTableCell, tableExtra >= 0),
            _pick("Place across", ["left", "center", "right"], ["Far left", "Centre", "Far right"],
                  function() { return false }, placeTableCell, hasCell),
            _pick("Place down", ["top", "middle", "bottom"], ["Top", "Middle", "Bottom"],
                  function() { return false }, placeTableCell, hasCell)
        ]),
        _sect("look", "Look", [
            _pick("Theme", ["gremlin", "hollow", "sheet"], ["Dark", "Hollow", "Sheet"],
                  function(t) { return (n && n.theme ? n.theme : "gremlin") === t }, setTableTheme),
            _pick("Font size", [8, 10, 12, 14, 16], null,
                  function(v) { return n && n.fontSize ? n.fontSize === v : v === 10 }, setTableFont)
        ]),
        _arrange([
            _act("Break group", ungroupSelection, canUngroup()),
            _act("Delete table", deleteTable)
        ])
    ]
}

// --- canvas ------------------------------------------------------------------

function _canvasSections() {
    var tools = ["rect", "roundrect", "ellipse", "triangle", "diamond", "arrow", "arrow2"]
    var draw = [
        _pick("Shape", tools, _SHAPE_LABELS, function(t) { return drawTool === t }, setDrawTool),
        _pick("Line", ["line", "arrowline"], ["Line", "Arrow"], function(t) { return drawTool === t }, setDrawTool),
        _pick("Box", ["text", "table"], ["Text box", "Table"], function(t) { return drawTool === t }, setDrawTool),
        _act("Import picture…", function() { overlayImportRequested() }),
        _act("Paste picture", function() { pastePictureRequested() }, canPastePicture),
        _act("Stop drawing", function() { drawTool = "" }, drawTool.length > 0)
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
    return _sect("align-many", "Align and distribute", [
        _pick("Across", ["left", "center", "right"], ["Left", "Centre", "Right"], none, alignSelection, canAlign()),
        _pick("Down", ["top", "middle", "bottom"], ["Top", "Middle", "Bottom"], none, alignSelection, canAlign()),
        _pick("Space out", ["h", "v"], ["Across", "Down"], none, distributeSelection, canDistribute())
    ])
}

// Several items turned together about the middle of the selection.
function _turnSection() {
    if (!canTurnTogether())
        return null
    var step = rotateSnap || 15
    var none = function() { return false }
    return _sect("turn-many", "Turn together", [
        _pick("Turn by", [-step, step, -90, 90, 180],
              ["−" + step + "°", "+" + step + "°", "−90°", "+90°", "180°"], none, turnSelectionBy)
    ])
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
        quick = [_act("Rename", _renameChip), _act("Delete chip", deleteChip)]
        sections = [_chipStyle(), _chipColours(), _hotspot(), _leader(), _leaderEnds(), _group(), _format(), _around(), _arrange()]
    } else if (kind === "group") {
        quick = groupEditId !== ""
            ? [_act("Done editing group", endGroupEdit), _act("Break group", ungroupSelection)]
            : [_act("Edit group", function() { beginGroupEdit(_ctx.nodeId) }), _act("Break group", ungroupSelection)]
        sections = [_format(), _align(), _chipStyle(), _chipColours(), _hotspot(), _leader(), _leaderEnds(), _around(), _arrange()]
    } else if (kind === "leader") {
        quick = [_act("Add leader", addLeader), _deleteLeaderItem()]
        if (selectedSpine >= 0)
            quick.unshift(_act("Delete spine", function() { selectedLeader = _ctx.leader; deleteSelection() }))
        sections = [_leader(), _leaderEnds(), _chipStyle(), _chipColours(), _hotspot()]
    } else if (kind === "shape" || kind === "line" || kind === "image") {
        quick = [_act("Duplicate", duplicateSelection), _act("Delete", deleteChip)]
        sections = kind === "shape" ? _shapeSections() : (kind === "line" ? _lineSections() : _imageSections())
    } else if (kind === "text") {
        quick = [
            _act("Edit text…", function() { var t = nodeAt(selectedId); if (isText(t)) beginTextRename(t.id) }),
            _act("Duplicate", duplicateSelection),
            _act("Delete text box", deleteChip)
        ]
        sections = _textSections()
    } else if (kind === "table") {
        quick = [_act("Add row below", function() { addTableRow(true) }), _act("Add column right", function() { addTableCol(true) })]
        sections = _tableSections()
    } else if (kind === "multi") {
        quick = [_act("Group selected", groupSelection, canGroup()), _act("Duplicate", duplicateSelection), _act("Delete", deleteChip)]
        var first = nodeAt(_ctx.nodeId)
        sections = [_alignSection(), _turnSection()].concat(isDraw(first) ? (isLine(first) ? _lineSections() : _shapeSections())
                                 : [_chipStyle(), _chipColours(), _hotspot(), _leader(), _around()])
    } else {
        if (clip && clip.length)
            quick.push(_act("Paste", pasteClipboard))
        if (drawTool.length)
            quick.push(_act("Stop drawing", function() { drawTool = "" }))
        sections = _canvasSections()
    }
    return { kind: kind, title: menuTitle(kind), quick: quick, sections: _compact(sections) }
}

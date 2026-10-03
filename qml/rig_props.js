// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The Properties panel: the selected item's exact position, size, angle and
// style, and setting them.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.
//
// propsModel() returns { title, locked, fields: [...] }; a field is
//   { key, label, kind: "number", value, min, max, step, suffix }
//   { key, label, kind: "choice", options: [{ text, value }], value }
//   { key, label, kind: "colour", value }              opens the colour picker
// setProp(key, value) applies one. Positions and sizes are percent of the page.


function _pct(v) {
    return Math.round((Number(v) || 0) * 10000) / 100
}

function _numField(key, label, value, min, max, suffix, step) {
    return { key: key, label: label, kind: "number", value: value, min: min, max: max,
             suffix: suffix || "", step: step || 1 }
}

function _choiceField(key, label, values, labels, value) {
    var options = []
    for (var i = 0; i < values.length; i++)
        options.push({ text: labels[i], value: values[i] })
    return { key: key, label: label, kind: "choice", options: options, value: value }
}

function _colourField(key, label, value) {
    return { key: key, label: label, kind: "colour", value: value }
}

function _propsIds() {
    return (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
}

function _drawStyleFields(n) {
    var out = []
    if (!isLine(n) && !isOverlay(n) && !isTable(n)) {
        out.push(_choiceField("fill", "Fill", ["filled", "hollow"], ["Filled", "Hollow"], n.fill || "hollow"))
        out.push(_colourField("color", "Fill color", n.color || styleDefault("color")))
    }
    if (!isOverlay(n)) {
        out.push(_colourField("border", isLine(n) ? "Color" : "Outline color", n.border || styleDefault("border")))
        if (!isTable(n) && !isText(n)) {
            out.push(_numField("stroke", "Line width", n.stroke || 2, 1, 24, "px"))
            out.push(_choiceField("dash", "Outline", ["", "dash", "dot"], ["Solid", "Dashed", "Dotted"], n.dash || ""))
        }
    }
    if (isText(n)) {
        out.push(_numField("fontSize", "Font size", n.fontSize || 12, 6, 72, "px"))
        out.push(_colourField("textColor", "Text color", n.textColor || styleDefault("textColor")))
    }
    if (isLine(n)) {
        var heads = ["none", "solid", "hollow"]
        var headLabels = ["None", "Solid", "Hollow"]
        out.push(_choiceField("headStart", "Start head", heads, headLabels, n.headStart || "none"))
        out.push(_choiceField("headEnd", "End head", heads, headLabels, n.headEnd || "none"))
    }
    out.push(_numField("opacity", "Opacity", Math.round((n.opacity === undefined ? 1 : n.opacity) * 100), 0, 100, "%"))
    return out
}

function propsModel() {
    tick
    var ids = _propsIds()
    if (!ids.length)
        return { title: "Nothing selected", locked: false, fields: [] }
    var n = nodeAt(selectedId) || nodeAt(ids[0])
    if (!n)
        return { title: "Nothing selected", locked: false, fields: [] }
    var fields = []
    var title = layerName(n)
    if (ids.length > 1) {
        // Several: only what applies to all of them at once.
        title = ids.length + " selected"
        if (isDraw(n))
            fields = _drawStyleFields(n).filter(function(f) { return f.key !== "fontSize" })
        else
            fields = [_numField("fontSize", "Font size", n.fontSize || 10, 6, 40, "px"),
                      _numField("chipSize", "Chip size", n.chipSize || 18, 8, 64, "px"),
                      _colourField("color", "Fill color", styleVal(n, null, "color", styleDefault("color"))),
                      _colourField("border", "Outline color", styleVal(n, null, "border", styleDefault("border"))),
                      _colourField("textColor", "Text color", styleVal(n, null, "textColor", styleDefault("textColor")))]
        return { title: title, locked: false, fields: fields }
    }
    if (isLine(n)) {
        var e = lineEndsAt(n)
        fields.push(_numField("ax", "Start X", _pct(xToFx(e.ax)), -50, 150, "%", 0.1))
        fields.push(_numField("ay", "Start Y", _pct(yToFy(e.ay)), -50, 150, "%", 0.1))
        fields.push(_numField("bx", "End X", _pct(xToFx(e.bx)), -50, 150, "%", 0.1))
        fields.push(_numField("by", "End Y", _pct(yToFy(e.by)), -50, 150, "%", 0.1))
    } else if (isDraw(n)) {
        var g = drawGeom(n)
        fields.push(_numField("x", "X", _pct(xToFx(g.x)), -50, 150, "%", 0.1))
        fields.push(_numField("y", "Y", _pct(yToFy(g.y)), -50, 150, "%", 0.1))
        fields.push(_numField("w", "Width", _pct(g.w / Math.max(1, spaceRect().w)), 0.1, 200, "%", 0.1))
        fields.push(_numField("h", "Height", _pct(g.h / Math.max(1, spaceRect().h)), 0.1, 200, "%", 0.1))
        if (isRotatable(n))
            fields.push(_numField("rot", "Angle", Math.round((n.rot || 0) * 10) / 10, 0, 360, "°", 1))
        if (isOverlay(n)) {
            var c = n.crop || {}
            fields.push(_numField("cropL", "Crop left", _pct(c.l || 0), 0, 98, "%", 0.1))
            fields.push(_numField("cropT", "Crop top", _pct(c.t || 0), 0, 98, "%", 0.1))
            fields.push(_numField("cropR", "Crop right", _pct(c.r || 0), 0, 98, "%", 0.1))
            fields.push(_numField("cropB", "Crop bottom", _pct(c.b || 0), 0, 98, "%", 0.1))
        }
    } else {
        fields.push(_numField("x", "X", _pct(n.chipFx), 0, 100, "%", 0.1))
        fields.push(_numField("y", "Y", _pct(n.chipFy), 0, 100, "%", 0.1))
        if (!isGroup(n)) {
            fields.push(_numField("hotX", "Hotspot X", _pct(hotFxOf(n)), 0, 100, "%", 0.1))
            fields.push(_numField("hotY", "Hotspot Y", _pct(hotFyOf(n)), 0, 100, "%", 0.1))
        }
    }
    if (isDraw(n))
        fields = fields.concat(_drawStyleFields(n))
    else
        fields = fields.concat([
            _numField("fontSize", "Font size", n.fontSize || 10, 6, 40, "px"),
            _numField("chipSize", "Chip size", n.chipSize || 18, 8, 64, "px"),
            _colourField("color", "Fill color", styleVal(n, null, "color", styleDefault("color"))),
            _colourField("border", "Outline color", styleVal(n, null, "border", styleDefault("border"))),
            _colourField("textColor", "Text color", styleVal(n, null, "textColor", styleDefault("textColor"))),
            _colourField("hotColor", "Hotspot color", styleVal(n, null, "hotColor", styleDefault("hotColor")))
        ])
    return { title: title, locked: isLocked(n), fields: fields }
}

// A drawing placed by its box: shapes drawn around chips let go of them.
function _placeDraw(n, x, y, w, h) {
    if (n.around && n.around.length) {
        var g = drawGeom(n)
        n.around = []
        n.fx = xToFx(g.x)
        n.fy = yToFy(g.y)
        n.fw = g.w / Math.max(1, spaceRect().w)
        n.fh = g.h / Math.max(1, spaceRect().h)
    }
    if (x !== null) n.fx = x
    if (y !== null) n.fy = y
    if (w !== null) n.fw = Math.max(0.001, w)
    if (h !== null) n.fh = Math.max(0.001, h)
    followTablePacked(n)
    syncOverlayChips(n)
}

function setProp(key, value) {
    var ids = _propsIds()
    if (!ids.length)
        return
    var n = nodeAt(selectedId) || nodeAt(ids[0])
    var v = Number(value)
    if (["color", "border", "textColor", "hotColor"].indexOf(key) >= 0) {
        if (isDraw(n))
            requestDrawColor(key)
        else
            pickColor(key)
        return
    }
    if (["fill", "dash", "headStart", "headEnd"].indexOf(key) >= 0) {
        applyDrawField(key, value)
        return
    }
    if (!(v === v))
        return
    if (key === "opacity") {
        applyDrawField("opacity", Math.max(0, Math.min(100, v)) / 100)
        return
    }
    if (key === "stroke") {
        applyDrawField("stroke", Math.max(1, v))
        return
    }
    if (key === "fontSize" || key === "chipSize") {
        applyField(key, v)
        return
    }
    if (key === "rot") {
        setRotation(v)
        return
    }
    if (key.indexOf("crop") === 0) {
        setCropEdge({ cropL: "l", cropT: "t", cropR: "r", cropB: "b" }[key], v)
        return
    }
    if (!n || isLocked(n) || ids.length > 1)
        return
    var f = v / 100
    if (isLine(n)) {
        var e = lineEndsAt(n)
        var ax = key === "ax" ? fxToX(f) : e.ax
        var ay = key === "ay" ? fyToY(f) : e.ay
        var bx = key === "bx" ? fxToX(f) : e.bx
        var by = key === "by" ? fyToY(f) : e.by
        setLineEnds(n, ax, ay, bx, by)
    } else if (isDraw(n)) {
        _placeDraw(n, key === "x" ? f : null, key === "y" ? f : null,
                   key === "w" ? f : null, key === "h" ? f : null)
    } else if (key === "x" || key === "y") {
        if (key === "x") n.chipFx = clamp01(f)
        else n.chipFy = clamp01(f)
        refreshChipPack(n)
    } else if (key === "hotX" || key === "hotY") {
        if (key === "hotX") n.hotFx = clamp01(f)
        else n.hotFy = clamp01(f)
    }
    bump()
}

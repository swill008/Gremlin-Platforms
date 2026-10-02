// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Text boxes: themes, copying and painting formats, fitting and renaming.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function textThemeStyle(n) {
    var theme = (n && n.theme) ? String(n.theme) : "gremlin"
    if (theme === "hollow")
        return { fill: "transparent", border: "#3F3F46", text: "#E4E4E7" }
    if (theme === "sheet")
        return { fill: "#E4E4E7", border: "#18181B", text: "#18181B" }
    return { fill: "#18181B", border: "#3F3F46", text: "#E4E4E7" }
}

function textFormatKeys() {
    return ["theme", "fontSize", "color", "border", "textColor", "fill", "fillOpacity", "borderOpacity", "stroke", "wrap", "scaleFont", "bold", "align", "valign"]
}

function copyTextFormat() {
    var n = nodeAt(selectedId)
    if (!isText(n))
        return
    var clip = {}
    var keys = textFormatKeys()
    var i
    for (i = 0; i < keys.length; i++)
        clip[keys[i]] = n[keys[i]]
    textFormatClip = clip
    textPaintOn = true
    bump()
}

function applyTextFormat(id) {
    if (!textFormatClip)
        return
    var ids = id ? [id] : ((selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : []))
    var keys = textFormatKeys()
    var i
    var k
    for (i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!isText(n))
            continue
        for (k = 0; k < keys.length; k++) {
            if (textFormatClip[keys[k]] !== undefined)
                n[keys[k]] = textFormatClip[keys[k]]
        }
    }
    bump()
}

function clearTextFormat() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    var i
    for (i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (!isText(n))
            continue
        n.theme = "gremlin"
        n.fontSize = 12
        n.color = "#18181B"
        n.border = "#3F3F46"
        n.textColor = "#E4E4E7"
        n.fill = "filled"
        n.fillOpacity = 1
        n.borderOpacity = 1
        n.stroke = 1
        n.wrap = true
        n.scaleFont = false
        n.bold = false
        n.align = "center"
        n.valign = "middle"
    }
    bump()
}

function fitTextBox(n) {
    if (!isText(n) || !_textFit)
        return
    var pad = 8
    var ew = Math.max(1, spaceRect().w)
    var eh = Math.max(1, spaceRect().h)
    _textFit.text = (n.text && String(n.text).length) ? String(n.text) : "Text"
    _textFit.font.pixelSize = uiPx(n.fontSize > 0 ? n.fontSize : 12)
    _textFit.font.bold = !!n.bold
    if (n.wrap === false) {
        _textFit.wrapMode = Text.NoWrap
        _textFit.width = 4000
        var tw = Math.ceil(_textFit.contentWidth > 0 ? _textFit.contentWidth : _textFit.implicitWidth) + pad
        var th = Math.ceil(_textFit.contentHeight > 0 ? _textFit.contentHeight : _textFit.implicitHeight) + pad
        n.fw = Math.max(24, tw) / ew
        n.fh = Math.max(16, th) / eh
    } else {
        var boxW = Math.max(24, (n.fw || 0.08) * ew)
        _textFit.wrapMode = Text.WordWrap
        _textFit.width = Math.max(16, boxW - pad)
        var th2 = Math.ceil(_textFit.contentHeight > 0 ? _textFit.contentHeight : _textFit.implicitHeight) + pad
        n.fh = Math.max(16, th2) / eh
    }
}

function copyTextPlain() {
    var n = nodeAt(selectedId)
    if (!isText(n))
        return
    if (!_textClip) {
        bump()
        return
    }
    _textClip.text = n.text || ""
    _textClip.selectAll()
    _textClip.copy()
}

function applyTextBoxSize(pw, ph) {
    var n = nodeAt(selectedId)
    if (!isText(n))
        return
    n.fw = Math.max(8, pw) / Math.max(1, spaceRect().w)
    n.fh = Math.max(8, ph) / Math.max(1, spaceRect().h)
    bump()
}

function textBoxSizeEq(pw, ph) {
    var n = nodeAt(selectedId)
    if (!isText(n))
        return false
    var w = Math.round((n.fw || 0) * spaceRect().w)
    var h = Math.round((n.fh || 0) * spaceRect().h)
    return Math.abs(w - pw) <= 1 && Math.abs(h - ph) <= 1
}

function applyTextTheme(theme) {
    var n = nodeAt(selectedId)
    if (!isText(n))
        return
    n.theme = theme || "gremlin"
    var st = textThemeStyle(n)
    n.color = st.fill
    n.border = st.border
    n.textColor = st.text
    n.fill = (theme === "hollow") ? "hollow" : "filled"
    bump()
}

function beginTextRename(id) {
    var n = nodeAt(id)
    if (!isText(n))
        return
    renameId = id
    renameMember = -1
    tableRow = -1
    tableCol = -1
    tableExtra = -1
    renameDraft = n.text || ""
    dragKind = ""
    Qt.callLater(function () {
        if (_nameEdit) {
            _nameEdit.forceActiveFocus()
            _nameEdit.selectAll()
        }
    })
    bump()
}

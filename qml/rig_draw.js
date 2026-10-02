// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Drawings: geometry, resizing, default style, drawing new shapes and painting them.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function isDraw(n) {
    return !!(n && n.kind === "draw")
}

function isTable(n) {
    return !!(n && n.kind === "draw" && n.shape === "table")
}

function isText(n) {
    return !!(n && n.kind === "draw" && n.shape === "text")
}

function drawGeom(n) {
    var pad = (n && n.pad > 0) ? n.pad : 8
    var around = (n && n.around) ? n.around : []
    if (around.length) {
        var minx = 1e9
        var miny = 1e9
        var maxx = -1e9
        var maxy = -1e9
        var k
        for (k = 0; k < around.length; k++) {
            var q = nodeAt(around[k])
            if (!q || isDraw(q))
                continue
            var b = chipBounds(q)
            minx = Math.min(minx, b.x)
            miny = Math.min(miny, b.y)
            maxx = Math.max(maxx, b.x + b.w)
            maxy = Math.max(maxy, b.y + b.h)
        }
        if (minx < 1e8)
            return { x: minx - pad, y: miny - pad, w: (maxx - minx) + pad * 2, h: (maxy - miny) + pad * 2 }
    }
    return {
        x: fxToX(n && n.fx ? n.fx : 0),
        y: fyToY(n && n.fy ? n.fy : 0),
        w: fwToW(n && n.fw ? n.fw : 0.08),
        h: fhToH(n && n.fh ? n.fh : 0.06)
    }
}

function applyDrawResize(n, mx, my, handle, altOff) {
    if (!n)
        return
    n.around = []
    var p = snapEnt(mx, my, altOff)
    var x0 = rzX0
    var y0 = rzY0
    var x1 = rzX1
    var y1 = rzY1
    if (handle.indexOf("n") >= 0)
        y0 = p.y
    if (handle.indexOf("s") >= 0)
        y1 = p.y
    if (handle.indexOf("w") >= 0)
        x0 = p.x
    if (handle.indexOf("e") >= 0)
        x1 = p.x
    if (shiftHeld && handle.length === 2) {
        var fx0 = (handle.indexOf("w") >= 0) ? x1 : x0
        var fy0 = (handle.indexOf("n") >= 0) ? y1 : y0
        var mx1 = (handle.indexOf("w") >= 0) ? x0 : x1
        var my1 = (handle.indexOf("n") >= 0) ? y0 : y1
        var lp = lockAspect(fx0, fy0, mx1, my1)
        if (handle.indexOf("w") >= 0)
            x0 = lp.x
        else
            x1 = lp.x
        if (handle.indexOf("n") >= 0)
            y0 = lp.y
        else
            y1 = lp.y
    }
    var nx = Math.min(x0, x1)
    var ny = Math.min(y0, y1)
    var nw = Math.max(8, Math.abs(x1 - x0))
    var nh = Math.max(8, Math.abs(y1 - y0))
    if (isTable(n)) {
        nw = Math.max(tableMinW(n), nw)
        nh = Math.max(tableMinH(n), nh)
    }
    var oldH = fhToH(n.fh || 0)
    n.fx = xToFx(nx)
    n.fy = yToFy(ny)
    n.fw = nw / Math.max(1, spaceRect().w)
    n.fh = nh / Math.max(1, spaceRect().h)
    if (isText(n) && n.scaleFont && oldH > 1) {
        var fs = n.fontSize > 0 ? n.fontSize : 12
        n.fontSize = Math.max(6, Math.min(72, Math.round(fs * (nh / oldH))))
    }
}

function _drawStyle() {
    return {
        kind: "draw",
        rot: 0,
        fill: "hollow",
        color: "#14532D",
        border: "#22C55E",
        stroke: 2,
        opacity: 1,
        pad: 8,
        around: []
    }
}

function addDrawAround(shape) {
    var ids = selectedIds || []
    var around = []
    var i
    for (i = 0; i < ids.length; i++) {
        var q = nodeAt(ids[i])
        if (q && !isDraw(q))
            around.push(ids[i])
    }
    if (!around.length)
        return
    var st = _drawStyle()
    st.id = _uid("d")
    st.shape = shape
    st.around = around
    var g = drawGeom(st)
    st.fx = xToFx(g.x)
    st.fy = yToFy(g.y)
    st.fw = g.w / Math.max(1, spaceRect().w)
    st.fh = g.h / Math.max(1, spaceRect().h)
    nodes.push(st)
    setSelection([st.id])
    bump()
}

function addDrawFree(shape, x0, y0, x1, y1) {
    if (shiftHeld) {
        var lp = lockAspect(x0, y0, x1, y1)
        x1 = lp.x
        y1 = lp.y
    }
    var x = Math.min(x0, x1)
    var y = Math.min(y0, y1)
    var w = Math.abs(x1 - x0)
    var h = Math.abs(y1 - y0)
    if (w < 6 || h < 6)
        return
    var st = _drawStyle()
    st.id = _uid("d")
    st.shape = shape
    st.fx = xToFx(x)
    st.fy = yToFy(y)
    st.fw = w / Math.max(1, spaceRect().w)
    st.fh = h / Math.max(1, spaceRect().h)
    if (shape === "table") {
        st.fill = "filled"
        st.color = "#18181B"
        st.border = "#3F3F46"
        st.stroke = 1
        st.theme = "gremlin"
        st.cols = 2
        st.idCol = false
        st.fontSize = 10
        st.rows = [emptyTableRow(2)]
        st.zLayer = 2
        var minW = tableMinW(st)
        var minH = tableMinH(st)
        if (w < minW)
            st.fw = minW / Math.max(1, spaceRect().w)
        if (h < minH)
            st.fh = minH / Math.max(1, spaceRect().h)
    }
    if (shape === "text") {
        st.fill = "filled"
        st.color = "#18181B"
        st.border = "#3F3F46"
        st.stroke = 1
        st.theme = "gremlin"
        st.text = "Text"
        st.textColor = "#E4E4E7"
        st.fontSize = 12
        st.bold = false
        st.align = "center"
        st.valign = "middle"
        st.fillOpacity = 1
        st.borderOpacity = 1
        st.wrap = true
        st.scaleFont = false
        st.zLayer = 3
    }
    nodes.push(st)
    setSelection([st.id])
    tableRow = 0
    tableCol = 0
    tableExtra = -1
    bump()
}

function setDrawTool(shape) {
    drawTool = (drawTool === shape) ? "" : shape
}

function lockAspect(x0, y0, x1, y1) {
    var w = x1 - x0
    var h = y1 - y0
    var s = Math.max(Math.abs(w), Math.abs(h))
    if (s < 1)
        s = 1
    return Qt.point(x0 + (w >= 0 ? s : -s), y0 + (h >= 0 ? s : -s))
}

function requestDrawColor(field) {
    var n = nodeAt(selectedId)
    if (!isDraw(n))
        return
    var hex = "#E4E4E7"
    if (field === "border")
        hex = n.border || "#3F3F46"
    else if (field === "textColor")
        hex = n.textColor || "#E4E4E7"
    else
        hex = n.color || "#18181B"
    colorPickRequested(field, hex)
}

function paintDraw(ctx, n, w, h) {
    if (!n || n.shape === "image")
        return
    if (n.shape === "text")
        return
    if (n.shape === "table") {
        ctx.save()
        ctx.strokeStyle = n.border || "#3F3F46"
        ctx.lineWidth = 1
        ctx.fillStyle = n.color || "#18181B"
        ctx.fillRect(0.5, 0.5, Math.max(1, w - 1), Math.max(1, h - 1))
        ctx.strokeRect(0.5, 0.5, Math.max(1, w - 1), Math.max(1, h - 1))
        ctx.beginPath()
        ctx.moveTo(w * 0.5, 0)
        ctx.lineTo(w * 0.5, h)
        ctx.moveTo(0, h * 0.5)
        ctx.lineTo(w, h * 0.5)
        ctx.stroke()
        ctx.restore()
        return
    }
    var stroke = n.stroke || 2
    var inset = stroke * 0.5 + 0.5
    var ww = Math.max(2, w - stroke)
    var hh = Math.max(2, h - stroke)
    var shape = n.shape || "rect"
    ctx.save()
    ctx.translate(inset, inset)
    ctx.beginPath()
    if (shape === "ellipse") {
        ctx.save()
        ctx.translate(ww * 0.5, hh * 0.5)
        ctx.scale(Math.max(0.5, ww * 0.5), Math.max(0.5, hh * 0.5))
        ctx.arc(0, 0, 1, 0, 6.2832)
        ctx.restore()
    } else if (shape === "triangle") {
        ctx.moveTo(ww * 0.5, 0)
        ctx.lineTo(ww, hh)
        ctx.lineTo(0, hh)
        ctx.closePath()
    } else if (shape === "diamond") {
        ctx.moveTo(ww * 0.5, 0)
        ctx.lineTo(ww, hh * 0.5)
        ctx.lineTo(ww * 0.5, hh)
        ctx.lineTo(0, hh * 0.5)
        ctx.closePath()
    } else if (shape === "roundrect") {
        var r = Math.min(14, ww * 0.2, hh * 0.2)
        ctx.moveTo(r, 0)
        ctx.lineTo(ww - r, 0)
        ctx.quadraticCurveTo(ww, 0, ww, r)
        ctx.lineTo(ww, hh - r)
        ctx.quadraticCurveTo(ww, hh, ww - r, hh)
        ctx.lineTo(r, hh)
        ctx.quadraticCurveTo(0, hh, 0, hh - r)
        ctx.lineTo(0, r)
        ctx.quadraticCurveTo(0, 0, r, 0)
        ctx.closePath()
    } else {
        ctx.rect(0, 0, ww, hh)
    }
    if (n.fill !== "hollow") {
        ctx.fillStyle = n.color || "#14532D"
        ctx.fill()
    }
    ctx.strokeStyle = n.border || "#22C55E"
    ctx.lineWidth = stroke
    ctx.stroke()
    ctx.restore()
}

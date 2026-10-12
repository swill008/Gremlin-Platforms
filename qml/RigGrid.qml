// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// The snap grid behind the Device Mapping Editor. It covers the map's box
// (the editor) scaled 1.2x about its centre, not only the page, with a
// border on its edge. Visual only: it takes no input, and showChrome hides
// it in prints and exports.
Canvas {
    id: _grid
    property var ed: null
    // How far the grid reaches past the editor on each side.
    readonly property real overX: parent ? parent.width * 0.1 : 0
    readonly property real overY: parent ? parent.height * 0.1 : 0
    readonly property color borderColour: Style.lineStrong
    objectName: "rigGrid"
    x: -overX
    y: -overY
    width: parent ? parent.width + overX * 2 : 0
    height: parent ? parent.height + overY * 2 : 0
    z: 1
    visible: ed.showChrome && ed.gridOn
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onBorderColourChanged: requestPaint()
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var pageW = ed.worldPageW
        var pageH = ed.worldPageH
        var step = Math.max(1, ed.gridSize)
        if (pageW / step > 80)
            step = Math.ceil(pageW / 80)
        if (pageH / step > 80)
            step = Math.max(step, Math.ceil(pageH / 80))
        var major = step * 4
        // World range covered by this canvas, on whole steps from the page's
        // origin so the lines carry on past the page.
        var x0 = Math.floor(ed.xToWorld(-overX) / step) * step
        var x1 = ed.xToWorld(width - overX)
        var y0 = Math.floor(ed.yToWorld(-overY) / step) * step
        var y1 = ed.yToWorld(height - overY)
        ctx.lineWidth = 1
        var w
        var px
        var py
        for (var pass = 0; pass < 2; pass++) {
            var wantMajor = pass === 1
            ctx.strokeStyle = wantMajor ? "#28FFFFFF" : "#14FFFFFF"
            ctx.beginPath()
            for (w = x0; w <= x1; w += step) {
                if ((Math.round(w) % major === 0) !== wantMajor)
                    continue
                px = ed.worldToX(w) + overX + 0.5
                ctx.moveTo(px, 0)
                ctx.lineTo(px, height)
            }
            for (w = y0; w <= y1; w += step) {
                if ((Math.round(w) % major === 0) !== wantMajor)
                    continue
                py = ed.worldToY(w) + overY + 0.5
                ctx.moveTo(0, py)
                ctx.lineTo(width, py)
            }
            ctx.stroke()
        }
        ctx.strokeStyle = borderColour
        ctx.strokeRect(0.5, 0.5, width - 1, height - 1)
    }
}

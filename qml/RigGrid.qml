// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// The snap grid behind the Button Map editor.
Canvas {
    id: _grid
    property var ed: null
    anchors.fill: parent
    z: 1
    visible: ed.interactive && ed.gridOn
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var s = ed.spaceRect()
        var pageW = ed.worldPageW
        var pageH = ed.worldPageH
        var step = Math.max(1, ed.gridSize)
        if (pageW / step > 80)
            step = Math.ceil(pageW / 80)
        if (pageH / step > 80)
            step = Math.max(step, Math.ceil(pageH / 80))
        var major = step * 4
        ctx.save()
        ctx.beginPath()
        ctx.rect(s.x, s.y, s.w, s.h)
        ctx.clip()
        ctx.lineWidth = 1
        ctx.strokeStyle = "#14FFFFFF"
        ctx.beginPath()
        var w
        var px
        var py
        for (w = 0; w <= pageW; w += step) {
            if (Math.round(w) % major === 0)
                continue
            px = ed.worldToX(w) + 0.5
            ctx.moveTo(px, s.y)
            ctx.lineTo(px, s.y + s.h)
        }
        for (w = 0; w <= pageH; w += step) {
            if (Math.round(w) % major === 0)
                continue
            py = ed.worldToY(w) + 0.5
            ctx.moveTo(s.x, py)
            ctx.lineTo(s.x + s.w, py)
        }
        ctx.stroke()
        ctx.strokeStyle = "#28FFFFFF"
        ctx.beginPath()
        for (w = 0; w <= pageW; w += major) {
            px = ed.worldToX(w) + 0.5
            ctx.moveTo(px, s.y)
            ctx.lineTo(px, s.y + s.h)
        }
        for (w = 0; w <= pageH; w += major) {
            py = ed.worldToY(w) + 0.5
            ctx.moveTo(s.x, py)
            ctx.lineTo(s.x + s.w, py)
        }
        ctx.stroke()
        ctx.strokeStyle = "#40A1A1AA"
        ctx.strokeRect(s.x + 0.5, s.y + 0.5, s.w - 1, s.h - 1)
        ctx.restore()
    }
}

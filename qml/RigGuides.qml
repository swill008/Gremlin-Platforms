// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// Alignment guide lines shown while moving items in the Button Map editor.
Canvas {
    id: _guides
    property var ed: null
    anchors.fill: parent
    z: 2
    visible: ed.showChrome && (ed.guideX >= 0 || ed.guideY >= 0
                               || (ed.guidesOn && (ed.rulerGuidesX.length || ed.rulerGuidesY.length)))
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        // Guides from the rulers, across the page.
        if (ed.guidesOn) {
            var s = ed.spaceRect()
            ctx.strokeStyle = String(Style.accent)
            ctx.lineWidth = 1
            ctx.setLineDash([])
            for (var i = 0; i < ed.rulerGuidesX.length; i++) {
                var gx = Math.round(ed.fxToX(ed.rulerGuidesX[i])) + 0.5
                ctx.beginPath()
                ctx.moveTo(gx, s.y)
                ctx.lineTo(gx, s.y + s.h)
                ctx.stroke()
            }
            for (var j = 0; j < ed.rulerGuidesY.length; j++) {
                var gy = Math.round(ed.fyToY(ed.rulerGuidesY[j])) + 0.5
                ctx.beginPath()
                ctx.moveTo(s.x, gy)
                ctx.lineTo(s.x + s.w, gy)
                ctx.stroke()
            }
        }
        ctx.strokeStyle = "#22C55E"
        ctx.lineWidth = 1
        ctx.setLineDash([5, 4])
        if (ed.guideX >= 0) {
            ctx.beginPath()
            ctx.moveTo(ed.guideX + 0.5, 0)
            ctx.lineTo(ed.guideX + 0.5, height)
            ctx.stroke()
        }
        if (ed.guideY >= 0) {
            ctx.beginPath()
            ctx.moveTo(0, ed.guideY + 0.5)
            ctx.lineTo(width, ed.guideY + 0.5)
            ctx.stroke()
        }
    }
    Connections {
        target: ed
        function onGuideXChanged() { _guides.requestPaint() }
        function onGuideYChanged() { _guides.requestPaint() }
        function onRulerGuidesXChanged() { _guides.requestPaint() }
        function onRulerGuidesYChanged() { _guides.requestPaint() }
        function onGuidesOnChanged() { _guides.requestPaint() }
        function onTickChanged() { if (_guides.visible) _guides.requestPaint() }
    }
}

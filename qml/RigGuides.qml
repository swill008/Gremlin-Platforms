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
    visible: ed.interactive && (ed.guideX >= 0 || ed.guideY >= 0)
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
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
    }
}

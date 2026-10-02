// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// Leader lines and hotspots of every chip in the Button Map editor, on one canvas.
Canvas {
    id: _lines
    property var ed: null
    anchors.fill: parent
    z: 2
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var list = ed.nodes || []
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (ed.isDraw(n) || ed.isHidden(n))
                continue
            var sel = ed.showChrome && ed.isSelected(n.id)
            var ls = ed.leaderList(n)
            var li
            for (li = 0; li < ls.length; li++) {
                var L = ls[li]
                if (L.hidden)
                    continue
                var leadSel = sel && ed.selectedLeader === li
                var lw = ed.leaderWidthOf(n)
                ctx.strokeStyle = leadSel ? "#FBBF24" : (sel ? "#D4D4D8" : (n.leaderColor || "#A1A1AA"))
                ctx.lineWidth = leadSel ? Math.max(lw, lw + 0.4) : lw
                ctx.lineJoin = "round"
                ctx.lineCap = "round"
                ed.strokeLeader(ctx, n, ed.pathPtsL(L), L)
            }
            var hot = ed.hotPt(n)
            var hs = ed.hotSz(n)
            var hShape = n.hotShape || "round"
            var hFill = n.hotFill || "filled"
            if (!ed.hotHidden(n))
                ed.drawMark(ctx, hot.x, hot.y, hs, hShape, hFill, sel ? "#FBBF24" : (n.hotColor || "#F4F4F5"))
            if (ed.showChrome) {
                for (li = 0; li < ls.length; li++) {
                    var L2 = ls[li]
                    if (!ed.showLeaderHandles(n, li) || ed.leaderBlocked(n, li))
                        continue
                    var leadSel2 = true
                    var a = ed.endPt(L2.from)
                    ed.drawMark(ctx, a.x, a.y, 8, "round", "filled", "#38BDF8")
                    if (L2.to && L2.to.type !== "hot") {
                        var tp = ed.endPt(L2.to)
                        ed.drawMark(ctx, tp.x, tp.y, 8, "round", "filled", "#FB923C")
                    }
                    var spines = L2.spines || []
                    for (var s = 0; s < spines.length; s++) {
                        var sx = ed.fxToX(spines[s].fx)
                        var sy = ed.fyToY(spines[s].fy)
                        ctx.beginPath()
                        ctx.arc(sx, sy, 5, 0, 6.3)
                        ctx.fillStyle = (ed.selectedSpine === s || (ed.dragKind === "spine" && ed.dragSpine === s)) ? "#F59E0B" : "#94A3B8"
                        ctx.fill()
                    }
                }
            }
        }
    }
}

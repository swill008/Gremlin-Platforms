// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

Item {
    id: _ed

    property var face: null
    property var nodes: []
    property string selectedId: ""
    property int selectedSpine: -1
    property string dragKind: ""
    property int dragSpine: -1
    property real dragOffX: 0
    property real dragOffY: 0
    property int tick: 0
    property bool seeded: false
    property bool interactive: false
    property var selectedIds: []
    property bool banding: false
    property bool bandAdd: false
    property real bandX0: 0
    property real bandY0: 0
    property real bandX1: 0
    property real bandY1: 0
    property bool gridOn: true
    property bool snapOn: true
    property bool snapEntOn: true
    property real guideX: -1
    property real guideY: -1
    property string guideXKind: ""
    property string guideYKind: ""
    property int gridSize: 200
    property bool altHeld: false
    property bool shiftHeld: false
    property string groupEditId: ""
    property int selectedMember: -1
    property int dragMember: -1
    property string renameId: ""
    property int renameMember: -1
    property int tableRow: -1
    property int tableCol: -1
    property int tableExtra: -1
    property string packWarn: ""
    readonly property real worldPageW: 32000
    readonly property real worldPageH: 18000
    readonly property real innerPageW: 24000
    readonly property real innerPageH: 13500
    readonly property real innerPadX: 0.125
    readonly property real innerPadY: 0.125
    readonly property real uiRefW: 1600
    readonly property real uiScale: {
        var s = Math.min(width / Math.max(1, worldPageW), height / Math.max(1, worldPageH))
        var sw = worldPageW * s
        if (sw < 8)
            return 1
        return sw / uiRefW
    }
    readonly property string worldSpace: "world"
    property var textFormatClip: null
    property bool textPaintOn: false
    property string renameDraft: ""
    property string armRenameId: ""
    property int armRenameMember: -1
    property int selectedLeader: 0
    property int selectedSeg: -1
    property int dragLeader: 0
    property string drawTool: ""
    property bool plantSnap: false
    property string overlayHoverId: ""
    property string hoverHwLabel: ""
    property real hoverTipX: 0
    property real hoverTipY: 0
    property real drawX0: 0
    property real drawY0: 0
    property real drawX1: 0
    property real drawY1: 0
    property real rzX0: 0
    property real rzY0: 0
    property real rzX1: 0
    property real rzY1: 0
    property var clip: []
    property bool lineArm: false
    property real lineArmX: 0
    property real lineArmY: 0
    property bool spineHoldArm: false
    property string spineHoldId: ""
    property int spineHoldLeader: 0
    property int spineHoldIndex: -1
    property real spineHoldX: 0
    property real spineHoldY: 0
    property real photoScale: 1
    property real photoOffX: 0
    property real photoOffY: 0
    property real photoRot: 0
    property bool movePhoto: false
    property real photoDragX0: 0
    property real photoDragY0: 0
    signal selectedChanged()
    signal chipMenuRequested(real x, real y)
    signal overlayImportRequested()
    signal historyChanged()
    signal colorPickRequested(string field, string hex)

    property var hist
    property int histAt: -1
    property int histCap: 80
    property bool _restoring: false
    readonly property bool canUndo: histAt > 0
    readonly property bool canRedo: histAt >= 0 && hist && histAt < hist.length - 1

    // Do NOT declare signal nodesChanged — property var nodes already has it.

    function repaint() {
        tick++
        if (_lines)
            _lines.requestPaint()
    }

    function bump() {
        repaint()
        selectedChanged()
        if (!_restoring)
            pushHist()
    }

    function snapJson() {
        try {
            return JSON.stringify(nodes || [])
        } catch (e) {
            return "[]"
        }
    }

    function seedHist() {
        hist = [snapJson()]
        histAt = 0
        historyChanged()
    }

    function pushHist() {
        if (_restoring || !interactive)
            return
        var s = snapJson()
        var cur = hist || []
        if (histAt >= 0 && histAt < cur.length && cur[histAt] === s)
            return
        var next = cur.slice(0, histAt + 1)
        next.push(s)
        if (next.length > histCap)
            next = next.slice(next.length - histCap)
        hist = next
        histAt = next.length - 1
        historyChanged()
    }

    function applySnap(s) {
        var next = []
        try {
            next = JSON.parse(s)
        } catch (e) {
            return
        }
        var list = nodes
        if (!list)
            return
        list.splice(0, list.length)
        for (var i = 0; i < next.length; i++)
            list.push(next[i])
    }

    function undo() {
        if (!canUndo)
            return
        histAt = histAt - 1
        _restoring = true
        applySnap(hist[histAt])
        groupEditId = ""
        selectedMember = -1
        setSelection([])
        historyChanged()
        bump()
        _restoring = false
    }

    function redo() {
        if (!canRedo)
            return
        histAt = histAt + 1
        _restoring = true
        applySnap(hist[histAt])
        groupEditId = ""
        selectedMember = -1
        setSelection([])
        historyChanged()
        bump()
        _restoring = false
    }

    function clearLayout() {
        setSelection([])
        groupEditId = ""
        selectedMember = -1
        selectedLeader = 0
        selectedSeg = -1
        dragKind = ""
        bump()
    }

    function applyPointer(mx, my, altOff) {
        if (!dragKind || dragKind === "band")
            return
        var n = nodeAt(selectedId)
        if (!n)
            return
        if (dragKind === "from" || dragKind === "to") {
            var ep2 = snapPos(mx, my, altOff)
            var fr2 = { type: "free", fx: xToFx(ep2.x), fy: yToFy(ep2.y) }
            var Ld = currentLeader(n)
            if (!Ld)
                return
            if (dragKind === "to") Ld.to = fr2
            else Ld.from = fr2
            if (selectedLeader === 0) {
                if (dragKind === "to") n.to = fr2
                else n.from = fr2
            }
        } else if (dragKind === "hot") {
            var hp = snapPos(mx, my, altOff)
            n.hotFx = xToFx(hp.x)
            n.hotFy = yToFy(hp.y)
        } else if (dragKind === "photo") {
            var sPhoto = spaceRect()
            var dw = Math.max(1, sPhoto.w)
            var dh = Math.max(1, sPhoto.h)
            photoOffX = Math.max(-1, Math.min(1, dragOffX + (mx - photoDragX0) / dw))
            photoOffY = Math.max(-1, Math.min(1, dragOffY + (my - photoDragY0) / dh))
            return
        } else if (dragKind === "chip") {
            var cp = snapPos(mx - dragOffX, my - dragOffY, altOff)
            var fx = xToFx(cp.x)
            var fy = yToFy(cp.y)
            var dFx = fx - n.chipFx
            var dFy = fy - n.chipFy
            var pack = tablePackOf(n)
            if (!pack) {
                var ids0 = (selectedIds && selectedIds.length) ? selectedIds : [selectedId]
                var pi
                for (pi = 0; !pack && pi < ids0.length; pi++)
                    pack = tablePackOf(nodeAt(ids0[pi]))
            }
            if (pack) {
                moveTablePack(pack, dFx, dFy)
            } else {
                var ids = (selectedIds && selectedIds.length) ? selectedIds : [selectedId]
                for (var i = 0; i < ids.length; i++) {
                    var q = nodeAt(ids[i])
                    if (!q)
                        continue
                    q.chipFx = clamp01(q.chipFx + dFx)
                    q.chipFy = clamp01(q.chipFy + dFy)
                    refreshChipPack(q)
                }
            }
        } else if (dragKind === "spine" && dragSpine >= 0) {
            var Ls = currentLeader(n)
            if (!Ls)
                return
            if (!Ls.spines) Ls.spines = []
            if (dragSpine < Ls.spines.length) {
                var sp = snapPos(mx, my, altOff)
                Ls.spines[dragSpine].fx = xToFx(sp.x)
                Ls.spines[dragSpine].fy = yToFy(sp.y)
            }
            n.spines = Ls.spines
        } else if (dragKind === "tablecell") {
            if (!isTable(n) || isLocked(n) || !tableHasTarget())
                return
            ensureTable(n)
            var cell = tableCurrentCell(n)
            if (!cell || !cell.free)
                return
            var rc0 = tableCurrentRect(n)
            var tp = snapEnt(mx - dragOffX, my - dragOffY, altOff)
            writeTablePartRect(n, cell, tp.x, tp.y, rc0.w, rc0.h)
        } else if (dragKind === "draw") {
            if (isLocked(n))
                return
            var packDraw = tablePackOf(n)
            var g0 = drawGeom(n)
            var np = snapEnt(mx - dragOffX, my - dragOffY, altOff)
            var ddx = np.x - g0.x
            var ddy = np.y - g0.y
            if (packDraw && !isTable(n)) {
                moveTablePack(packDraw, ddx / Math.max(1, spaceRect().w), ddy / Math.max(1, spaceRect().h))
                return
            }
            var around = n.around || []
            if (around.length) {
                var ai
                for (ai = 0; ai < around.length; ai++) {
                    var qn = nodeAt(around[ai])
                    if (!qn || isDraw(qn))
                        continue
                    qn.chipFx = clamp01(qn.chipFx + ddx / Math.max(1, spaceRect().w))
                    qn.chipFy = clamp01(qn.chipFy + ddy / Math.max(1, spaceRect().h))
                }
            } else {
                var oldFx = n.fx || 0
                var oldFy = n.fy || 0
                n.fx = xToFx(np.x)
                n.fy = yToFy(np.y)
                shiftIndependentParts(n, n.fx - oldFx, n.fy - oldFy)
            }
            followTablePacked(n)
            syncOverlayChips(n)
        } else if (dragKind.indexOf("cell-") === 0) {
            if (!isTable(n) || isLocked(n) || !tableHasTarget())
                return
            applyTableCellResize(n, mx, my, dragKind.slice(5), altOff)
        } else if (dragKind.indexOf("draw-") === 0) {
            if (isLocked(n))
                return
            var rzOldFx = n.fx || 0
            var rzOldFy = n.fy || 0
            applyDrawResize(n, mx, my, dragKind.slice(5), altOff)
            shiftIndependentParts(n, (n.fx || 0) - rzOldFx, (n.fy || 0) - rzOldFy)
            followTablePacked(n)
            syncOverlayChips(n)
        } else if (dragKind === "member" && n.members && dragMember >= 0 && dragMember < n.members.length) {
            var mp = snapPos(mx - dragOffX, my - dragOffY, altOff)
            var mm = n.members[dragMember]
            if (themeLayout(n)) {
                var g = themeGeom(n)
                var role = fiveWayRole(mm)
                var home = g[role] || g.center
                mm.offX = (mp.x - fxToX(n.chipFx) - home.x) / Math.max(1, spaceRect().w)
                mm.offY = (mp.y - fyToY(n.chipFy) - home.y) / Math.max(1, spaceRect().h)
            } else {
                bakeAlignToFree(n)
                mm.ox = xToFx(mp.x) - n.chipFx
                mm.oy = yToFy(mp.y) - n.chipFy
            }
        }
        if (n && (dragKind === "chip" || dragKind === "draw" || dragKind === "tablecell" || dragKind === "member"))
            updateMoveGuides(n)
        else
            clearMoveGuides()
        repaint()
    }

    function isStyleKey(key) {
        return key === "chipShape" || key === "chipSize" || key === "chipFill" || key === "fontSize"
            || key === "color" || key === "border" || key === "textColor" || key === "highlight"
            || key === "hlColor" || key === "hlBorder" || key === "hlText"
    }

    function targetMember() {
        var n = nodeAt(selectedId)
        if (!n || !isGroup(n) || groupEditId !== n.id || selectedMember < 0)
            return null
        var mem = n.members || []
        if (selectedMember >= mem.length)
            return null
        return mem[selectedMember]
    }

    function styleVal(n, mem, key, fallback) {
        if (mem && mem[key] !== undefined && mem[key] !== null && mem[key] !== "")
            return mem[key]
        if (n && n[key] !== undefined && n[key] !== null && n[key] !== "")
            return n[key]
        return fallback
    }

    function applyField(key, val) {
        var mem = targetMember()
        if (mem && isStyleKey(key)) {
            mem[key] = val
            bump()
            return
        }
        var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
        for (var i = 0; i < ids.length; i++) {
            var n = nodeAt(ids[i])
            if (n) {
                n[key] = val
                if (isText(n) && (key === "color" || key === "border" || key === "textColor"))
                    delete n.theme
                if (isText(n) && (key === "wrap" || key === "fontSize" || key === "bold"))
                    fitTextBox(n)
            }
        }
        bump()
    }

    function fieldEq(key, val, fallback) {
        var n = nodeAt(selectedId)
        var mem = targetMember()
        var cur = styleVal(n, mem, key, undefined)
        if (cur === undefined || cur === null || cur === "")
            return val === fallback
        return cur === val
    }

    function styleDefault(key) {
        if (key === "color") return "#18181B"
        if (key === "border") return "#3F3F46"
        if (key === "textColor") return "#E4E4E7"
        if (key === "hlColor") return "#14532D"
        if (key === "hlBorder") return "#22C55E"
        if (key === "hlText") return "#BBF7D0"
        if (key === "leaderColor") return "#A1A1AA"
        if (key === "hotColor") return "#F4F4F5"
        return ""
    }

    function pickColor(field) {
        var n = nodeAt(selectedId)
        var mem = (field === "leaderColor" || field === "hotColor") ? null : targetMember()
        colorPickRequested(field, styleVal(n, mem, field, styleDefault(field)))
    }

    function uiPx(px) {
        var v = (px || 0) * uiScale
        return v < 1 ? 1 : v
    }

    function leaderWidthOf(n) {
        var w = n && n.leaderWidth
        if (!(w > 0))
            w = 1.1
        w = Math.max(0.5, Math.min(4, w))
        return Math.max(0.6, w * uiScale)
    }

    function resetMemberStyle() {
        var mem = targetMember()
        if (!mem)
            return
        var keys = ["chipShape", "chipSize", "chipFill", "fontSize", "color", "border", "textColor", "hlColor", "hlBorder", "hlText", "offX", "offY"]
        var i
        for (i = 0; i < keys.length; i++)
            delete mem[keys[i]]
        bump()
    }

    function snapWorld(w) {
        var g = gridSize
        if (!snapOn || g < 1)
            return w
        return Math.round(w / g) * g
    }

    function snapPx(v) {
        return worldToX(snapWorld(xToWorld(v)))
    }

    function nodeBox(n) {
        if (!n)
            return { x: 0, y: 0, w: 8, h: 8 }
        if (isDraw(n))
            return drawGeom(n)
        if (isGroup(n)) {
            return {
                x: fxToX(n.chipFx) + groupMinX(n),
                y: fyToY(n.chipFy) + groupMinY(n),
                w: Math.max(8, groupSpanW(n)),
                h: Math.max(8, groupSpanH(n))
            }
        }
        return chipBounds(n)
    }

    function clearMoveGuides() {
        guideX = -1
        guideY = -1
        guideXKind = ""
        guideYKind = ""
    }

    function guideSkipTarget(moving, other) {
        if (!other || !moving || other.id === moving.id)
            return true
        var ids = selectedIds || []
        var i
        for (i = 0; i < ids.length; i++) {
            if (ids[i] === other.id)
                return true
        }
        var pack = tablePackOf(moving)
        if (pack && tablePackOf(other) === pack)
            return true
        return false
    }

    function updateMoveGuides(n) {
        clearMoveGuides()
        if (!n || altHeld)
            return
        var s = spaceRect()
        var b = nodeBox(n)
        var slop = Style.dp(10)
        var cx = b.x + b.w * 0.5
        var cy = b.y + b.h * 0.5
        var left = b.x
        var right = b.x + b.w
        var top = b.y
        var bot = b.y + b.h
        var bestX = slop + 1
        var bestY = slop + 1
        var rankX = 9
        var rankY = 9
        function considerX(line, kind, rank, dist) {
            if (dist > slop)
                return
            if (rank < rankX || (rank === rankX && dist < bestX)) {
                guideX = line
                guideXKind = kind
                bestX = dist
                rankX = rank
            }
        }
        function considerY(line, kind, rank, dist) {
            if (dist > slop)
                return
            if (rank < rankY || (rank === rankY && dist < bestY)) {
                guideY = line
                guideYKind = kind
                bestY = dist
                rankY = rank
            }
        }
        var pageCx = s.x + s.w * 0.5
        var pageCy = s.y + s.h * 0.5
        considerX(pageCx, "center", 0, Math.abs(cx - pageCx))
        considerY(pageCy, "center", 0, Math.abs(cy - pageCy))
        considerX(s.x, "left", 2, Math.abs(left - s.x))
        considerX(s.x + s.w, "right", 2, Math.abs(right - (s.x + s.w)))
        considerY(s.y, "top", 2, Math.abs(top - s.y))
        considerY(s.y + s.h, "bottom", 2, Math.abs(bot - (s.y + s.h)))
        if (!snapEntOn)
            return
        var list = nodes || []
        var i
        for (i = 0; i < list.length; i++) {
            var o = list[i]
            if (guideSkipTarget(n, o))
                continue
            var ob = nodeBox(o)
            if (ob.w < 2 || ob.h < 2)
                continue
            var oL = ob.x
            var oR = ob.x + ob.w
            var oC = ob.x + ob.w * 0.5
            var oT = ob.y
            var oB = ob.y + ob.h
            var oM = ob.y + ob.h * 0.5
            considerX(oC, "center", 1, Math.abs(cx - oC))
            considerX(oL, "left", 3, Math.abs(left - oL))
            considerX(oR, "right", 3, Math.abs(right - oR))
            considerX(oL, "right", 3, Math.abs(right - oL))
            considerX(oR, "left", 3, Math.abs(left - oR))
            considerY(oM, "center", 1, Math.abs(cy - oM))
            considerY(oT, "top", 3, Math.abs(top - oT))
            considerY(oB, "bottom", 3, Math.abs(bot - oB))
            considerY(oT, "bottom", 3, Math.abs(bot - oT))
            considerY(oB, "top", 3, Math.abs(top - oB))
        }
    }

    function commitGuideSnap() {
        if (guideX < 0 && guideY < 0)
            return
        var n = nodeAt(selectedId)
        if (!n)
            return
        var b = nodeBox(n)
        var nx = b.x
        var ny = b.y
        if (guideXKind === "center")
            nx = guideX - b.w * 0.5
        else if (guideXKind === "left")
            nx = guideX
        else if (guideXKind === "right")
            nx = guideX - b.w
        if (guideYKind === "center")
            ny = guideY - b.h * 0.5
        else if (guideYKind === "top")
            ny = guideY
        else if (guideYKind === "bottom")
            ny = guideY - b.h
        var dx = nx - b.x
        var dy = ny - b.y
        if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5)
            return
        var pack = tablePackOf(n)
        if (pack) {
            moveTablePack(pack, dx / Math.max(1, spaceRect().w), dy / Math.max(1, spaceRect().h))
        } else if (isDraw(n)) {
            n.fx = xToFx(nx)
            n.fy = yToFy(ny)
            followTablePacked(n)
        } else {
            n.chipFx = xToFx(nx - (isGroup(n) ? groupMinX(n) : 0))
            n.chipFy = yToFy(ny - (isGroup(n) ? groupMinY(n) : 0))
        }
    }

    function snapPos(x, y, altOff) {
        if (altOff || !snapOn)
            return Qt.point(x, y)
        return Qt.point(worldToX(snapWorld(xToWorld(x))), worldToY(snapWorld(yToWorld(y))))
    }

    onInteractiveChanged: {
        if (!interactive) {
            selectedId = ""
            selectedIds = []
            selectedSpine = -1
            dragKind = ""
            banding = false
            groupEditId = ""
            selectedMember = -1
            dragMember = -1
            hoverHwLabel = ""
            cancelRename()
            armRenameId = ""
            armRenameMember = -1
        } else {
            Qt.callLater(seedHist)
        }
        if (_lines)
            _lines.requestPaint()
    }

    function nodeAt(id) {
        var list = nodes || []
        for (var i = 0; i < list.length; i++) {
            if (list[i].id === id) {
                return list[i]
            }
        }
        return null
    }

    function nodeIndex(id) {
        var list = nodes || []
        for (var i = 0; i < list.length; i++) {
            if (list[i].id === id) {
                return i
            }
        }
        return -1
    }

    function destOf(kind, hwId) {
        tick
        if (!face) {
            return "—"
        }
        if (kind === "axis" || kind === "axis_stack") {
            return face.labelAxis(hwId)
        }
        if (kind === "hat") {
            return face.labelHat(hwId)
        }
        return face.labelBtn(hwId)
    }

    // Physical names from the EVO R lock inventory. Shown as default friendly names.
    readonly property var physNames: ({
        "btn:1": "Red trigger half",
        "btn:2": "Red trigger full",
        "btn:3": "Red head button",
        "btn:4": "White cap",
        "btn:5": "Lower grip white",
        "btn:6": "Head 5-way (right of red) up",
        "btn:7": "Head 5-way (right of red) right",
        "btn:8": "Head 5-way (right of red) down",
        "btn:9": "Head 5-way (right of red) left",
        "btn:10": "Head 5-way (right of red) center",
        "btn:11": "Top-right head 5-way up",
        "btn:12": "Top-right head 5-way right",
        "btn:13": "Top-right head 5-way down",
        "btn:14": "Top-right head 5-way left",
        "btn:15": "Top-right head 5-way center",
        "btn:16": "Silver wheel 5-way up",
        "btn:17": "Silver wheel 5-way right",
        "btn:18": "Silver wheel 5-way down",
        "btn:19": "Silver wheel 5-way left",
        "btn:20": "Silver wheel 5-way center",
        "btn:21": "Grey paddle push",
        "btn:22": "Grey paddle pull",
        "btn:23": "En2 right knob up",
        "btn:24": "En2 right knob down",
        "btn:25": "En1 left knob up",
        "btn:26": "En1 left knob down",
        "btn:27": "Middle base pad",
        "btn:28": "Left base pad",
        "btn:29": "Right base pad",
        "hat:1": "Analog ministick",
        "axis:1": "Stick X roll",
        "axis:2": "Stick Y pitch",
        "axis:3": "Stick Z twist",
        "axis:4": "Z slider (En1–En2)"
    })

    // Kind of one chip in a group: its own kind when saved. Files saved before
    // members carried a kind fall back to the group: an axis stack holds axes,
    // any other group buttons.
    function memberKind(n, mem) {
        var own = mem && mem.kind ? String(mem.kind) : ""
        if (own === "axis" || own === "hat")
            return own
        if (own === "btn" || own === "button")
            return "btn"
        return (n && n.kind === "axis_stack") ? "axis" : "btn"
    }

    function leafKind(kind) {
        if (kind === "axis_stack")
            return "axis"
        if (kind === "plus" || kind === "pair" || kind === "stack")
            return "btn"
        return kind || "btn"
    }

    function physicalName(kind, hwId) {
        var k = leafKind(kind) + ":" + hwId
        return physNames[k] || ""
    }

    function hardwareLabel(kind, hwId) {
        var lk = leafKind(kind)
        if (lk === "axis")
            return "Axis " + hwId
        if (lk === "hat")
            return "Hat " + hwId
        return "Button " + hwId
    }

    function defaultFriendly(kind, hwId) {
        return hardwareLabel(kind, hwId)
    }

    function isClearedFriendly(v) {
        return v === "" || (typeof v === "string" && !String(v).trim().length)
    }

    function isUserFriendly(kind, hwId, v) {
        if (v === undefined || v === null || isClearedFriendly(v))
            return false
        var t = String(v).trim()
        if (!t.length)
            return false
        if (t === hardwareLabel(kind, hwId))
            return false
        if (t === physicalName(kind, hwId))
            return false
        return true
    }

    function carryFriendly(v, fallback) {
        if (isClearedFriendly(v))
            return ""
        if (v !== undefined && v !== null && String(v).length)
            return v
        return fallback
    }

    function friendlyOf(n, mem) {
        if (mem) {
            var lk = memberKind(n, mem)
            if (isUserFriendly(lk, mem.hwId, mem.friendly))
                return String(mem.friendly).trim()
            return hardwareLabel(lk, mem.hwId)
        }
        if (!n)
            return ""
        if (isGroup(n)) {
            if (n.friendly && !isClearedFriendly(n.friendly) && n.friendly !== n.id)
                return n.friendly
            if (n.label && String(n.label).length)
                return n.label
            return n.id
        }
        if (isDraw(n))
            return (n.friendly && String(n.friendly).length) ? n.friendly : "Draw"
        if (isUserFriendly(n.kind, n.hwId, n.friendly))
            return String(n.friendly).trim()
        if (n.label && String(n.label).length && isUserFriendly(n.kind, n.hwId, n.label))
            return String(n.label).trim()
        return hardwareLabel(n.kind, n.hwId)
    }

    function fullNameOf(kind, hwId) {
        var lk = leafKind(kind)
        var idn = lk === "axis" ? ("Axis " + hwId) : (lk === "hat" ? ("Hat " + hwId) : ("Button " + hwId))
        var phys = physicalName(lk, hwId)
        var dest = destOf(lk, hwId)
        var s = idn
        if (phys.length)
            s += " · " + phys
        if (dest && dest !== "—")
            s += " → " + dest
        return s
    }

    function placedId(kind, hwId) {
        var want = leafKind(kind) + ":" + hwId
        var list = nodes || []
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (isGroup(n)) {
                var mem = n.members || []
                for (var j = 0; j < mem.length; j++) {
                    if (memberKind(n, mem[j]) + ":" + mem[j].hwId === want)
                        return n.id
                }
            } else if (leafKind(n.kind) + ":" + n.hwId === want) {
                return n.id
            }
        }
        return ""
    }

    function catalog() {
        tick
        var rows = (face && face.chipRows) ? face.chipRows : []
        var seen = {}
        var items = []
        var i
        for (i = 0; i < rows.length; i++) {
            var row = rows[i]
            if (!row)
                continue
            var kind = row.kind || "btn"
            var hwId = row.hwId
            var key = kind + ":" + hwId
            if (seen[key])
                continue
            seen[key] = true
            var pid = placedId(kind, hwId)
            var lk = leafKind(kind)
            var hwName = lk === "axis" ? ("Axis " + hwId) : (lk === "hat" ? ("Hat " + hwId) : ("Button " + hwId))
            items.push({
                kind: kind,
                hwId: hwId,
                key: key,
                friendly: defaultFriendly(kind, hwId),
                hwName: hwName,
                dest: row.dest || destOf(lk, hwId),
                fullName: row.dest || fullNameOf(kind, hwId),
                placed: pid.length > 0,
                placedId: pid
            })
        }
        return items
    }

    function viewCenterPage() {
        return Qt.point(xToFx(width * 0.5), yToFy(height * 0.5))
    }

    function clampPhotoScale(v) {
        var n = Number(v)
        if (!(n === n) || n <= 0)
            n = 1
        return Math.max(0.25, Math.min(4, n))
    }

    function clampPhotoOff(v) {
        var n = Number(v)
        if (!(n === n))
            n = 0
        return Math.max(-1, Math.min(1, n))
    }

    function applyPhotoPose(pose) {
        pose = pose || {}
        photoScale = clampPhotoScale(pose.scale)
        photoOffX = clampPhotoOff(pose.offX)
        photoOffY = clampPhotoOff(pose.offY)
        var r = Number(pose.rot)
        if (!(r === r))
            r = 0
        photoRot = r
        if (_photoWell)
            repaint()
    }

    function resetPhotoPose() {
        photoScale = 1
        photoOffX = 0
        photoOffY = 0
        photoRot = 0
        movePhoto = false
        repaint()
    }

    function fitPhotoWell() {
        photoScale = 1
        repaint()
    }

    function photoBag() {
        return {
            scale: photoScale,
            offX: photoOffX,
            offY: photoOffY,
            rot: photoRot
        }
    }

    function hotFxOf(n) {
        if (!n)
            return 0.5
        if (n.hotFx !== undefined && n.hotFx === n.hotFx)
            return n.hotFx
        if (n.chipFx !== undefined && n.chipFx === n.chipFx)
            return n.chipFx
        return 0.5
    }

    function hotFyOf(n) {
        if (!n)
            return 0.5
        if (n.hotFy !== undefined && n.hotFy === n.hotFy)
            return n.hotFy
        if (n.chipFy !== undefined && n.chipFy === n.chipFy)
            return n.chipFy
        return 0.5
    }

    function addChiplet(kind, hwId, wx, wy) {
        kind = leafKind(kind)
        hwId = parseInt(hwId, 10)
        if (!(hwId > 0))
            return
        var existing = placedId(kind, hwId)
        if (existing) {
            setSelection([existing])
            bump()
            return
        }
        var fx
        var fy
        if (wx !== undefined && wy !== undefined && wx !== null && wy !== null) {
            fx = xToFx(wx)
            fy = yToFy(wy)
        } else {
            var c = viewCenterPage()
            fx = c.x
            fy = c.y
        }
        fx = Math.max(0.04, Math.min(0.92, fx))
        fy = Math.max(0.04, Math.min(0.94, fy))
        var st = _styleOf({})
        var n = {
            id: _uid(kind === "btn" ? "b" : kind.charAt(0)),
            kind: kind,
            hwId: hwId,
            prefix: kind === "axis" ? "A" : (kind === "hat" ? "H" : ""),
            label: "",
            friendly: defaultFriendly(kind, hwId),
            hotFx: fx,
            hotFy: fy,
            chipFx: fx,
            chipFy: fy,
            pin: fx < 0.5 ? "right" : "left",
            spines: [],
            curve: st.curve,
            color: st.color,
            border: st.border,
            textColor: st.textColor,
            highlight: st.highlight,
            hlColor: st.hlColor,
            hlBorder: st.hlBorder,
            hlText: st.hlText,
            fontSize: st.fontSize,
            chipSize: st.chipSize,
            chipShape: st.chipShape,
            chipFill: st.chipFill,
            hotSize: st.hotSize,
            hotShape: st.hotShape,
            hotFill: st.hotFill
        }
        var list = nodes || []
        list.push(n)
        setSelection([n.id])
        bump()
    }

    function ensureFriendly(n) {
        if (!n)
            return
        if (isGroup(n)) {
            var mem = n.members || []
            for (var i = 0; i < mem.length; i++) {
                if (mem[i].friendly === undefined || mem[i].friendly === null)
                    mem[i].friendly = defaultFriendly(memberKind(n, mem[i]), mem[i].hwId)
            }
            if (n.friendly === undefined || n.friendly === null)
                n.friendly = n.label && n.label.length ? n.label : n.id
        } else if (isDraw(n)) {
            if (n.friendly === undefined || n.friendly === null)
                n.friendly = "Draw"
        } else if (n.friendly === undefined || n.friendly === null) {
            n.friendly = (n.label && n.label.length) ? n.label : defaultFriendly(n.kind, n.hwId)
        }
    }

    function litOf(kind, hwId) {
        tick
        if (!face) {
            return false
        }
        if (kind === "axis" || kind === "axis_stack") {
            return Math.abs(face.hwAxis(hwId)) > 0.12
        }
        if (kind === "hat") {
            return face.hwHat(hwId) > 0.5
        }
        return face.hwButton(hwId) > 0.5
    }

    function chipXY(n) {
        if (!n)
            return Qt.point(0, 0)
        return Qt.point(fxToX(n.chipFx), fyToY(n.chipFy))
    }

    function pinPt(n, item, side) {
        if (!item) {
            return chipXY(n)
        }
        var pin = side || (n ? n.pin : "right") || "right"
        var x = pin === "right" ? item.width : (pin === "left" ? 0 : item.width * 0.5)
        var y = pin === "top" ? 0 : (pin === "bottom" ? item.height : item.height * 0.5)
        return item.mapToItem(_ed, x, y)
    }

    function pagePhotoRect() {
        return innerPageRect()
    }

    function hotPt(n) {
        if (!n)
            return Qt.point(0, 0)
        return Qt.point(fxToX(hotFxOf(n)), fyToY(hotFyOf(n)))
    }

    function toPhoto(mx, my) {
        return Qt.point(xToFx(mx), yToFy(my))
    }

    function fromEnd(n) {
        if (n && n.from && n.from.type)
            return n.from
        return { type: "chip", id: n ? n.id : "", pin: n && n.pin ? n.pin : "right" }
    }

    function toEnd(n) {
        if (n && n.to && n.to.type)
            return n.to
        return { type: "hot", id: n ? n.id : "" }
    }

    function endPt(end) {
        if (!end)
            return Qt.point(0, 0)
        if (end.type === "free")
            return Qt.point(fxToX(end.fx || 0), fyToY(end.fy || 0))
        if (end.type === "member") {
            var gn = nodeAt(end.id)
            if (!gn || !gn.members || end.member < 0 || end.member >= gn.members.length)
                return chipXY(gn || {})
            var gm = gn.members[end.member]
            var gx = fxToX(gn.chipFx) + groupMinX(gn) + memberLocalX(gn, gm)
            var gy = fyToY(gn.chipFy) + groupMinY(gn) + memberLocalY(gn, gm)
            var gw = chipWGuess(gn, gm)
            var gh = chipH(gn)
            var pin = end.pin || "right"
            var px = pin === "left" ? gx : (pin === "top" || pin === "bottom" ? gx + gw * 0.5 : gx + gw)
            var py = pin === "top" ? gy : (pin === "bottom" ? gy + gh : gy + gh * 0.5)
            return Qt.point(px, py)
        }
        if (end.type === "chip") {
            var cn = nodeAt(end.id)
            var it = _chips.itemAt(nodeIndex(end.id))
            return pinPt(cn, it, end.pin)
        }
        if (end.type === "hot") {
            return hotPt(nodeAt(end.id))
        }
        return Qt.point(0, 0)
    }

    function _legacyLeader(n) {
        return {
            id: ((n && n.id) ? n.id : "n") + "_L0",
            from: fromEnd(n),
            to: toEnd(n),
            spines: (n && n.spines) ? n.spines : [],
            curve: n ? n.curve : true,
            fromCurve: n ? n.fromCurve : undefined
        }
    }

    function leaderList(n) {
        if (!n || n.kind === "draw")
            return []
        if (fiveWayFormat(n) === "radial") {
            if (n.leaders && n.leaders.length)
                return n.leaders
            return buildRadialLeaders(n)
        }
        if (n.leaders)
            return n.leaders
        return [_legacyLeader(n)]
    }

    function ensureLeaders(n) {
        if (!n || n.kind === "draw")
            return []
        if (n.leaders === undefined || n.leaders === null)
            n.leaders = [_legacyLeader(n)]
        return n.leaders
    }

    function currentLeader(n) {
        var ls = ensureLeaders(n)
        if (!ls.length)
            return null
        var i = selectedLeader
        if (i < 0 || i >= ls.length)
            i = 0
        return ls[i]
    }

    function hollowMarkPad(end) {
        if (!end)
            return null
        if (end.type === "hot") {
            var hn = nodeAt(end.id)
            if (!hn)
                return null
            if ((hn.hotFill || "filled") !== "hollow")
                return null
            var hs = hotSz(hn)
            var r = hs * 0.5 + 2
            if ((hn.hotShape || "round") === "square")
                return { shape: "square", hw: r, hh: r }
            return { shape: "round", r: r }
        }
        if (end.type === "chip" || end.type === "member") {
            var cn = nodeAt(end.id)
            if (!cn)
                return null
            var mem = null
            if (end.type === "member" && cn.members && end.member >= 0 && end.member < cn.members.length)
                mem = cn.members[end.member]
            if (!chipIsHollow(cn, mem))
                return null
            var w = chipWGuess(cn, mem)
            var h = chipH(cn, mem)
            var shape = styleVal(cn, mem, "chipShape", "round")
            if (shape === "square")
                return { shape: "square", hw: w * 0.5 + 1, hh: h * 0.5 + 1 }
            return { shape: "round", r: Math.min(w, h) * 0.5 + 1 }
        }
        return null
    }

    function pullToCircle(prev, center, r) {
        var dx = center.x - prev.x
        var dy = center.y - prev.y
        var len = Math.hypot(dx, dy)
        if (len < 0.001)
            return prev
        if (len <= r)
            return prev
        var u = r / len
        return Qt.point(center.x - dx * u, center.y - dy * u)
    }

    function pullToBox(prev, center, hw, hh) {
        var dx = center.x - prev.x
        var dy = center.y - prev.y
        if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001)
            return prev
        var tx = Math.abs(dx) < 0.001 ? 1e9 : hw / Math.abs(dx)
        var ty = Math.abs(dy) < 0.001 ? 1e9 : hh / Math.abs(dy)
        var t = Math.min(tx, ty)
        if (t > 1)
            return prev
        return Qt.point(center.x - t * dx, center.y - t * dy)
    }

    function clipHollowEnd(prev, tip, end) {
        var pad = hollowMarkPad(end)
        if (!pad)
            return tip
        if (end.type === "chip" || end.type === "member")
            return tip
        if (pad.shape === "square")
            return pullToBox(prev, tip, pad.hw, pad.hh)
        return pullToCircle(prev, tip, pad.r)
    }

    function pathPtsL(L) {
        if (!L)
            return []
        var pts = [endPt(L.from)]
        var spines = L.spines || []
        for (var s = 0; s < spines.length; s++) {
            pts.push(Qt.point(fxToX(spines[s].fx), fyToY(spines[s].fy)))
        }
        pts.push(endPt(L.to))
        if (pts.length >= 2) {
            pts[0] = clipHollowEnd(pts[1], pts[0], L.from)
            pts[pts.length - 1] = clipHollowEnd(pts[pts.length - 2], pts[pts.length - 1], L.to)
        }
        return pts
    }

    function pathPts(n) {
        return pathPtsL(leaderList(n)[0])
    }

    function segIsCurve(L, j) {
        if (!L)
            return true
        if (j <= 0) {
            if (L.fromCurve !== undefined)
                return L.fromCurve !== false
            return L.curve !== false
        }
        var sp = (L.spines || [])[j - 1]
        if (sp && sp.curve !== undefined)
            return sp.curve !== false
        return L.curve !== false
    }

    function setSegCurve(L, j, on) {
        if (!L)
            return
        if (j <= 0)
            L.fromCurve = on
        else if (L.spines && L.spines[j - 1])
            L.spines[j - 1].curve = on
        bump()
    }

    function toggleSegCurve() {
        var n = nodeAt(selectedId)
        if (!n)
            return
        var L = currentLeader(n)
        if (!L)
            return
        var j = selectedSeg
        if (j < 0)
            j = (selectedSpine >= 0) ? (selectedSpine + 1) : 0
        setSegCurve(L, j, !segIsCurve(L, j))
    }

    function setAllSegCurve(on) {
        var n = nodeAt(selectedId)
        if (!n)
            return
        var L = currentLeader(n)
        if (!L)
            return
        L.curve = on
        L.fromCurve = on
        var s = L.spines || []
        for (var i = 0; i < s.length; i++)
            s[i].curve = on
        if (selectedLeader === 0)
            n.curve = on
        bump()
    }

    function addLeader() {
        var n = nodeAt(selectedId)
        if (!n)
            return
        var ls = ensureLeaders(n)
        var src = ls.length ? (ls[selectedLeader] || ls[0]) : null
        if (!src) {
            ls.push(_legacyLeader(n))
            selectedLeader = 0
            bump()
            return
        }
        var a = endPt(src.from)
        ls.push({
            id: _uid("L"),
            from: {
                type: src.from && src.from.type ? src.from.type : "chip",
                id: src.from ? src.from.id : n.id,
                pin: src.from ? src.from.pin : (n.pin || "right"),
                fx: src.from ? src.from.fx : 0,
                fy: src.from ? src.from.fy : 0
            },
            to: {
                type: "free",
                fx: xToFx(a.x + 48),
                fy: yToFy(a.y + 36)
            },
            spines: [],
            curve: false,
            fromCurve: false
        })
        selectedLeader = ls.length - 1
        selectedSeg = 0
        bump()
    }

    function addBranch() {
        var n = nodeAt(selectedId)
        if (!n)
            return
        var ls = ensureLeaders(n)
        var src = ls.length ? (ls[selectedLeader] || ls[0]) : null
        if (!src)
            return
        var origin = (src.to && src.to.type === "free") ? src.to : src.from
        var p = endPt(origin)
        ls.push({
            id: _uid("L"),
            from: {
                type: origin && origin.type ? origin.type : "free",
                id: origin ? origin.id : "",
                pin: origin ? origin.pin : "",
                fx: origin ? origin.fx : xToFx(p.x),
                fy: origin ? origin.fy : yToFy(p.y)
            },
            to: {
                type: "free",
                fx: xToFx(p.x + 56),
                fy: yToFy(p.y - 44)
            },
            spines: [],
            curve: true,
            fromCurve: true
        })
        selectedLeader = ls.length - 1
        selectedSeg = 0
        bump()
    }

    function stripLeaders(n) {
        if (!n || isDraw(n))
            return
        n.leaders = []
        n.spines = []
        n.from = undefined
        n.to = undefined
    }

    function deleteLeader() {
        var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
        if (!ids.length && _ctx && _ctx.nodeId)
            ids = [_ctx.nodeId]
        var i
        var any = false
        for (i = 0; i < ids.length; i++) {
            var n = nodeAt(ids[i])
            if (!n || isDraw(n))
                continue
            var ls = ensureLeaders(n)
            if (!ls.length) {
                stripLeaders(n)
                any = true
                continue
            }
            if (ids.length > 1) {
                stripLeaders(n)
                any = true
                continue
            }
            var li = selectedLeader
            if (li < 0 || li >= ls.length)
                li = 0
            ls.splice(li, 1)
            n.leaders = ls
            if (ls.length) {
                selectedLeader = Math.min(li, ls.length - 1)
                var L = ls[selectedLeader]
                n.spines = L.spines || []
                n.from = L.from
                n.to = L.to
            } else {
                stripLeaders(n)
                selectedLeader = 0
                selectedSpine = -1
            }
            any = true
        }
        if (any)
            bump()
    }

    function groupAlignH(n) {
        var a = n && n.alignH ? String(n.alignH) : "left"
        if (a === "center" || a === "right" || a === "free")
            return a
        return "left"
    }

    function setAlignH(mode) {
        var n = nodeAt(selectedId)
        if (!isGroup(n))
            return
        if (mode === "free")
            bakeAlignToFree(n)
        else
            n.alignH = (mode === "left" || mode === "right") ? mode : "center"
        bump()
    }

    function bakeAlignToFree(n) {
        if (!isGroup(n) || groupAlignH(n) === "free")
            return
        var mem = n.members || []
        var ew = Math.max(1, spaceRect().w)
        var eh = Math.max(1, spaceRect().h)
        for (var i = 0; i < mem.length; i++) {
            mem[i].ox = memberLocalX(n, mem[i]) / ew
            mem[i].oy = memberLocalY(n, mem[i]) / eh
        }
        n.alignH = "free"
    }

    function memberIndexOf(n, mem) {
        var mems = (n && n.members) ? n.members : []
        for (var i = 0; i < mems.length; i++) {
            if (mems[i] === mem)
                return i
        }
        return 0
    }

    function stackPitch(n) {
        return chipH(n) + 2
    }

    function memberLocalX(n, mem) {
        var a = groupAlignH(n)
        if (!themeLayout(n) && a === "center") {
            var w = chipWGuess(n, mem)
            return Math.max(0, (groupSpanW(n) - w) * 0.5)
        }
        if (!themeLayout(n) && a === "right") {
            var wr = chipWGuess(n, mem)
            return Math.max(0, groupSpanW(n) - wr)
        }
        if (!themeLayout(n) && a === "left")
            return 0
        return memberHomeX(n, mem) - groupMinX(n)
    }

    function memberLocalY(n, mem) {
        if (!themeLayout(n) && groupAlignH(n) !== "free")
            return captionH(n) + memberIndexOf(n, mem) * stackPitch(n)
        return memberHomeY(n, mem) - groupMinY(n)
    }

    function memberHomeX(n, mem) {
        if (themeLayout(n)) {
            var g = themeGeom(n)
            var r = fiveWayRole(mem)
            return (g[r] || g.center).x + (mem.offX || 0) * Math.max(1, spaceRect().w)
        }
        var ew = Math.max(1, spaceRect().w)
        var a = groupAlignH(n)
        var w = chipWGuess(n, mem)
        if (a === "center" || a === "right" || a === "left")
            return 0
        return (mem.ox || 0) * ew
    }

    function memberHomeY(n, mem) {
        var cap = captionH(n)
        if (themeLayout(n)) {
            var g = themeGeom(n)
            var r = fiveWayRole(mem)
            return (g[r] || g.center).y + (mem.offY || 0) * Math.max(1, spaceRect().h)
        }
        if (groupAlignH(n) !== "free")
            return cap + memberIndexOf(n, mem) * stackPitch(n)
        return (mem.oy || 0) * Math.max(1, spaceRect().h)
    }

    function groupMinX(n) {
        var mem = (n && n.members) ? n.members : []
        if (!mem.length)
            return 0
        if (themeLayout(n) || groupAlignH(n) === "free") {
            var minx = 1e9
            var i
            for (i = 0; i < mem.length; i++)
                minx = Math.min(minx, memberHomeX(n, mem[i]))
            return minx < 1e8 ? minx : 0
        }
        return 0
    }

    function groupMinY(n) {
        var mem = (n && n.members) ? n.members : []
        if (!mem.length)
            return 0
        if (themeLayout(n) || groupAlignH(n) === "free") {
            var miny = 1e9
            var i
            for (i = 0; i < mem.length; i++)
                miny = Math.min(miny, memberHomeY(n, mem[i]))
            return miny < 1e8 ? miny : 0
        }
        return 0
    }

    function groupSpanW(n) {
        var mem = (n && n.members) ? n.members : []
        if (!mem.length)
            return 40
        if (groupAlignH(n) !== "free" && !themeLayout(n)) {
            var maxw = 8
            var i
            for (i = 0; i < mem.length; i++)
                maxw = Math.max(maxw, chipWGuess(n, mem[i]))
            return maxw
        }
        var minx = groupMinX(n)
        var maxx = minx
        var j
        for (j = 0; j < mem.length; j++)
            maxx = Math.max(maxx, memberHomeX(n, mem[j]) + chipWGuess(n, mem[j]))
        return Math.max(8, maxx - minx)
    }

    function groupSpanH(n) {
        var mem = (n && n.members) ? n.members : []
        if (!mem.length)
            return 20
        if (groupAlignH(n) !== "free" && !themeLayout(n))
            return Math.max(8, captionH(n) + mem.length * stackPitch(n) - 2)
        var miny = groupMinY(n)
        var maxy = miny
        var i
        for (i = 0; i < mem.length; i++)
            maxy = Math.max(maxy, memberHomeY(n, mem[i]) + chipH(n, mem[i]))
        return Math.max(8, maxy - miny)
    }

    function chipH(n, mem) {
        var sz = styleVal(n, mem, "chipSize", 18)
        var fs = styleVal(n, mem, "fontSize", 10)
        return uiPx(Math.max(sz, fs + 8))
    }

    function chipR(n, h, mem) {
        return styleVal(n, mem, "chipShape", "round") === "square" ? 0 : Math.max(2, h * 0.5)
    }

    function chipIsHollow(n, mem) {
        return styleVal(n, mem, "chipFill", "filled") === "hollow"
    }

    function hotSz(n) {
        return uiPx((n && n.hotSize) ? n.hotSize : 9)
    }

    function showLeaderHandles(n, li) {
        if (!interactive || !n || !isSelected(n.id))
            return false
        if (dragKind === "spine" && (dragLeader === li || selectedLeader === li))
            return true
        if (dragKind === "from" || dragKind === "to")
            return selectedLeader === li
        if (selectedLeader !== li)
            return false
        return selectedSpine >= 0 || selectedSeg >= 0
    }

    function drawMark(ctx, x, y, size, shape, fill, color) {
        var r = Math.max(2, size * 0.5)
        ctx.beginPath()
        if (shape === "square")
            ctx.rect(x - r, y - r, r * 2, r * 2)
        else
            ctx.arc(x, y, r, 0, 6.2832)
        if (fill === "hollow") {
            ctx.strokeStyle = color
            ctx.lineWidth = 2
            ctx.stroke()
        } else {
            ctx.fillStyle = color
            ctx.fill()
        }
    }

    function nearestPin(item, mx, my) {
        if (!item)
            return "right"
        var p = item.mapFromItem(_ed, mx, my)
        var dl = Math.abs(p.x)
        var dr = Math.abs(item.width - p.x)
        var dt = Math.abs(p.y)
        var db = Math.abs(item.height - p.y)
        var m = Math.min(dl, dr, dt, db)
        if (m === dt) return "top"
        if (m === db) return "bottom"
        if (m === dl) return "left"
        return "right"
    }

    function attachNear(x, y) {
        var list = nodes || []
        var best = { type: "free", fx: xToFx(x), fy: yToFy(y) }
        var bestD = 16
        var i
        for (i = 0; i < list.length; i++) {
            var h = hotPt(list[i])
            var hd = Math.hypot(x - h.x, y - h.y)
            var lim = hotSz(list[i]) * 0.5 + 10
            if (hd < lim && hd < bestD) {
                bestD = hd
                best = { type: "hot", id: list[i].id }
            }
        }
        for (i = 0; i < list.length; i++) {
            var it = _chips.itemAt(i)
            if (!it)
                continue
            var p = it.mapFromItem(_ed, x, y)
            var dx = p.x < 0 ? -p.x : (p.x > it.width ? p.x - it.width : 0)
            var dy = p.y < 0 ? -p.y : (p.y > it.height ? p.y - it.height : 0)
            var cd = Math.hypot(dx, dy)
            if (cd < 14 && cd < bestD) {
                bestD = cd
                best = { type: "chip", id: list[i].id, pin: nearestPin(it, x, y) }
            }
        }
        return best
    }

    function detachEnd(which) {
        var n = nodeAt(selectedId)
        if (!n) return
        var L = currentLeader(n)
        if (!L)
            return
        var p = endPt(which === "to" ? L.to : L.from)
        var free = { type: "free", fx: xToFx(p.x), fy: yToFy(p.y) }
        if (which === "to") L.to = free
        else L.from = free
        if (selectedLeader === 0) {
            if (which === "to") n.to = free
            else n.from = free
        }
        bump()
    }

    function attachEndToSelf(which) {
        var n = nodeAt(selectedId)
        if (!n) return
        var L = currentLeader(n)
        if (!L)
            return
        if (which === "to") L.to = { type: "hot", id: n.id }
        else L.from = { type: "chip", id: n.id, pin: n.pin || "right" }
        if (selectedLeader === 0) {
            n.to = L.to
            n.from = L.from
        }
        bump()
    }

    function _clampPt(pts, i) {
        if (i < 0) return pts[0]
        if (i >= pts.length) return pts[pts.length - 1]
        return pts[i]
    }

    function _bezierCtrl(pts, i) {
        var p0 = _clampPt(pts, i - 1)
        var p1 = pts[i]
        var p2 = pts[i + 1]
        var p3 = _clampPt(pts, i + 2)
        return {
            c1x: p1.x + (p2.x - p0.x) / 6.0,
            c1y: p1.y + (p2.y - p0.y) / 6.0,
            c2x: p2.x - (p3.x - p1.x) / 6.0,
            c2y: p2.y - (p3.y - p1.y) / 6.0,
            x: p2.x,
            y: p2.y
        }
    }

    function strokeLeader(ctx, n, pts, L) {
        if (!pts || pts.length < 2) return
        if (!L)
            L = leaderList(n)[0]
        ctx.beginPath()
        ctx.moveTo(pts[0].x, pts[0].y)
        for (var j = 0; j < pts.length - 1; j++) {
            if (pts.length > 2 && segIsCurve(L, j)) {
                var c = _bezierCtrl(pts, j)
                ctx.bezierCurveTo(c.c1x, c.c1y, c.c2x, c.c2y, c.x, c.y)
            } else {
                ctx.lineTo(pts[j + 1].x, pts[j + 1].y)
            }
        }
        ctx.stroke()
    }

    function ensureMidSpine(n) {
        if (!n || n.kind === "draw")
            return
        if (n.spines && n.spines.length) {
            return
        }
        var L = currentLeader(n)
        if (!L)
            return
        var a = endPt(L.from)
        var b = endPt(L.to)
        if (L.spines && L.spines.length)
            return
        L.spines = [{ fx: xToFx((a.x + b.x) * 0.5), fy: yToFy((a.y + b.y) * 0.5), curve: L.curve !== false }]
        n.spines = L.spines
    }

    function addCurveSpine(n) {
        if (!n) return
        var L = currentLeader(n)
        if (!L)
            return
        L.curve = true
        var a = endPt(L.from)
        var b = endPt(L.to)
        var spines = L.spines || []
        if (spines.length) {
            a = Qt.point(fxToX(spines[spines.length - 1].fx), fyToY(spines[spines.length - 1].fy))
        }
        var dx = b.x - a.x
        var dy = b.y - a.y
        var len = Math.hypot(dx, dy) || 1
        var ox = -dy / len * 36
        var oy = dx / len * 36
        var mx = (a.x + b.x) * 0.5
        var my = (a.y + b.y) * 0.5
        var cx = width * 0.5
        var cy = height * 0.5
        var dPos = Math.hypot(mx + ox - cx, my + oy - cy)
        var dNeg = Math.hypot(mx - ox - cx, my - oy - cy)
        if (dPos > dNeg) {
            ox = -ox
            oy = -oy
        }
        if (!L.spines) L.spines = []
        L.spines.push({ fx: xToFx(mx + ox), fy: yToFy(my + oy), curve: true })
        n.spines = L.spines
        selectedId = n.id
        selectedSpine = L.spines.length - 1
        selectedLeader = Math.max(0, selectedLeader)
        selectedChanged()
        bump()
    }

    function hitTest(mx, my) {
        var list = nodes || []
        var i
        var n
        for (i = 0; i < list.length; i++) {
            n = list[i]
            if (isPinnable(n) && hitOverlayPin(n, mx, my))
                return { kind: "overlayPin", id: n.id, spine: -1 }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            if (!isGroup(n))
                continue
            var mi0 = memberHit(n, mx, my)
            if (mi0 < 0)
                continue
            if (groupEditId === n.id)
                return { kind: "member", id: n.id, spine: -1, member: mi0 }
            return { kind: "chip", id: n.id, spine: -1 }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            if (n.kind === "draw")
                continue
            var ls = leaderList(n)
            for (var li = 0; li < ls.length; li++) {
                var fp = endPt(ls[li].from)
                if (Math.hypot(mx - fp.x, my - fp.y) < 9) {
                    return { kind: "from", id: n.id, spine: -1, leader: li }
                }
            }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            var ls2 = leaderList(n)
            for (var lj = 0; lj < ls2.length; lj++) {
                var te = ls2[lj].to || { type: "hot", id: n.id }
                var tp = endPt(te)
                if (te.type !== "hot" && Math.hypot(mx - tp.x, my - tp.y) < 9) {
                    return { kind: "to", id: n.id, spine: -1, leader: lj }
                }
            }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            if (n.kind === "draw")
                continue
            var h = hotPt(n)
            if (Math.hypot(mx - h.x, my - h.y) < (hotSz(n) * 0.5 + 5)) {
                return { kind: "hot", id: n.id, spine: -1 }
            }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            var lss = leaderList(n)
            for (var lk = 0; lk < lss.length; lk++) {
                if (!showLeaderHandles(n, lk))
                    continue
                var spines = lss[lk].spines || []
                for (var s = 0; s < spines.length; s++) {
                    var sx = fxToX(spines[s].fx)
                    var sy = fyToY(spines[s].fy)
                    if (Math.hypot(mx - sx, my - sy) < 9) {
                        return { kind: "spine", id: n.id, spine: s, leader: lk }
                    }
                }
            }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            if (isGroup(n) && groupEditId === n.id) {
                var mi = memberHit(n, mx, my)
                if (mi >= 0)
                    return { kind: "member", id: n.id, spine: -1, member: mi }
            }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            if (isDraw(n))
                continue
            if (isGroup(n) && memberHit(n, mx, my) >= 0)
                return { kind: "chip", id: n.id, spine: -1 }
            var it = _chips.itemAt(i)
            if (!it) {
                continue
            }
            var p = it.mapFromItem(_ed, mx, my)
            if (p.x >= 0 && p.y >= 0 && p.x <= it.width && p.y <= it.height) {
                return { kind: "chip", id: list[i].id, spine: -1 }
            }
        }
        for (i = 0; i < list.length; i++) {
            n = list[i]
            if (!isDraw(n))
                continue
            var dh = hitDraw(n, mx, my)
            if (dh)
                return { kind: "draw", id: n.id, spine: -1, handle: dh }
        }
        for (i = 0; i < list.length; i++) {
            var seg = _nearLeader(list[i], mx, my)
            if (seg && seg.seg >= 0) {
                return { kind: "line", id: list[i].id, spine: -1, leader: seg.leader, seg: seg.seg }
            }
        }
        return { kind: "", id: "", spine: -1 }
    }

    function _nearLeader(n, mx, my) {
        var ls = leaderList(n)
        var best = { leader: -1, seg: -1 }
        var bestD = 6
        var li
        for (li = 0; li < ls.length; li++) {
            var L = ls[li]
            var pts = pathPtsL(L)
            if (pts.length < 2)
                continue
            for (var j = 0; j < pts.length - 1; j++) {
                var d
                if (pts.length > 2 && segIsCurve(L, j)) {
                    d = _distBezier(mx, my, pts, j)
                } else {
                    d = _distSeg(mx, my, pts[j].x, pts[j].y, pts[j + 1].x, pts[j + 1].y)
                }
                if (d < bestD) {
                    bestD = d
                    best = { leader: li, seg: j }
                }
            }
        }
        return best
    }

    function _distBezier(mx, my, pts, j) {
        var c = _bezierCtrl(pts, j)
        var p1x = pts[j].x
        var p1y = pts[j].y
        var prevx = p1x
        var prevy = p1y
        var best = 1e9
        var steps = 8
        for (var s = 1; s <= steps; s++) {
            var tt = s / steps
            var u = 1 - tt
            var x = u*u*u*p1x + 3*u*u*tt*c.c1x + 3*u*tt*tt*c.c2x + tt*tt*tt*c.x
            var y = u*u*u*p1y + 3*u*u*tt*c.c1y + 3*u*tt*tt*c.c2y + tt*tt*tt*c.y
            var d = _distSeg(mx, my, prevx, prevy, x, y)
            if (d < best)
                best = d
            prevx = x
            prevy = y
        }
        return best
    }

    function _distSeg(px, py, x1, y1, x2, y2) {
        var dx = x2 - x1
        var dy = y2 - y1
        var len = dx * dx + dy * dy
        if (len < 1) {
            return Math.hypot(px - x1, py - y1)
        }
        var t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / len))
        return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
    }

    function clearAllSpines(id) {
        var n = nodeAt(id || selectedId)
        if (!n || isDraw(n))
            return
        var ls = ensureLeaders(n)
        var i
        for (i = 0; i < ls.length; i++)
            ls[i].spines = []
        n.spines = []
        selectedSpine = -1
        bump()
    }

    function addSpineAt(id, mx, my, forceCurve) {
        var n = nodeAt(id)
        if (!n) {
            return -1
        }
        if (!n.spines) {
            n.spines = []
        }
        var L = currentLeader(n)
        if (!L)
            return -1
        if (!L.spines)
            L.spines = []
        var pts = pathPtsL(L)
        var best = 0
        var bestD = 1e9
        for (var i = 0; i < pts.length - 1; i++) {
            var d = _distSeg(mx, my, pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y)
            if (d < bestD) {
                bestD = d
                best = i
            }
        }
        var spn = snapPos(mx, my, false)
        var curved = (forceCurve === true) ? true : segIsCurve(L, best)
        L.spines.splice(best, 0, { fx: xToFx(spn.x), fy: yToFy(spn.y), curve: curved })
        n.spines = L.spines
        selectedId = id
        selectedSpine = best
        selectedChanged()
        bump()
        return best
    }

    function deleteSpineAt(id, leader, index) {
        var n = nodeAt(id)
        if (!n || index === undefined || index < 0)
            return false
        selectedId = id
        if (leader !== undefined)
            selectedLeader = leader
        var L = currentLeader(n)
        if (!L || !L.spines || index >= L.spines.length)
            return false
        L.spines.splice(index, 1)
        n.spines = L.spines
        selectedSpine = -1
        bump()
        return true
    }

    function deleteSelection() {
        var n = nodeAt(selectedId)
        if (!n)
            return
        var L = currentLeader(n)
        if (!L)
            return
        if (selectedSpine >= 0 && L.spines && selectedSpine < L.spines.length) {
            L.spines.splice(selectedSpine, 1)
            n.spines = L.spines
            selectedSpine = -1
            bump()
        }
    }

    function deleteChip(id) {
        var nid = id || selectedId
        var n = nodeAt(nid)
        if (!n || isGroup(n))
            return false
        var idx = nodeIndex(nid)
        if (idx < 0)
            return false
        if (tableIsPacked(n))
            detachTablePacked(n)
        else
            detachChipFromTable(n)
        var list = nodes || []
        list.splice(idx, 1)
        var keep = []
        var s = selectedIds || []
        for (var i = 0; i < s.length; i++) {
            if (s[i] !== nid)
                keep.push(s[i])
        }
        groupEditId = ""
        selectedMember = -1
        setSelection(keep)
        bump()
        return true
    }

    function isDraw(n) {
        return !!(n && n.kind === "draw")
    }

    function isTable(n) {
        return !!(n && n.kind === "draw" && n.shape === "table")
    }

    function isText(n) {
        return !!(n && n.kind === "draw" && n.shape === "text")
    }

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

    function isOverlay(n) {
        return !!(n && n.kind === "draw" && n.shape === "image")
    }

    function isPinnable(n) {
        return isOverlay(n) || isTable(n) || isText(n)
    }

    function emptyTableRow(cols) {
        var row = { cells: [] }
        var i
        var count = Math.max(1, cols || 2)
        for (i = 0; i < count; i++)
            row.cells.push({ text: "" })
        return row
    }

    function ensureTable(n) {
        if (!isTable(n))
            return
        var cols = (n.cols > 0) ? n.cols : 2
        n.cols = cols
        if (!n.theme || !String(n.theme).length)
            n.theme = "gremlin"
        if (n.idCol === undefined || n.idCol === null)
            n.idCol = false
        if (!n.fontSize)
            n.fontSize = 10
        if (!n.extras)
            n.extras = []
        if (!n.rows || !n.rows.length)
            n.rows = [emptyTableRow(cols)]
        var r
        for (r = 0; r < n.rows.length; r++) {
            if (!n.rows[r])
                n.rows[r] = emptyTableRow(cols)
            if (!n.rows[r].cells)
                n.rows[r].cells = []
            while (n.rows[r].cells.length < cols)
                n.rows[r].cells.push({ text: "" })
            if (n.rows[r].cells.length > cols)
                n.rows[r].cells = n.rows[r].cells.slice(0, cols)
        }
    }

    function tableMinW(n) {
        return 8
    }

    function tableMinH(n) {
        return 8
    }

    function tableHomeRect(n, row, col) {
        var g = drawGeom(n)
        ensureTable(n)
        var rows = n.rows.length
        var cols = n.cols
        var idCol = !!n.idCol && cols > 1
        var idW = idCol ? Math.min(g.w * 0.32, Math.max(22, g.w * 0.22)) : 0
        var rest = Math.max(1, g.w - idW)
        var other = Math.max(1, idCol ? cols - 1 : cols)
        var colW = rest / other
        var rowH = g.h / Math.max(1, rows)
        var x = g.x
        var w = colW
        if (idCol) {
            if (col <= 0) {
                x = g.x
                w = idW
            } else {
                x = g.x + idW + (col - 1) * colW
                w = colW
            }
        } else {
            w = g.w / Math.max(1, cols)
            x = g.x + col * w
        }
        return { x: x, y: g.y + row * rowH, w: Math.max(8, w), h: Math.max(8, rowH) }
    }

    function tableGetCell(n, row, col) {
        if (!n || !n.rows || row < 0 || col < 0)
            return null
        if (row >= n.rows.length)
            return null
        var cells = n.rows[row].cells || []
        if (col >= cells.length)
            return null
        return cells[col]
    }

    function tableCellIsFree(n, row, col) {
        var c = tableGetCell(n, row, col)
        return !!(c && c.free)
    }

    function tableExtraAt(n, i) {
        if (!n || !n.extras || i < 0 || i >= n.extras.length)
            return null
        return n.extras[i]
    }

    function tablePartWorldRect(n, cell, fallback) {
        if (cell && cell.independent && cell.efw > 0 && cell.efh > 0) {
            return {
                x: fxToX(cell.efx || 0),
                y: fyToY(cell.efy || 0),
                w: fwToW(cell.efw),
                h: fhToH(cell.efh)
            }
        }
        return fallback
    }

    function writeTablePartRect(n, cell, x, y, w, h) {
        if (!cell)
            return
        w = Math.max(8, w)
        h = Math.max(8, h)
        var s = spaceRect()
        var pad = 4
        if (x < s.x + pad) x = s.x + pad
        if (y < s.y + pad) y = s.y + pad
        if (x + w > s.x + s.w - pad) x = Math.max(s.x + pad, s.x + s.w - pad - w)
        if (y + h > s.y + s.h - pad) y = Math.max(s.y + pad, s.y + s.h - pad - h)
        if (cell.independent) {
            cell.efx = xToFx(x)
            cell.efy = yToFy(y)
            cell.efw = w / Math.max(1, s.w)
            cell.efh = h / Math.max(1, s.h)
            return
        }
        var g = drawGeom(n)
        cell.ox = (x - g.x) / Math.max(1, g.w)
        cell.oy = (y - g.y) / Math.max(1, g.h)
        cell.cw = w / Math.max(1, g.w)
        cell.ch = h / Math.max(1, g.h)
    }

    function setTableCellIndependent(on) {
        var n = nodeAt(selectedId)
        if (!isTable(n) || !tableHasTarget())
            return
        var cell = tableCurrentCell(n)
        if (!cell)
            return
        var rc = tableCurrentRect(n)
        if (on) {
            cell.independent = true
            cell.free = true
            writeTablePartRect(n, cell, rc.x, rc.y, rc.w, rc.h)
        } else {
            cell.independent = false
            delete cell.efx
            delete cell.efy
            delete cell.efw
            delete cell.efh
            writeTablePartRect(n, cell, rc.x, rc.y, rc.w, rc.h)
        }
        bump()
    }

    function tableCellHandlesOn(n) {
        if (!interactive || !isTable(n) || isLocked(n) || !isSelected(n.id))
            return false
        if (tableExtra >= 0)
            return true
        var c = tableGetCell(n, tableRow, tableCol)
        return !!(c && c.free)
    }

    function tableExtraRect(n, i) {
        var e = tableExtraAt(n, i)
        var g = drawGeom(n)
        if (!e)
            return { x: g.x, y: g.y, w: 16, h: 16 }
        var follow = {
            x: g.x + (e.ox || 0) * g.w,
            y: g.y + (e.oy || 0) * g.h,
            w: Math.max(8, (e.cw > 0) ? e.cw * g.w : 16),
            h: Math.max(8, (e.ch > 0) ? e.ch * g.h : 16)
        }
        return tablePartWorldRect(n, e, follow)
    }

    function tableCurrentCell(n) {
        if (!n)
            return null
        if (tableExtra >= 0)
            return tableExtraAt(n, tableExtra)
        return tableGetCell(n, tableRow, tableCol)
    }

    function tableHasTarget() {
        return tableExtra >= 0 || (tableRow >= 0 && tableCol >= 0)
    }

    function tableCurrentRect(n) {
        if (tableExtra >= 0)
            return tableExtraRect(n, tableExtra)
        if (tableRow >= 0 && tableCol >= 0)
            return tableCellRect(n, tableRow, tableCol)
        return drawGeom(n)
    }

    function tableCellRect(n, row, col) {
        var home = tableHomeRect(n, row, col)
        var c = tableGetCell(n, row, col)
        if (!c || !c.free)
            return home
        var g = drawGeom(n)
        var follow = {
            x: g.x + (c.ox || 0) * g.w,
            y: g.y + (c.oy || 0) * g.h,
            w: Math.max(8, (c.cw > 0) ? c.cw * g.w : home.w),
            h: Math.max(8, (c.ch > 0) ? c.ch * g.h : home.h)
        }
        return tablePartWorldRect(n, c, follow)
    }

    function tableCellAt(n, mx, my) {
        if (!isTable(n))
            return { row: -1, col: -1, extra: -1 }
        ensureTable(n)
        var extras = n.extras || []
        var ei
        for (ei = extras.length - 1; ei >= 0; ei--) {
            var er = tableExtraRect(n, ei)
            if (mx >= er.x - 8 && mx <= er.x + er.w + 8 && my >= er.y - 8 && my <= er.y + er.h + 8)
                return { row: -1, col: -1, extra: ei }
        }
        var rows = n.rows.length
        var cols = n.cols
        var r
        var c
        for (r = rows - 1; r >= 0; r--) {
            for (c = cols - 1; c >= 0; c--) {
                if (!tableCellIsFree(n, r, c))
                    continue
                var rc = tableCellRect(n, r, c)
                if (mx >= rc.x && mx <= rc.x + rc.w && my >= rc.y && my <= rc.y + rc.h)
                    return { row: r, col: c, extra: -1 }
            }
        }
        var g = drawGeom(n)
        if (mx < g.x || my < g.y || mx > g.x + g.w || my > g.y + g.h)
            return { row: -1, col: -1, extra: -1 }
        var row = Math.floor((my - g.y) / Math.max(1, g.h / Math.max(1, rows)))
        var idCol = !!n.idCol && cols > 1
        var idW = idCol ? Math.min(g.w * 0.32, Math.max(22, g.w * 0.22)) : 0
        var lx = mx - g.x
        var col = 0
        if (idCol) {
            if (lx < idW)
                col = 0
            else
                col = 1 + Math.floor((lx - idW) / Math.max(1, (g.w - idW) / Math.max(1, cols - 1)))
        } else {
            col = Math.floor(lx / Math.max(1, g.w / Math.max(1, cols)))
        }
        if (row < 0) row = 0
        if (col < 0) col = 0
        if (row > rows - 1) row = rows - 1
        if (col > cols - 1) col = cols - 1
        return { row: row, col: col, extra: -1 }
    }

    function setTableCellFree(on) {
        var n = nodeAt(selectedId)
        if (!isTable(n) || !tableHasTarget())
            return
        ensureTable(n)
        var cell = tableCurrentCell(n)
        if (!cell)
            return
        var g = drawGeom(n)
        if (on) {
            if (!cell.free) {
                if (tableExtra >= 0) {
                    if (!(cell.cw > 0)) cell.cw = 0.4
                    if (!(cell.ch > 0)) cell.ch = 0.4
                } else {
                    var home = tableHomeRect(n, tableRow, tableCol)
                    cell.ox = (home.x - g.x) / Math.max(1, g.w)
                    cell.oy = (home.y - g.y) / Math.max(1, g.h)
                    cell.cw = home.w / Math.max(1, g.w)
                    cell.ch = home.h / Math.max(1, g.h)
                }
            }
            cell.free = true
        } else {
            cell.free = false
            cell.ox = 0
            cell.oy = 0
            if (tableExtra < 0) {
                delete cell.cw
                delete cell.ch
            }
        }
        bump()
    }

    function toggleTableCellFree() {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        var cell = tableCurrentCell(n)
        setTableCellFree(!(cell && cell.free))
    }

    function placeTableCell(where) {
        var n = nodeAt(selectedId)
        if (!isTable(n) || !tableHasTarget())
            return
        ensureTable(n)
        setTableCellFree(true)
        var cell = tableCurrentCell(n)
        if (!cell)
            return
        var rc = tableCurrentRect(n)
        var g = drawGeom(n)
        var x = rc.x
        var y = rc.y
        if (where === "left")
            x = g.x
        else if (where === "right")
            x = g.x + g.w - rc.w
        else if (where === "center")
            x = g.x + (g.w - rc.w) * 0.5
        else if (where === "top")
            y = g.y
        else if (where === "bottom")
            y = g.y + g.h - rc.h
        else if (where === "middle")
            y = g.y + (g.h - rc.h) * 0.5
        writeTablePartRect(n, cell, x, y, rc.w, rc.h)
        bump()
    }

    function spawnEmptyCell() {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        ensureTable(n)
        var g = drawGeom(n)
        var src = tableCurrentRect(n)
        var cw = src.w / Math.max(1, g.w)
        var ch = src.h / Math.max(1, g.h)
        if (!(cw > 0)) cw = 0.4
        if (!(ch > 0)) ch = 0.4
        var ox = (src.x - g.x) / Math.max(1, g.w) + 12 / Math.max(1, g.w)
        var oy = (src.y - g.y) / Math.max(1, g.h) + 12 / Math.max(1, g.h)
        if (!n.extras)
            n.extras = []
        n.extras.push({
            text: "",
            free: true,
            independent: true,
            ox: ox,
            oy: oy,
            cw: cw,
            ch: ch,
            efx: xToFx(src.x + 12),
            efy: yToFy(src.y + 12),
            efw: src.w / Math.max(1, spaceRect().w),
            efh: src.h / Math.max(1, spaceRect().h)
        })
        tableExtra = n.extras.length - 1
        tableRow = -1
        tableCol = -1
        bump()
    }

    function deleteThisTableCell() {
        var n = nodeAt(selectedId)
        if (!isTable(n) || tableExtra < 0)
            return
        ensureTable(n)
        if (!n.extras || tableExtra >= n.extras.length)
            return
        n.extras.splice(tableExtra, 1)
        tableExtra = Math.min(tableExtra, n.extras.length - 1)
        bump()
    }

    function tableCellStyle(n, col) {
        var theme = (n && n.theme) ? String(n.theme) : "gremlin"
        var idCell = !!(n && n.idCol && col === 0)
        if (theme === "hollow")
            return { fill: "transparent", border: "#3F3F46", text: "#E4E4E7" }
        if (theme === "sheet") {
            if (idCell)
                return { fill: "#18181B", border: "#18181B", text: "#F4F4F5" }
            return { fill: "#E4E4E7", border: "#18181B", text: "#18181B" }
        }
        return { fill: "#18181B", border: "#3F3F46", text: "#E4E4E7" }
    }

    function tableCellText(n, row, col) {
        if (!n || !n.rows || row < 0 || col < 0)
            return ""
        if (row >= n.rows.length)
            return ""
        var cells = n.rows[row].cells || []
        if (col >= cells.length)
            return ""
        return cells[col].text || ""
    }

    function addTableRow(below) {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        ensureTable(n)
        var at = (tableRow >= 0) ? tableRow : n.rows.length - 1
        var row = emptyTableRow(n.cols)
        if (below)
            n.rows.splice(at + 1, 0, row)
        else
            n.rows.splice(Math.max(0, at), 0, row)
        tableRow = below ? at + 1 : Math.max(0, at)
        bump()
    }

    function deleteTableRow() {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        ensureTable(n)
        if (n.rows.length <= 1)
            return
        var at = (tableRow >= 0) ? tableRow : n.rows.length - 1
        n.rows.splice(at, 1)
        tableRow = Math.min(at, n.rows.length - 1)
        bump()
    }

    function addTableCol(right) {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        ensureTable(n)
        var at = (tableCol >= 0) ? tableCol : n.cols - 1
        var insert = right ? at + 1 : Math.max(0, at)
        var r
        for (r = 0; r < n.rows.length; r++) {
            if (!n.rows[r].cells)
                n.rows[r].cells = []
            n.rows[r].cells.splice(insert, 0, { text: "" })
        }
        n.cols = n.cols + 1
        tableCol = insert
        bump()
    }

    function deleteTableCol() {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        ensureTable(n)
        if (n.cols <= 1)
            return
        var at = (tableCol >= 0) ? tableCol : n.cols - 1
        var r
        for (r = 0; r < n.rows.length; r++) {
            if (n.rows[r].cells)
                n.rows[r].cells.splice(at, 1)
        }
        n.cols = n.cols - 1
        tableCol = Math.min(at, n.cols - 1)
        bump()
    }

    function toggleTableIdCol() {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        ensureTable(n)
        n.idCol = !n.idCol
        bump()
    }

    function setTableTheme(name) {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        n.theme = name || "gremlin"
        bump()
    }

    function setTableFont(sz) {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        n.fontSize = sz
        bump()
    }

    function deleteTable() {
        var n = nodeAt(selectedId)
        if (!isTable(n))
            return
        deleteChip(n.id)
    }

    function beginTableRename(id, row, col, extra) {
        var n = nodeAt(id)
        if (!isTable(n))
            return
        ensureTable(n)
        renameId = id
        renameMember = -1
        tableRow = row
        tableCol = col
        tableExtra = (extra !== undefined && extra !== null) ? extra : -1
        if (tableExtra >= 0) {
            var ex = tableExtraAt(n, tableExtra)
            renameDraft = ex && ex.text ? ex.text : ""
        } else {
            renameDraft = tableCellText(n, row, col)
        }
        dragKind = ""
        Qt.callLater(function () {
            if (_nameEdit) {
                _nameEdit.forceActiveFocus()
                _nameEdit.selectAll()
            }
        })
        bump()
    }

    function isLocked(n) {
        return !!(n && (n.pinned || n.locked))
    }

    function pinLocal() {
        return { x: -2, y: -18, w: 16, h: 16 }
    }

    function hitOverlayPin(n, mx, my) {
        if (!isPinnable(n) || !interactive)
            return false
        var i = nodeIndex(n.id)
        var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
        if (!it)
            return false
        var p = it.mapFromItem(_ed, mx, my)
        var r = pinLocal()
        return p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h
    }

    function overlayContains(n, mx, my) {
        if (!isPinnable(n))
            return false
        if (hitOverlayPin(n, mx, my))
            return true
        var i = nodeIndex(n.id)
        var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
        if (!it)
            return false
        var p = it.mapFromItem(_ed, mx, my)
        return p.x >= 0 && p.y >= 0 && p.x <= it.width && p.y <= it.height
    }

    function setOverlayHover(mx, my) {
        var list = nodes || []
        var id = ""
        var i
        for (i = list.length - 1; i >= 0; i--) {
            if (overlayContains(list[i], mx, my)) {
                id = list[i].id
                break
            }
        }
        if (overlayHoverId === id)
            return
        overlayHoverId = id
        bump()
    }

    function addOverlay(rel, fileUrl) {
        var st = _drawStyle()
        st.id = _uid("d")
        st.shape = "image"
        st.src = rel || ""
        st.srcUrl = fileUrl || ""
        st.locked = false
        st.pinned = false
        st.sockets = []
        st.zLayer = 2
        st.fill = "filled"
        st.fx = 0.36
        st.fy = 0.28
        st.fw = 0.28
        st.fh = 0.28
        st.rot = 0
        st.opacity = 1
        nodes.push(st)
        setSelection([st.id])
        bump()
        return st.id
    }

    function pinTarget(id) {
        var n = nodeAt(id || selectedId)
        if (isDraw(n))
            return n
        var ids = selectedIds || []
        var i
        for (i = 0; i < ids.length; i++) {
            var q = nodeAt(ids[i])
            if (isTable(q))
                return q
        }
        return null
    }

    function toggleLock(id) {
        var n = pinTarget(id)
        if (!isDraw(n))
            return
        var on = !isLocked(n)
        n.pinned = on
        n.locked = on
        plantSnap = false
        bump()
    }

    function beginPlantSnap() {
        var n = nodeAt(selectedId)
        if (!isOverlay(n))
            return
        plantSnap = true
        bump()
    }

    function addSocketAt(n, mx, my) {
        if (!isOverlay(n))
            return
        var g = drawGeom(n)
        var lx = mx
        var ly = my
        var rot = n.rot || 0
        if (rot) {
            var cx = g.x + g.w * 0.5
            var cy = g.y + g.h * 0.5
            var rad = -rot * Math.PI / 180
            var dx = mx - cx
            var dy = my - cy
            var c = Math.cos(rad)
            var s = Math.sin(rad)
            lx = cx + dx * c - dy * s
            ly = cy + dx * s + dy * c
        }
        var ux = (lx - g.x) / Math.max(1, g.w)
        var uy = (ly - g.y) / Math.max(1, g.h)
        ux = Math.max(0, Math.min(1, ux))
        uy = Math.max(0, Math.min(1, uy))
        if (!n.sockets)
            n.sockets = []
        n.sockets.push({ id: _uid("s"), ux: ux, uy: uy, chipId: "" })
        plantSnap = false
        bump()
    }

    function socketWorld(n, sock) {
        var g = drawGeom(n)
        var lx = g.x + (sock.ux || 0) * g.w
        var ly = g.y + (sock.uy || 0) * g.h
        var rot = n.rot || 0
        if (!rot)
            return Qt.point(lx, ly)
        var cx = g.x + g.w * 0.5
        var cy = g.y + g.h * 0.5
        var rad = rot * Math.PI / 180
        var dx = lx - cx
        var dy = ly - cy
        var c = Math.cos(rad)
        var s = Math.sin(rad)
        return Qt.point(cx + dx * c - dy * s, cy + dx * s + dy * c)
    }

    function syncOverlayChips(n) {
        if (!n || !n.sockets)
            return
        var i
        for (i = 0; i < n.sockets.length; i++) {
            var sock = n.sockets[i]
            if (!sock || !sock.chipId)
                continue
            var q = nodeAt(sock.chipId)
            if (!q || isDraw(q)) {
                sock.chipId = ""
                continue
            }
            var pt = socketWorld(n, sock)
            var bw = chipBounds(q)
            q.chipFx = xToFx(pt.x - bw.w * 0.5)
            q.chipFy = yToFy(pt.y - bw.h * 0.5)
        }
    }

    function unsnapChip(chipId) {
        var list = nodes || []
        var i, j
        for (i = 0; i < list.length; i++) {
            var ov = list[i]
            if (!ov.sockets)
                continue
            for (j = 0; j < ov.sockets.length; j++) {
                if (ov.sockets[j].chipId === chipId)
                    ov.sockets[j].chipId = ""
            }
        }
    }

    function snapChipToSocket(chipId, mx, my) {
        if (!chipId)
            return false
        var list = nodes || []
        var best = null
        var bestD = Style.dp(28)
        var bi = -1
        var i, j
        for (i = 0; i < list.length; i++) {
            var ov = list[i]
            if (!isOverlay(ov) || !ov.sockets)
                continue
            for (j = 0; j < ov.sockets.length; j++) {
                var pt = socketWorld(ov, ov.sockets[j])
                var d = Math.hypot(mx - pt.x, my - pt.y)
                if (d < bestD) {
                    bestD = d
                    best = ov
                    bi = j
                }
            }
        }
        if (!best)
            return false
        unsnapChip(chipId)
        best.sockets[bi].chipId = chipId
        syncOverlayChips(best)
        bump()
        return true
    }

    function clearSockets() {
        var n = nodeAt(selectedId)
        if (!isOverlay(n))
            return
        n.sockets = []
        bump()
    }

    function chipBounds(n) {
        if (!n)
            return { x: 0, y: 0, w: 40, h: 20 }
        var i = nodeIndex(n.id)
        var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
        if (it && it.width > 1)
            return { x: it.x, y: it.y, w: it.width, h: it.height }
        return {
            x: fxToX(n.chipFx || 0),
            y: fyToY(n.chipFy || 0),
            w: 80,
            h: chipH(n)
        }
    }

    function spaceRect() {
        var pw = Math.max(1, worldPageW)
        var ph = Math.max(1, worldPageH)
        var scale = Math.min(width / pw, height / ph)
        var dw = pw * scale
        var dh = ph * scale
        return {
            x: (width - dw) * 0.5,
            y: (height - dh) * 0.5,
            w: dw,
            h: dh
        }
    }

    function innerPageRect() {
        var s = spaceRect()
        return {
            x: s.x + s.w * innerPadX,
            y: s.y + s.h * innerPadY,
            w: s.w * (innerPageW / worldPageW),
            h: s.h * (innerPageH / worldPageH)
        }
    }

    function clamp01(v) {
        return Math.max(0, Math.min(1, v))
    }

    function worldToX(wx) {
        return spaceRect().x + (wx / worldPageW) * spaceRect().w
    }

    function worldToY(wy) {
        return spaceRect().y + (wy / worldPageH) * spaceRect().h
    }

    function xToWorld(px) {
        return (px - spaceRect().x) / Math.max(1, spaceRect().w) * worldPageW
    }

    function yToWorld(py) {
        return (py - spaceRect().y) / Math.max(1, spaceRect().h) * worldPageH
    }

    function fxToX(fx) {
        var s = spaceRect()
        return s.x + (fx || 0) * s.w
    }

    function fyToY(fy) {
        var s = spaceRect()
        return s.y + (fy || 0) * s.h
    }

    function xToFx(px) {
        var s = spaceRect()
        return (px - s.x) / Math.max(1, s.w)
    }

    function yToFy(py) {
        var s = spaceRect()
        return (py - s.y) / Math.max(1, s.h)
    }

    function fwToW(fw) {
        return Math.max(8, (fw || 0) * spaceRect().w)
    }

    function fhToH(fh) {
        return Math.max(8, (fh || 0) * spaceRect().h)
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

    function snapEnt(x, y, altOff) {
        if (altOff)
            return Qt.point(x, y)
        if (!snapEntOn) {
            if (snapOn)
                return snapPos(x, y, false)
            return Qt.point(x, y)
        }
        var xs = []
        var ys = []
        function ax(v) { xs.push(v) }
        function ay(v) { ys.push(v) }
        var list = nodes || []
        var i
        for (i = 0; i < list.length; i++) {
            var nn = list[i]
            if (dragKind && nn.id === selectedId)
                continue
            if (isDraw(nn)) {
                var g = drawGeom(nn)
                ax(g.x); ax(g.x + g.w); ax(g.x + g.w * 0.5)
                ay(g.y); ay(g.y + g.h); ay(g.y + g.h * 0.5)
                continue
            }
            var bb = chipBounds(nn)
            ax(bb.x); ax(bb.x + bb.w); ax(bb.x + bb.w * 0.5)
            ay(bb.y); ay(bb.y + bb.h); ay(bb.y + bb.h * 0.5)
            if (!isDraw(nn)) {
                var hp = hotPt(nn)
                ax(hp.x)
                ay(hp.y)
            }
        }
        function nearest(v, arr) {
            var best = v
            var d = 8
            var j
            for (j = 0; j < arr.length; j++) {
                var dd = Math.abs(v - arr[j])
                if (dd < d) {
                    d = dd
                    best = arr[j]
                }
            }
            if (snapOn) {
                var g2 = (arr === xs) ? worldToX(snapWorld(xToWorld(v))) : worldToY(snapWorld(yToWorld(v)))
                if (Math.abs(g2 - v) <= d)
                    best = g2
            }
            return best
        }
        return Qt.point(nearest(x, xs), nearest(y, ys))
    }

    function applyTableCellResize(n, mx, my, handle, altOff) {
        var cell = tableCurrentCell(n)
        if (!cell)
            return
        cell.free = true
        if (!cell.independent)
            setTableCellIndependent(true)
        cell = tableCurrentCell(n)
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
        var nx = Math.min(x0, x1)
        var ny = Math.min(y0, y1)
        var nw = Math.max(8, Math.abs(x1 - x0))
        var nh = Math.max(8, Math.abs(y1 - y0))
        writeTablePartRect(n, cell, nx, ny, nw, nh)
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

    function nudge(dx, dy) {
        var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
        if (!ids.length)
            return
        var seenPack = {}
        var i
        for (i = 0; i < ids.length; i++) {
            var n = nodeAt(ids[i])
            if (!n)
                continue
            var pack = tablePackOf(n)
            if (pack) {
                if (!seenPack[pack.id]) {
                    seenPack[pack.id] = true
                    moveTablePack(pack, dx, dy)
                }
                continue
            }
            if (isDraw(n)) {
                if (isLocked(n))
                    continue
                var around = n.around || []
                if (around.length) {
                    var ai
                    for (ai = 0; ai < around.length; ai++) {
                        var qn = nodeAt(around[ai])
                        if (!qn || isDraw(qn))
                            continue
                        qn.chipFx = Math.max(0.01, Math.min(0.92, qn.chipFx + dx))
                        qn.chipFy = Math.max(0.01, Math.min(0.92, qn.chipFy + dy))
                    }
                } else {
                    var oldFx = n.fx || 0
                    var oldFy = n.fy || 0
                    n.fx = Math.max(0, Math.min(0.98, oldFx + dx))
                    n.fy = Math.max(0, Math.min(0.98, oldFy + dy))
                    shiftIndependentParts(n, n.fx - oldFx, n.fy - oldFy)
                }
                followTablePacked(n)
            } else {
                n.chipFx = Math.max(0.01, Math.min(0.92, (n.chipFx || 0) + dx))
                n.chipFy = Math.max(0.01, Math.min(0.92, (n.chipFy || 0) + dy))
                refreshChipPack(n)
            }
        }
        bump()
    }

    function _newId(n) {
        if (isDraw(n))
            return _uid("d")
        if (isGroup(n))
            return _uid("g")
        var k = n.kind || "btn"
        return _uid(k === "btn" ? "b" : k.charAt(0))
    }

    function shiftClone(n, dx, dy) {
        if (isDraw(n)) {
            n.fx = (n.fx || 0) + dx
            n.fy = (n.fy || 0) + dy
        } else {
            n.chipFx = Math.max(0.01, Math.min(0.92, (n.chipFx || 0) + dx))
            n.chipFy = Math.max(0.01, Math.min(0.92, (n.chipFy || 0) + dy))
            n.hotFx = Math.max(0, Math.min(1, hotFxOf(n) + dx))
            n.hotFy = Math.max(0, Math.min(1, hotFyOf(n) + dy))
        }
        var ls = n.leaders || []
        var li
        for (li = 0; li < ls.length; li++) {
            var sp = ls[li].spines || []
            var s
            for (s = 0; s < sp.length; s++) {
                sp[s].fx = (sp[s].fx || 0) + dx
                sp[s].fy = (sp[s].fy || 0) + dy
            }
            if (ls[li].from && ls[li].from.type === "free") {
                ls[li].from.fx = (ls[li].from.fx || 0) + dx
                ls[li].from.fy = (ls[li].from.fy || 0) + dy
            }
            if (ls[li].to && ls[li].to.type === "free") {
                ls[li].to.fx = (ls[li].to.fx || 0) + dx
                ls[li].to.fy = (ls[li].to.fy || 0) + dy
            }
        }
    }

    function pasteNodes(src, dx, dy) {
        if (!src || !src.length)
            return
        var map = {}
        var copies = []
        var i
        for (i = 0; i < src.length; i++) {
            var c = JSON.parse(JSON.stringify(src[i]))
            var old = c.id
            c.id = _newId(c)
            map[old] = c.id
            copies.push(c)
        }
        for (i = 0; i < copies.length; i++) {
            var n = copies[i]
            shiftClone(n, dx, dy)
            if (n.around && n.around.length) {
                var a = []
                var k
                for (k = 0; k < n.around.length; k++) {
                    if (map[n.around[k]])
                        a.push(map[n.around[k]])
                }
                n.around = a
            }
            var ls = n.leaders || []
            var li
            for (li = 0; li < ls.length; li++) {
                if (ls[li].from && ls[li].from.id && map[ls[li].from.id])
                    ls[li].from.id = map[ls[li].from.id]
                if (ls[li].to && ls[li].to.id && map[ls[li].to.id])
                    ls[li].to.id = map[ls[li].to.id]
            }
            nodes.push(n)
        }
        var ids = []
        for (i = 0; i < copies.length; i++)
            ids.push(copies[i].id)
        setSelection(ids)
        bump()
    }

    function duplicateSelection() {
        var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
        var src = []
        var i
        for (i = 0; i < ids.length; i++) {
            var n = nodeAt(ids[i])
            if (n)
                src.push(n)
        }
        pasteNodes(src, 16 / Math.max(1, spaceRect().w), 16 / Math.max(1, spaceRect().h))
    }

    function copySelection() {
        var ids = (selectedIds && selectedIds.length) ? selectedIds.slice() : (selectedId ? [selectedId] : [])
        var arr = []
        var i
        for (i = 0; i < ids.length; i++) {
            var n = nodeAt(ids[i])
            if (n)
                arr.push(JSON.parse(JSON.stringify(n)))
        }
        clip = arr
    }

    function pasteClipboard() {
        pasteNodes(clip || [], 16 / Math.max(1, spaceRect().w), 16 / Math.max(1, spaceRect().h))
    }

    function bringForward() {
        var list = nodes || []
        var i
        for (i = list.length - 2; i >= 0; i--) {
            if (isSelected(list[i].id) && !isSelected(list[i + 1].id)) {
                var t = list[i]
                list[i] = list[i + 1]
                list[i + 1] = t
            }
        }
        for (i = 0; i < list.length; i++) {
            if (isSelected(list[i].id) && isDraw(list[i]))
                list[i].zLayer = 4
        }
        bump()
    }

    function sendBack() {
        var list = nodes || []
        var i
        for (i = 1; i < list.length; i++) {
            if (isSelected(list[i].id) && !isSelected(list[i - 1].id)) {
                var t = list[i]
                list[i] = list[i - 1]
                list[i - 1] = t
            }
        }
        for (i = 0; i < list.length; i++) {
            if (isSelected(list[i].id) && isDraw(list[i]))
                list[i].zLayer = 1
        }
        bump()
    }

    function hitDraw(n, mx, my) {
        var i = nodeIndex(n.id)
        var it = (i >= 0 && _chips) ? _chips.itemAt(i) : null
        if (!it)
            return ""
        var p = it.mapFromItem(_ed, mx, my)
        var w = it.width
        var h = it.height
        if (tableCellHandlesOn(n)) {
            var cr = tableCurrentRect(n)
            var chs = [
                [cr.x, cr.y, "cell-nw"], [cr.x + cr.w, cr.y, "cell-ne"],
                [cr.x, cr.y + cr.h, "cell-sw"], [cr.x + cr.w, cr.y + cr.h, "cell-se"],
                [cr.x + cr.w * 0.5, cr.y, "cell-n"], [cr.x + cr.w * 0.5, cr.y + cr.h, "cell-s"],
                [cr.x, cr.y + cr.h * 0.5, "cell-w"], [cr.x + cr.w, cr.y + cr.h * 0.5, "cell-e"]
            ]
            var ct
            for (ct = 0; ct < chs.length; ct++) {
                if (Math.hypot(mx - chs[ct][0], my - chs[ct][1]) < 8)
                    return chs[ct][2]
            }
        }
        if (interactive && isSelected(n.id) && !isLocked(n) && !tableCellHandlesOn(n)) {
            var hs = [
                [0, 0, "nw"], [w, 0, "ne"], [0, h, "sw"], [w, h, "se"],
                [w * 0.5, 0, "n"], [w * 0.5, h, "s"], [0, h * 0.5, "w"], [w, h * 0.5, "e"]
            ]
            var t
            for (t = 0; t < hs.length; t++) {
                if (Math.hypot(p.x - hs[t][0], p.y - hs[t][1]) < 8)
                    return hs[t][2]
            }
        }
        if (isTable(n)) {
            var hitCell = tableCellAt(n, mx, my)
            if (hitCell.row >= 0 || hitCell.extra >= 0) {
                if (isLocked(n))
                    return ""
                return "body"
            }
        }
        if (p.x < 0 || p.y < 0 || p.x > w || p.y > h)
            return ""
        if (isLocked(n))
            return ""
        if (n.shape === "image" || n.shape === "table" || n.shape === "text" || n.fill === "filled")
            return "body"
        var ring = Math.max(6, (n.stroke || 2) + 4)
        if (p.x <= ring || p.y <= ring || p.x >= w - ring || p.y >= h - ring)
            return "body"
        return ""
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

    function isSelected(id) {
        if (!id)
            return false
        if (selectedId === id)
            return true
        var s = selectedIds || []
        for (var i = 0; i < s.length; i++) {
            if (s[i] === id)
                return true
        }
        return false
    }

    function setSelection(ids) {
        selectedIds = ids || []
        selectedId = selectedIds.length ? selectedIds[selectedIds.length - 1] : ""
        selectedSpine = -1
        selectedChanged()
    }

    function toggleSelected(id) {
        var s = (selectedIds || []).slice()
        var at = s.indexOf(id)
        if (at >= 0)
            s.splice(at, 1)
        else
            s.push(id)
        setSelection(s)
    }

    function isGroup(n) {
        if (!n)
            return false
        var k = n.kind
        if (k === "plus" || k === "pair" || k === "axis_stack" || k === "stack")
            return true
        return !!(n.members && n.members.length)
    }

    function isFiveWay(n) {
        if (!isGroup(n) || n.kind === "axis_stack")
            return false
        var mem = n.members || []
        if (mem.length !== 5)
            return false
        var roles = {}
        var ids = []
        var i
        for (i = 0; i < mem.length; i++) {
            if (mem[i].role)
                roles[String(mem[i].role).toLowerCase()] = true
            ids.push(mem[i].hwId)
        }
        if (roles.up && roles.down && roles.left && roles.right && (roles.center || roles.push))
            return true
        ids.sort(function (a, b) { return a - b })
        return (ids[0] === 6 && ids[4] === 10) || (ids[0] === 11 && ids[4] === 15) || (ids[0] === 16 && ids[4] === 20)
    }

    function fiveWayFormat(n) {
        var f = n && n.format ? String(n.format) : ""
        if (f === "plus" || f === "mini" || f === "card" || f === "radial")
            return f
        return ""
    }

    function ctxTarget() {
        tick
        return nodeAt((_ctx && _ctx.nodeId) || selectedId)
    }

    function ctxHasTheme() {
        tick
        var n = ctxTarget()
        return !!(n && isFiveWay(n) && fiveWayFormat(n) !== "")
    }

    function memberHasOverride(mem) {
        if (!mem)
            return false
        var keys = ["chipShape", "chipSize", "chipFill", "fontSize", "color", "border", "textColor",
                    "hlColor", "hlBorder", "hlText", "offX", "offY"]
        var i
        for (i = 0; i < keys.length; i++) {
            var v = mem[keys[i]]
            if (v !== undefined && v !== null && v !== "")
                return true
        }
        return false
    }

    function ctxHasGroupFormat() {
        tick
        var n = ctxTarget()
        if (!n || !isGroup(n))
            return false
        if (fiveWayFormat(n) !== "")
            return true
        var mem = n.members || []
        var i
        for (i = 0; i < mem.length; i++) {
            if (memberHasOverride(mem[i]))
                return true
        }
        return false
    }

    function clearGroupFormat() {
        var n = ctxTarget() || nodeAt(selectedId)
        if (!n || !isGroup(n))
            return
        selectedId = n.id
        var mem = n.members || []
        var keys = ["chipShape", "chipSize", "chipFill", "fontSize", "color", "border", "textColor",
                    "hlColor", "hlBorder", "hlText", "offX", "offY"]
        var i
        var k
        for (i = 0; i < mem.length; i++) {
            for (k = 0; k < keys.length; k++)
                delete mem[i][keys[k]]
        }
        if (isFiveWay(n)) {
            clearThemeMemberLayout(n)
            delete n.format
            if (n.leaders && n.leaders.length > 1)
                n.leaders = [n.leaders[0]]
        }
        bump()
    }

    function ctxHasSpines() {
        tick
        var n = ctxTarget()
        if (!n || isDraw(n))
            return false
        var ls = leaderList(n)
        var i
        for (i = 0; i < ls.length; i++) {
            if (ls[i].spines && ls[i].spines.length)
                return true
        }
        return !!(n.spines && n.spines.length)
    }

    function ctxSpineIndex() {
        tick
        if (_ctx && _ctx.kind === "spine" && _ctx.seg >= 0)
            return _ctx.seg
        return selectedSpine
    }

    function ctxHasSelectedSpine() {
        return ctxSpineIndex() >= 0
    }

    function ctxSpineCurved() {
        tick
        var n = ctxTarget()
        var i = ctxSpineIndex()
        if (!n || i < 0)
            return false
        var L = currentLeader(n)
        return !!(L && L.spines && L.spines[i] && L.spines[i].curve)
    }

    function convertSelectedSpine() {
        var n = ctxTarget()
        var i = ctxSpineIndex()
        if (!n || i < 0)
            return
        selectedId = n.id
        if (_ctx)
            selectedLeader = _ctx.leader
        var L = currentLeader(n)
        if (!L || !L.spines || i >= L.spines.length)
            return
        L.spines[i].curve = !L.spines[i].curve
        n.spines = L.spines
        selectedSpine = i
        bump()
    }

    function ctxMode() {
        tick
        var k = (_ctx && _ctx.kind) ? String(_ctx.kind) : ""
        if (k === "line" || k === "spine" || k === "from" || k === "to")
            return "leader"
        if (k === "draw")
            return "draw"
        var n = ctxTarget()
        if (!n)
            return "empty"
        if (isDraw(n))
            return "draw"
        return "chip"
    }

    function ctxIsLeader() {
        return ctxMode() === "leader"
    }

    function ctxHasMapItem() {
        var m = ctxMode()
        return m === "chip" || m === "leader"
    }

    function fiveWayRole(mem) {
        var r = String((mem && mem.role) || "").toLowerCase()
        if (r === "push")
            return "center"
        return r
    }

    function fiveWayCaption(n) {
        var id = n && n.id ? String(n.id) : ""
        if (id === "p610")
            return "Head 5-way"
        if (id === "p1115")
            return "Top-right 5-way"
        if (id === "p1620")
            return "Wheel 5-way"
        return "5-way"
    }

    function captionH(n) {
        var f = fiveWayFormat(n)
        if (f === "card" || f === "plus" || f === "mini")
            return Math.max(14, ((n && n.fontSize) || 10) + 4)
        return 0
    }

    function themeLayout(n) {
        var f = fiveWayFormat(n)
        return f === "plus" || f === "mini" || f === "radial"
    }

    function ensureFiveWayRoles(n) {
        var mem = n.members || []
        var i
        var ok = mem.length === 5
        for (i = 0; i < mem.length; i++) {
            var r = fiveWayRole(mem[i])
            if (!(r === "up" || r === "down" || r === "left" || r === "right" || r === "center"))
                ok = false
        }
        if (ok)
            return
        var ids = []
        for (i = 0; i < mem.length; i++)
            ids.push(mem[i].hwId)
        var min = ids.length ? Math.min.apply(null, ids) : 0
        var map = {}
        if (min === 6 || min === 11 || min === 16) {
            map[min] = "up"
            map[min + 1] = "right"
            map[min + 2] = "down"
            map[min + 3] = "left"
            map[min + 4] = "center"
        }
        var fallback = ["up", "left", "center", "right", "down"]
        for (i = 0; i < mem.length; i++) {
            if (map[mem[i].hwId])
                mem[i].role = map[mem[i].hwId]
            else if (!mem[i].role)
                mem[i].role = fallback[i] || "center"
        }
    }

    function roleWord(r) {
        if (r === "up") return "Up"
        if (r === "down") return "Down"
        if (r === "left") return "Left"
        if (r === "right") return "Right"
        if (r === "center") return "Push"
        return ""
    }

    function systemName(n, mem) {
        if (mem)
            return hardwareLabel(memberKind(n, mem), mem.hwId)
        if (!n)
            return ""
        return hardwareLabel(n.kind, n.hwId)
    }

    function hoverLabelAt(mx, my) {
        var list = nodes || []
        var i
        for (i = list.length - 1; i >= 0; i--) {
            var n = list[i]
            if (!n || isDraw(n))
                continue
            if (isGroup(n)) {
                var mi = memberHit(n, mx, my)
                if (mi >= 0 && n.members && n.members[mi])
                    return systemName(n, n.members[mi])
                continue
            }
            var it = _chips.itemAt(i)
            if (!it)
                continue
            var p = it.mapFromItem(_ed, mx, my)
            if (p.x >= 0 && p.y >= 0 && p.x <= it.width && p.y <= it.height)
                return systemName(n, null)
        }
        return ""
    }

    function setChipTip(mx, my) {
        hoverTipX = mx
        hoverTipY = my
        if (dragKind || banding || renameId)
            hoverHwLabel = ""
        else
            hoverHwLabel = hoverLabelAt(mx, my)
    }

    function memberHasCustomName(n, mem) {
        if (!mem)
            return false
        return isUserFriendly(memberKind(n, mem), mem.hwId, mem.friendly)
    }

    function memberLabel(n, mem) {
        return friendlyOf(n, mem)
    }

    function memByRole(n, role) {
        var mem = (n && n.members) ? n.members : []
        var i
        for (i = 0; i < mem.length; i++) {
            if (fiveWayRole(mem[i]) === role)
                return mem[i]
        }
        return null
    }

    function themeGap(n) {
        return Math.max(8, 4 * 2 + 2)
    }

    function themeGeom(n) {
        function bw(role) {
            var m = memByRole(n, role)
            return m ? chipWGuess(n, m) : 24
        }
        function bh(role) {
            var m = memByRole(n, role)
            return chipH(n, m)
        }
        var h = chipH(n, null)
        var wu = bw("up")
        var wl = bw("left")
        var wc = bw("center")
        var wr = bw("right")
        var wd = bw("down")
        var G = themeGap(n)
        var cap = captionH(n)
        var leftX = 0
        var pushX = wl + G
        var rightX = pushX + wc + G
        var pushC = pushX + wc * 0.5
        var upX = pushC - wu * 0.5
        var downX = pushC - wd * 0.5
        var minx = Math.min(0, upX, downX)
        var shift = minx < 0 ? -minx : 0
        leftX += shift
        pushX += shift
        rightX += shift
        upX += shift
        downX += shift
        var hu = bh("up")
        var hl = bh("left")
        var hc = bh("center")
        var hr = bh("right")
        var hd = bh("down")
        var rowH = Math.max(hl, hc, hr)
        var upY = cap
        var rowY = cap + hu + G
        var downY = rowY + rowH + G
        var maxx = Math.max(leftX + wl, pushX + wc, rightX + wr, upX + wu, downX + wd)
        return {
            up: { x: upX, y: upY },
            left: { x: leftX, y: rowY + (rowH - hl) * 0.5 },
            center: { x: pushX, y: rowY + (rowH - hc) * 0.5 },
            right: { x: rightX, y: rowY + (rowH - hr) * 0.5 },
            down: { x: downX, y: downY },
            w: Math.max(8, maxx),
            h: downY + hd
        }
    }

    function themeCell(n) {
        var g = themeGeom(n)
        return { w: g.w, h: chipH(n), gap: themeGap(n) }
    }

    function clearThemeMemberLayout(n) {
        var mem = n && n.members ? n.members : []
        var keys = ["chipShape", "chipSize", "chipFill", "fontSize", "color", "border", "textColor",
                    "hlColor", "hlBorder", "hlText", "offX", "offY"]
        var i, k
        for (i = 0; i < mem.length; i++) {
            for (k = 0; k < keys.length; k++)
                delete mem[i][keys[k]]
        }
    }

    function applyFiveWayFormat(fmt) {
        var id = selectedId || groupEditId
        var n = nodeAt(id)
        if (!isFiveWay(n))
            return
        if (fmt !== "plus" && fmt !== "mini" && fmt !== "card" && fmt !== "radial")
            return
        ensureFiveWayRoles(n)
        clearThemeMemberLayout(n)
        n.format = fmt
        if (fmt === "radial") {
            n.leaders = buildRadialLeaders(n)
        } else if (n.leaders && n.leaders.length > 1) {
            n.leaders = [n.leaders[0]]
        }
        bump()
    }

    function resetFiveWayFormat() {
        var id = selectedId || groupEditId
        var n = nodeAt(id)
        if (!isFiveWay(n))
            return
        clearThemeMemberLayout(n)
        delete n.format
        if (n.leaders && n.leaders.length > 1)
            n.leaders = [n.leaders[0]]
        bump()
    }

    function buildRadialLeaders(n) {
        var mem = n.members || []
        var out = []
        var i
        for (i = 0; i < mem.length; i++) {
            out.push({
                id: n.id + "_R" + i,
                from: { type: "member", id: n.id, member: i, pin: "right" },
                to: { type: "hot", id: n.id },
                spines: [],
                curve: false
            })
        }
        return out
    }

    function beginGroupEdit(id) {
        var n = nodeAt(id || selectedId)
        if (!isGroup(n))
            return
        if (!themeLayout(n))
            ensureMemberOffsets(n)
        groupEditId = n.id
        selectedMember = 0
        setSelection([n.id])
        bump()
    }

    function endGroupEdit() {
        groupEditId = ""
        selectedMember = -1
        dragMember = -1
        if (dragKind === "member")
            dragKind = ""
        bump()
    }

    function cancelAllActions() {
        endGroupEdit()
        drawTool = ""
        dragKind = ""
        clearMoveGuides()
        dragSpine = -1
        dragMember = -1
        banding = false
        selectedSpine = -1
        selectedLeader = 0
        selectedSeg = -1
        setSelection([])
        movePhoto = false
        if (_ctx)
            _ctx.close()
        if (_tableCtx)
            _tableCtx.close()
        if (_textCtx)
            _textCtx.close()
        textPaintOn = false
        cancelRename()
        armRenameId = ""
        armRenameMember = -1
        bump()
    }

    function chipScreenRect(n, mem) {
        if (!n)
            return Qt.rect(0, 0, 40, 20)
        if (isTable(n) && tableHasTarget()) {
            var tr = tableCurrentRect(n)
            return Qt.rect(tr.x, tr.y, tr.w, tr.h)
        }
        if (isText(n) || isDraw(n)) {
            var dg = drawGeom(n)
            return Qt.rect(dg.x, dg.y, dg.w, dg.h)
        }
        if (isGroup(n) && mem) {
            return Qt.rect(
                fxToX(n.chipFx) + groupMinX(n) + memberLocalX(n, mem),
                fyToY(n.chipFy) + groupMinY(n) + memberLocalY(n, mem),
                Math.max(24, chipWGuess(n, mem)),
                chipH(n, mem)
            )
        }
        return Qt.rect(
            fxToX(n.chipFx),
            fyToY(n.chipFy),
            Math.max(24, chipWGuess(n, null)),
            chipH(n, null)
        )
    }

    function beginRename(id, memberIndex) {
        var n = nodeAt(id)
        if (!n || isDraw(n))
            return
        var mem = null
        if (isGroup(n) && memberIndex >= 0 && n.members && memberIndex < n.members.length)
            mem = n.members[memberIndex]
        renameId = id
        renameMember = mem ? memberIndex : -1
        renameDraft = mem ? memberLabel(n, mem) : friendlyOf(n, null)
        dragKind = ""
        Qt.callLater(function () {
            if (_nameEdit) {
                _nameEdit.forceActiveFocus()
                _nameEdit.selectAll()
            }
        })
        bump()
    }

    function commitRename() {
        if (!renameId)
            return
        var n = nodeAt(renameId)
        if (!n) {
            cancelRename()
            return
        }
        var t = String(renameDraft || "").trim()
        if (isText(n)) {
            n.text = t
            fitTextBox(n)
        } else if (isTable(n) && tableHasTarget()) {
            ensureTable(n)
            if (tableExtra >= 0) {
                var ex = tableExtraAt(n, tableExtra)
                if (ex)
                    ex.text = t
            } else if (n.rows[tableRow] && n.rows[tableRow].cells && n.rows[tableRow].cells[tableCol]) {
                n.rows[tableRow].cells[tableCol].text = t
            }
        } else if (isGroup(n) && renameMember >= 0 && n.members && renameMember < n.members.length) {
            n.members[renameMember].friendly = t
        } else {
            n.friendly = t
        }
        cancelRename()
        bump()
    }

    function cancelRename() {
        renameId = ""
        renameMember = -1
        renameDraft = ""
    }

    function ensureMemberOffsets(n) {
        var mem = n.members || []
        var i
        var any = false
        for (i = 0; i < mem.length; i++) {
            if (mem[i].ox !== undefined || mem[i].oy !== undefined) {
                any = true
                break
            }
        }
        if (any) {
            for (i = 0; i < mem.length; i++) {
                if (mem[i].ox === undefined) mem[i].ox = 0
                if (mem[i].oy === undefined) mem[i].oy = 0
            }
            return
        }
        // Default column. Do not keep a 5-way cross. ox/oy only used in free layout.
        var eh = Math.max(1, height)
        var pitch = stackPitch(n) / eh
        for (i = 0; i < mem.length; i++) {
            mem[i].ox = 0
            mem[i].oy = i * pitch
        }
    }

    function demoteSpecialKinds() {
        var list = nodes || []
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (!n)
                continue
            if (n.kind === "plus" || n.kind === "pair")
                n.kind = "stack"
        }
    }

    function chipWGuess(n, mem) {
        var fs = styleVal(n, mem, "fontSize", 10)
        var sz = styleVal(n, mem, "chipSize", 18)
        var s = mem ? memberLabel(n, mem) : friendlyOf(n, null)
        var pad = Math.max(10, sz * 0.55)
        if (fiveWayFormat(n) === "mini" && !memberHasCustomName(n, mem))
            return uiPx(Math.max(18, fs + 10))
        return uiPx(String(s).length * fs * 0.50 + pad)
    }

    function memberHit(n, mx, my) {
        if (!isGroup(n))
            return -1
        var mem = n.members || []
        for (var i = mem.length - 1; i >= 0; i--) {
            var x = fxToX(n.chipFx) + groupMinX(n) + memberLocalX(n, mem[i])
            var y = fyToY(n.chipFy) + groupMinY(n) + memberLocalY(n, mem[i])
            var h = chipH(n, mem[i])
            var w = chipWGuess(n, mem[i])
            if (mx >= x && mx <= x + w && my >= y && my <= y + h)
                return i
        }
        return -1
    }

    function attachChipToTable(table, chip) {
        if (!table || !chip || isDraw(chip))
            return
        if (!table.packed)
            table.packed = []
        if (table.packed.indexOf(chip.id) < 0)
            table.packed.push(chip.id)
        chip.packId = table.id
        var fw = table.fw > 0 ? table.fw : 0.01
        var fh = table.fh > 0 ? table.fh : 0.01
        chip.packUx = ((chip.chipFx || 0) - (table.fx || 0)) / fw
        chip.packUy = ((chip.chipFy || 0) - (table.fy || 0)) / fh
    }

    function followTablePacked(table) {
        if (!isTable(table))
            return
        var i
        var ids = table.packed || []
        for (i = 0; i < ids.length; i++) {
            var q = nodeAt(ids[i])
            if (!q || isDraw(q))
                continue
            q.chipFx = (table.fx || 0) + (q.packUx || 0) * (table.fw || 0)
            q.chipFy = (table.fy || 0) + (q.packUy || 0) * (table.fh || 0)
        }
        var draws = table.packedDraw || []
        for (i = 0; i < draws.length; i++) {
            var d = nodeAt(draws[i])
            if (!isText(d) && !isDraw(d))
                continue
            d.fx = (table.fx || 0) + (d.packUx || 0) * (table.fw || 0)
            d.fy = (table.fy || 0) + (d.packUy || 0) * (table.fh || 0)
        }
    }

    function attachDrawToTable(table, draw) {
        if (!isTable(table) || !isDraw(draw) || draw.id === table.id)
            return
        if (!table.packedDraw)
            table.packedDraw = []
        if (table.packedDraw.indexOf(draw.id) < 0)
            table.packedDraw.push(draw.id)
        draw.packId = table.id
        var fw = table.fw > 0 ? table.fw : 0.01
        var fh = table.fh > 0 ? table.fh : 0.01
        draw.packUx = ((draw.fx || 0) - (table.fx || 0)) / fw
        draw.packUy = ((draw.fy || 0) - (table.fy || 0)) / fh
    }

    function tablePackOf(n) {
        if (!n)
            return null
        if (isTable(n) && tableIsPacked(n))
            return n
        if (n.packId) {
            var t = nodeAt(n.packId)
            if (isTable(t))
                return t
        }
        return null
    }

    function shiftIndependentParts(table, dFx, dFy) {
        if (!isTable(table) || (!dFx && !dFy))
            return
        function bump(cell) {
            if (!cell || !cell.independent)
                return
            cell.efx = (cell.efx || 0) + dFx
            cell.efy = (cell.efy || 0) + dFy
        }
        var extras = table.extras || []
        var i
        for (i = 0; i < extras.length; i++)
            bump(extras[i])
        var rows = table.rows || []
        var r
        var c
        for (r = 0; r < rows.length; r++) {
            var cells = rows[r] && rows[r].cells ? rows[r].cells : []
            for (c = 0; c < cells.length; c++)
                bump(cells[c])
        }
    }

    function moveTablePack(table, dFx, dFy) {
        if (!isTable(table) || isLocked(table))
            return
        table.fx = Math.max(0, Math.min(0.98, (table.fx || 0) + dFx))
        table.fy = Math.max(0, Math.min(0.98, (table.fy || 0) + dFy))
        shiftIndependentParts(table, dFx, dFy)
        followTablePacked(table)
    }

    function refreshChipPack(chip) {
        if (!chip || !chip.packId)
            return
        var table = nodeAt(chip.packId)
        if (!isTable(table))
            return
        attachChipToTable(table, chip)
    }

    function detachChipFromTable(chip) {
        if (!chip || !chip.packId)
            return
        var table = nodeAt(chip.packId)
        if (isTable(table) && table.packed) {
            var at = table.packed.indexOf(chip.id)
            if (at >= 0)
                table.packed.splice(at, 1)
        }
        delete chip.packId
        delete chip.packUx
        delete chip.packUy
    }

    function detachTablePacked(table) {
        if (!table)
            return
        var ids = (table.packed || []).slice()
        var i
        for (i = 0; i < ids.length; i++) {
            var q = nodeAt(ids[i])
            if (q) {
                delete q.packId
                delete q.packUx
                delete q.packUy
            }
        }
        table.packed = []
        var draws = (table.packedDraw || []).slice()
        for (i = 0; i < draws.length; i++) {
            var d = nodeAt(draws[i])
            if (d) {
                delete d.packId
                delete d.packUx
                delete d.packUy
            }
        }
        table.packedDraw = []
    }

    function tableIsPacked(n) {
        return !!(isTable(n) && ((n.packed && n.packed.length) || (n.packedDraw && n.packedDraw.length)))
    }

    function canGroup() {
        return (selectedIds || []).length >= 2
    }

    function packTableFromSelection() {
        var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
        var i
        for (i = 0; i < ids.length; i++) {
            var n = nodeAt(ids[i])
            if (tableIsPacked(n))
                return n
            if (n && n.packId) {
                var t = nodeAt(n.packId)
                if (tableIsPacked(t))
                    return t
            }
        }
        return null
    }

    function canUngroup() {
        if (packTableFromSelection())
            return true
        var n = nodeAt(selectedId) || ctxTarget()
        return isGroup(n)
    }

    function _uid(prefix) {
        return prefix + "_" + Date.now().toString(36) + Math.floor(Math.random() * 1000)
    }

    function _styleOf(n) {
        return {
            color: n.color || "#18181B",
            border: n.border || "#3F3F46",
            textColor: n.textColor || "#E4E4E7",
            highlight: n.highlight !== false,
            hlColor: n.hlColor || "#14532D",
            hlBorder: n.hlBorder || "#22C55E",
            hlText: n.hlText || "#BBF7D0",
            fontSize: n.fontSize || 10,
            pin: n.pin || "right",
            curve: n.curve !== false,
            chipSize: n.chipSize || 18,
            chipShape: n.chipShape || "round",
            chipFill: n.chipFill || "filled",
            hotSize: n.hotSize || 9,
            hotShape: n.hotShape || "round",
            hotFill: n.hotFill || "filled"
        }
    }

    function _partsFrom(n) {
        var out = []
        if (!n)
            return out
        if (isGroup(n)) {
            var mem = n.members || []
            for (var i = 0; i < mem.length; i++)
                out.push({ hwId: mem[i].hwId, kind: memberKind(n, mem[i]), role: mem[i].role || "", src: n, friendly: mem[i].friendly || "" })
        } else {
            out.push({ hwId: n.hwId, kind: n.kind || "btn", role: "", src: n, friendly: n.friendly || "" })
        }
        return out
    }

    function groupSelection() {
        var ids = selectedIds || []
        if (ids.length < 2)
            return
        packWarn = ""
        var tables = []
        var chipNodes = []
        var textNodes = []
        var i
        var n
        for (i = 0; i < ids.length; i++) {
            n = nodeAt(ids[i])
            if (!n)
                continue
            if (isTable(n))
                tables.push(n)
            else if (isText(n))
                textNodes.push(n)
            else if (!isDraw(n))
                chipNodes.push(n)
        }
        if (!tables.length && chipNodes.length) {
            var inferred = tablesUnderChips(chipNodes)
            if (inferred.length > 1) {
                packWarn = "Chips sit on more than one table."
                bump()
                return
            }
            if (inferred.length === 1)
                tables = inferred
        }
        if (tables.length > 1) {
            packWarn = "Group one table at a time."
            bump()
            return
        }
        if (tables.length === 1) {
            if (!chipNodes.length && !textNodes.length) {
                packWarn = "Select chips or text with the table to pack."
                bump()
                return
            }
            var table = tables[0]
            for (i = 0; i < chipNodes.length; i++)
                attachChipToTable(table, chipNodes[i])
            for (i = 0; i < textNodes.length; i++)
                attachDrawToTable(table, textNodes[i])
            var keep = [table.id]
            for (i = 0; i < chipNodes.length; i++)
                keep.push(chipNodes[i].id)
            for (i = 0; i < textNodes.length; i++)
                keep.push(textNodes[i].id)
            setSelection(keep)
            bump()
            return
        }
        var parts = []
        var chipIds = []
        for (i = 0; i < ids.length; i++) {
            var chunkN = nodeAt(ids[i])
            if (!chunkN || isDraw(chunkN))
                continue
            chipIds.push(ids[i])
            var chunk = _partsFrom(chunkN)
            for (var p = 0; p < chunk.length; p++)
                parts.push(chunk[p])
        }
        if (parts.length < 2)
            return
        var axisN = 0
        for (i = 0; i < parts.length; i++) {
            if (parts[i].kind === "axis")
                axisN++
        }
        var kind = "stack"
        if (axisN === parts.length)
            kind = "axis_stack"
        var first = nodeAt(chipIds[0])
        var st = _styleOf(first)
        var fx = 0
        var fy = 0
        var hx = 0
        var hy = 0
        for (i = 0; i < chipIds.length; i++) {
            n = nodeAt(chipIds[i])
            fx += (n.chipFx || 0)
            fy += (n.chipFy || 0)
            hx += hotFxOf(n)
            hy += hotFyOf(n)
        }
        var c = chipIds.length
        var ox0 = fx / c
        var oy0 = fy / c
        parts.sort(function(a, b) {
            var dy = (a.src.chipFy || 0) - (b.src.chipFy || 0)
            return dy !== 0 ? dy : ((a.src.chipFx || 0) - (b.src.chipFx || 0))
        })
        var members = []
        for (i = 0; i < parts.length; i++)
            members.push({
                hwId: parts[i].hwId,
                kind: leafKind(parts[i].kind),
                role: parts[i].role || ("m" + i),
                ox: parts[i].src.chipFx - ox0,
                oy: parts[i].src.chipFy - oy0,
                friendly: carryFriendly(parts[i].friendly, carryFriendly(parts[i].src && parts[i].src.friendly, defaultFriendly(parts[i].kind, parts[i].hwId)))
            })
        var g = {
            id: _uid("g"), kind: kind, members: members,
            hotFx: hx / c, hotFy: hy / c, chipFx: ox0, chipFy: oy0,
            pin: st.pin, spines: [], curve: st.curve, alignH: "left",
            color: st.color, border: st.border, textColor: st.textColor,
            highlight: st.highlight, hlColor: st.hlColor, hlBorder: st.hlBorder,
            hlText: st.hlText, fontSize: st.fontSize, label: "", chipSize: st.chipSize, chipShape: st.chipShape, chipFill: st.chipFill, hotSize: st.hotSize, hotShape: st.hotShape, hotFill: st.hotFill
        }
        g.from = { type: "chip", id: g.id, pin: g.pin }
        g.to = { type: "hot", id: g.id }
        g.leaders = [{
            id: g.id + "_L0",
            from: g.from,
            to: g.to,
            spines: [],
            curve: st.curve !== false
        }]
        var drop = {}
        for (i = 0; i < chipIds.length; i++)
            drop[chipIds[i]] = true
        var list = nodes || []
        for (i = list.length - 1; i >= 0; i--) {
            if (drop[list[i].id])
                list.splice(i, 1)
        }
        var oi, sj
        for (oi = 0; oi < list.length; oi++) {
            if (!list[oi].sockets)
                continue
            for (sj = 0; sj < list[oi].sockets.length; sj++) {
                if (drop[list[oi].sockets[sj].chipId])
                    list[oi].sockets[sj].chipId = ""
            }
        }
        list.push(g)
        setSelection([g.id])
        bump()
    }

    function ungroupSelection() {
        var packed = packTableFromSelection()
        if (packed) {
            detachTablePacked(packed)
            bump()
            return
        }
        var n = nodeAt(selectedId)
        if (!isGroup(n))
            n = ctxTarget()
        if (!isGroup(n))
            return
        var mem = n.members || []
        if (!mem.length)
            return
        var st = _styleOf(n)
        var created = []
        var i
        for (i = 0; i < mem.length; i++) {
            var px = fxToX(n.chipFx) + groupMinX(n) + memberLocalX(n, mem[i])
            var py = fyToY(n.chipFy) + groupMinY(n) + memberLocalY(n, mem[i])
            var kindOf = memberKind(n, mem[i])
            created.push({
                id: _uid(kindOf === "btn" ? "b" : kindOf.charAt(0)), kind: kindOf, hwId: mem[i].hwId,
                prefix: kindOf === "axis" ? "A" : "",
                label: "",
                friendly: carryFriendly(mem[i].friendly, defaultFriendly(kindOf, mem[i].hwId)),
                hotFx: hotFxOf(n), hotFy: hotFyOf(n),
                chipFx: xToFx(px),
                chipFy: yToFy(py),
                pin: st.pin, spines: [], curve: st.curve,
                color: st.color, border: st.border, textColor: st.textColor,
                highlight: st.highlight, hlColor: st.hlColor, hlBorder: st.hlBorder,
                hlText: st.hlText, fontSize: st.fontSize, chipSize: st.chipSize, chipShape: st.chipShape, chipFill: st.chipFill, hotSize: st.hotSize, hotShape: st.hotShape, hotFill: st.hotFill
            })
        }
        var list = nodes || []
        var idx = nodeIndex(n.id)
        if (idx < 0)
            return
        list.splice(idx, 1)
        for (i = 0; i < created.length; i++)
            list.splice(idx + i, 0, created[i])
        groupEditId = ""
        selectedMember = -1
        setSelection([])
        bump()
    }

    function setGroupKind(kind) {
        var n = nodeAt(selectedId)
        if (!isGroup(n) || !kind)
            return
        n.kind = kind === "plus" ? "stack" : kind
        bump()
    }

    function rectHitsBand(r, x0, y0, x1, y1) {
        if (!r)
            return false
        return r.x < x1 && r.x + r.w > x0 && r.y < y1 && r.y + r.h > y0
    }

    function tableHitsBand(n, x0, y0, x1, y1) {
        if (!isTable(n))
            return false
        if (rectHitsBand(drawGeom(n), x0, y0, x1, y1))
            return true
        var extras = n.extras || []
        var i
        for (i = 0; i < extras.length; i++) {
            if (rectHitsBand(tableExtraRect(n, i), x0, y0, x1, y1))
                return true
        }
        var r
        var c
        var rows = (n.rows && n.rows.length) ? n.rows.length : 0
        var cols = n.cols > 0 ? n.cols : 0
        for (r = 0; r < rows; r++) {
            for (c = 0; c < cols; c++) {
                if (tableCellIsFree(n, r, c) && rectHitsBand(tableCellRect(n, r, c), x0, y0, x1, y1))
                    return true
            }
        }
        return false
    }

    function tablesUnderChips(chips) {
        var out = []
        var seen = {}
        var list = nodes || []
        var i
        var t
        for (i = 0; i < chips.length; i++) {
            var chip = chips[i]
            var b = chipBounds(chip)
            var cx = b.x + b.w * 0.5
            var cy = b.y + b.h * 0.5
            var j
            for (j = 0; j < list.length; j++) {
                t = list[j]
                if (!isTable(t) || seen[t.id])
                    continue
                var g = drawGeom(t)
                var hit = cx >= g.x && cx <= g.x + g.w && cy >= g.y && cy <= g.y + g.h
                var ei
                var extras = t.extras || []
                for (ei = 0; !hit && ei < extras.length; ei++) {
                    var er = tableExtraRect(t, ei)
                    if (cx >= er.x && cx <= er.x + er.w && cy >= er.y && cy <= er.y + er.h)
                        hit = true
                }
                if (!hit)
                    continue
                seen[t.id] = true
                out.push(t)
            }
        }
        return out
    }

    function selectBand(add) {
        var x0 = Math.min(bandX0, bandX1)
        var y0 = Math.min(bandY0, bandY1)
        var x1 = Math.max(bandX0, bandX1)
        var y1 = Math.max(bandY0, bandY1)
        var ids = add ? (selectedIds || []).slice() : []
        var list = nodes || []
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            var hit = false
            if (isTable(n)) {
                hit = tableHitsBand(n, x0, y0, x1, y1)
            } else {
                var it = _chips.itemAt(i)
                if (!it)
                    continue
                var cx = it.x + it.width * 0.5
                var cy = it.y + it.height * 0.5
                hit = cx >= x0 && cx <= x1 && cy >= y0 && cy <= y1
            }
            if (hit && ids.indexOf(n.id) < 0)
                ids.push(n.id)
            if (hit && isTable(n)) {
                var pk = n.packed || []
                var p
                for (p = 0; p < pk.length; p++) {
                    if (ids.indexOf(pk[p]) < 0)
                        ids.push(pk[p])
                }
                var pd = n.packedDraw || []
                for (p = 0; p < pd.length; p++) {
                    if (ids.indexOf(pd[p]) < 0)
                        ids.push(pd[p])
                }
            }
            if (hit && n.packId && ids.indexOf(n.packId) < 0)
                ids.push(n.packId)
        }
        setSelection(ids)
    }


    Connections {
        target: face
        function onLiveStampChanged() { _ed.tick++ }
        function onDestTickChanged() { _ed.tick++ }
        function onWidthChanged() { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
        function onHeightChanged() { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
    }

    Repeater {
        id: _chips
        model: { _ed.tick; return (_ed.nodes || []).length }
        delegate: Item {
            id: _wrap
            required property int index
            readonly property var node: {
                _ed.tick
                var list = _ed.nodes || []
                return (index >= 0 && index < list.length) ? list[index] : null
            }
            visible: node !== null
            x: {
                _ed.tick
                if (!node)
                    return 0
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).x
                var x = _ed.fxToX(node.chipFx)
                if (_ed.isGroup(node))
                    x += _ed.groupMinX(node)
                return x
            }
            y: {
                _ed.tick
                if (!node)
                    return 0
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).y
                var y = _ed.fyToY(node.chipFy)
                if (_ed.isGroup(node))
                    y += _ed.groupMinY(node)
                return y
            }
            z: {
                _ed.tick
                if (!node)
                    return 0
                if (node.zLayer !== undefined && node.zLayer !== null)
                    return node.zLayer
                return _ed.isDraw(node) ? 2 : 3
            }
            rotation: { _ed.tick; return (_ed.isDraw(node) && node.rot) ? node.rot : 0 }
            opacity: { _ed.tick; return (_ed.isDraw(node) && node.opacity !== undefined && node.opacity !== null) ? node.opacity : 1 }
            transformOrigin: Item.Center
            clip: false
            width: {
                _ed.tick
                if (!node)
                    return 40
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).w
                if (_ed.isGroup(node))
                    return _ed.groupSpanW(node)
                return (_body.item && _body.item.implicitWidth > 1) ? _body.item.implicitWidth : _ed.chipWGuess(node, null)
            }
            height: {
                _ed.tick
                if (!node)
                    return 20
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).h
                if (_ed.isGroup(node))
                    return _ed.groupSpanH(node)
                return (_body.item && _body.item.implicitHeight > 1) ? _body.item.implicitHeight : _ed.chipH(node)
            }

            Loader {
                id: _body
                clip: false
                width: {
                    _ed.tick
                    if (_wrap.node && (_ed.isGroup(_wrap.node) || _ed.isDraw(_wrap.node)))
                        return _wrap.width
                    return item ? item.implicitWidth : 0
                }
                height: {
                    _ed.tick
                    if (_wrap.node && (_ed.isGroup(_wrap.node) || _ed.isDraw(_wrap.node)))
                        return _wrap.height
                    return item ? item.implicitHeight : 0
                }
                sourceComponent: {
                    var n = _wrap.node
                    if (!n) return _tagComp
                    if (_ed.isDraw(n)) return _drawComp
                    return _ed.isGroup(n) ? _groupComp : _tagComp
                }
                onLoaded: {
                    item.node = Qt.binding(function() { return _wrap.node })
                    if (_wrap.node && _ed.isGroup(_wrap.node))
                        _ed.ensureMemberOffsets(_wrap.node)
                    if (_wrap.node && _ed.isTable(_wrap.node))
                        _ed.ensureTable(_wrap.node)
                }
            }
        }
    }

    Component {
        id: _groupComp
        RigGroupItem { ed: _ed }
    }

    Component {
        id: _drawComp
        RigDrawItem { ed: _ed }
    }

    Component {
        id: _tagComp
        RigChipItem { ed: _ed }
    }

    onWidthChanged: { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
    onHeightChanged: { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
    onTickChanged: _lines.requestPaint()
    onGridOnChanged: if (_grid) _grid.requestPaint()
    onGridSizeChanged: if (_grid) _grid.requestPaint()
    onNodesChanged: {
        seeded = false
        _lines.requestPaint()
        _seedTimer.restart()
    }

    Timer {
        id: _seedTimer
        interval: 80
        repeat: false
        onTriggered: {
            var list = _ed.nodes || []
            _ed.demoteSpecialKinds()
            for (var i = 0; i < list.length; i++) {
                _ed.ensureFriendly(list[i])
                _ed.ensureMidSpine(list[i])
            }
            _ed.seeded = true
            _ed.bump()
        }
    }

    RigPhotoLayer { id: _photoWell; ed: _ed; linesCanvas: _lines }

    RigGuides { id: _guides; ed: _ed }

    RigGrid { id: _grid; ed: _ed }

    RigLeaderLayer { id: _lines; ed: _ed }

    RigPointerArea {
        ed: _ed
        chipMenu: _ctx
        tableMenu: _tableCtx
        textMenu: _textCtx
        spineHoldTimer: _spineHold
    }

    MouseArea {
        anchors.fill: parent
        z: 8
        enabled: !_ed.interactive
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onPositionChanged: (m) => _ed.setChipTip(m.x, m.y)
        onExited: _ed.hoverHwLabel = ""
    }

    ToolTip {
        visible: _ed.hoverHwLabel.length > 0 && !_ed.dragKind && !_ed.renameId
        text: _ed.hoverHwLabel
        delay: 400
        timeout: 4000
        x: _ed.hoverTipX - width / 2
        y: _ed.hoverTipY - height - Style.dp(8)
    }

    TextEdit {
        id: _textClip
        visible: false
        width: 1
        height: 1
    }

    Text {
        renderType: Text.NativeRendering
        id: _textFit
        visible: false
        width: 100
        wrapMode: Text.WordWrap
        font.pixelSize: 12
    }

    TextInput {
        id: _nameEdit
        z: 12
        visible: _ed.interactive && _ed.renameId.length > 0
        x: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.chipScreenRect(n, mem).x
        }
        y: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.chipScreenRect(n, mem).y
        }
        width: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return Math.max(Style.dp(48), _ed.chipScreenRect(n, mem).width)
        }
        height: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return Math.max(18, _ed.chipScreenRect(n, mem).height)
        }
        text: _ed.renameDraft
        color: "#E4E4E7"
        font.pixelSize: {
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.styleVal(n, mem, "fontSize", 10)
        }
        horizontalAlignment: TextInput.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        selectByMouse: true
        clip: true
        leftPadding: Style.dp(4)
        rightPadding: Style.dp(4)
        onTextChanged: _ed.renameDraft = text
        onAccepted: _ed.commitRename()
        Keys.onEscapePressed: (event) => {
            _ed.cancelRename()
            event.accepted = true
        }
        Rectangle {
            anchors.fill: parent
            z: -1
            radius: Style.dp(4)
            color: "#18181B"
            border.color: "#38BDF8"
            border.width: Style.dp(2)
        }
    }

    Rectangle {
        visible: _ed.banding
        x: Math.min(_ed.bandX0, _ed.bandX1)
        y: Math.min(_ed.bandY0, _ed.bandY1)
        width: Math.abs(_ed.bandX1 - _ed.bandX0)
        height: Math.abs(_ed.bandY1 - _ed.bandY0)
        z: 9
        color: "#33FBBF24"
        border.color: "#FBBF24"
        border.width: Style.dp(1)
    }

    Text {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: Style.dp(6)
        z: 9
        visible: _ed.interactive && text.length
        color: "#A1A1AA"
        font.pixelSize: Style.dp(10)
        text: {
            if (_ed.packWarn.length)
                return _ed.packWarn
            if (_ed.dragKind === "tablecell")
                return "Dragging free cell. Handles still resize the table."
            if (_ed.textPaintOn)
                return "Format painter — click a text box. Esc cancels."
            if (_ed.drawTool === "text")
                return "Draw text — drag a box. Double-click to edit. Esc cancels."
            if (_ed.drawTool === "table")
                return "Draw table — drag a box. Blank 1×2. Esc cancels."
            if (_ed.drawTool.length)
                return "Draw " + _ed.drawTool + " — drag on empty. Esc cancels."
            if (_ed.groupEditId.length) {
                var n = _ed.nodeAt(_ed.groupEditId)
                var mem = _ed.targetMember()
                var who = mem ? (_ed.roleWord(_ed.fiveWayRole(mem)) || "cell") : "group"
                return "Edit group " + _ed.groupEditId + " · " + who + ". Drag a cell to nudge. Esc done."
            }
            return ""
        }
    }

    Canvas {
        visible: _ed.interactive && _ed.dragKind === "drawnew"
        x: Math.min(_ed.drawX0, _ed.drawX1)
        y: Math.min(_ed.drawY0, _ed.drawY1)
        width: Math.max(1, Math.abs(_ed.drawX1 - _ed.drawX0))
        height: Math.max(1, Math.abs(_ed.drawY1 - _ed.drawY0))
        z: 7
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            _ed.paintDraw(ctx, { shape: _ed.drawTool || "rect", fill: "hollow", color: "#14532D", border: "#22C55E", stroke: 2 }, width, height)
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Timer {
        id: _spineHold
        interval: 450
        repeat: false
        onTriggered: {
            if (!_ed.spineHoldArm)
                return
            _ed.spineHoldArm = false
            _ed.deleteSpineAt(_ed.spineHoldId, _ed.spineHoldLeader, _ed.spineHoldIndex)
        }
    }

    Menu {
        id: _tableCtx
        MenuItem {
            text: "Add row below"
            onTriggered: _ed.addTableRow(true)
        }
        MenuItem {
            text: "Insert row above"
            onTriggered: _ed.addTableRow(false)
        }
        MenuItem {
            text: "Delete this row"
            enabled: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.rows && n.rows.length > 1)
            }
            onTriggered: _ed.deleteTableRow()
        }
        MenuSeparator {}
        MenuItem {
            text: "Add column right"
            onTriggered: _ed.addTableCol(true)
        }
        MenuItem {
            text: "Insert column left"
            onTriggered: _ed.addTableCol(false)
        }
        MenuItem {
            text: "Delete this column"
            enabled: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.cols > 1)
            }
            onTriggered: _ed.deleteTableCol()
        }
        MenuItem {
            text: "ID column"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.idCol)
            }
            onTriggered: _ed.toggleTableIdCol()
        }
        MenuItem {
            text: "Free position"
            checkable: true
            enabled: {
                _ed.tick
                return _ed.tableHasTarget()
            }
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                var c = _ed.tableCurrentCell(n)
                return !!(c && c.free)
            }
            onTriggered: _ed.toggleTableCellFree()
        }
        MenuItem {
            text: "Independent of table"
            checkable: true
            enabled: {
                _ed.tick
                return _ed.tableHasTarget()
            }
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                var c = _ed.tableCurrentCell(n)
                return !!(c && c.independent)
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                var c = _ed.tableCurrentCell(n)
                _ed.setTableCellIndependent(!(c && c.independent))
            }
        }
        MenuItem {
            text: "Spawn empty cell"
            onTriggered: _ed.spawnEmptyCell()
        }
        MenuItem {
            text: "Delete this cell"
            enabled: {
                _ed.tick
                return _ed.tableExtra >= 0
            }
            onTriggered: _ed.deleteThisTableCell()
        }
        Menu {
            title: "Place"
            enabled: {
                _ed.tick
                return _ed.tableHasTarget()
            }
            MenuItem { text: "Far left"; onTriggered: _ed.placeTableCell("left") }
            MenuItem { text: "Center"; onTriggered: _ed.placeTableCell("center") }
            MenuItem { text: "Far right"; onTriggered: _ed.placeTableCell("right") }
            MenuSeparator {}
            MenuItem { text: "Top"; onTriggered: _ed.placeTableCell("top") }
            MenuItem { text: "Middle"; onTriggered: _ed.placeTableCell("middle") }
            MenuItem { text: "Bottom"; onTriggered: _ed.placeTableCell("bottom") }
        }
        MenuSeparator {}
        Menu {
            title: "Theme"
            MenuItem {
                text: "Gremlin dark"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.theme || n.theme === "gremlin"
                }
                onTriggered: _ed.setTableTheme("gremlin")
            }
            MenuItem {
                text: "Gremlin hollow"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "hollow")
                }
                onTriggered: _ed.setTableTheme("hollow")
            }
            MenuItem {
                text: "Sheet"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "sheet")
                }
                onTriggered: _ed.setTableTheme("sheet")
            }
        }
        Menu {
            title: "Font size"
            MenuItem {
                text: "8"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 8)
                }
                onTriggered: _ed.setTableFont(8)
            }
            MenuItem {
                text: "10"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.fontSize || n.fontSize === 10
                }
                onTriggered: _ed.setTableFont(10)
            }
            MenuItem {
                text: "12"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 12)
                }
                onTriggered: _ed.setTableFont(12)
            }
            MenuItem {
                text: "14"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 14)
                }
                onTriggered: _ed.setTableFont(14)
            }
            MenuItem {
                text: "16"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 16)
                }
                onTriggered: _ed.setTableFont(16)
            }
        }
        MenuSeparator {}
        MenuItem {
            text: "Break group"
            enabled: {
                _ed.tick
                return _ed.canUngroup()
            }
            onTriggered: _ed.ungroupSelection()
        }
        MenuItem {
            text: {
                _ed.tick
                var n = _ed.pinTarget()
                return _ed.isLocked(n) ? "Unpin" : "Pin"
            }
            checkable: true
            checked: {
                _ed.tick
                return _ed.isLocked(_ed.pinTarget())
            }
            onTriggered: {
                var n = _ed.pinTarget()
                if (n)
                    _ed.toggleLock(n.id)
            }
        }
        MenuItem {
            text: "Bring forward"
            onTriggered: _ed.bringForward()
        }
        MenuItem {
            text: "Send back"
            onTriggered: _ed.sendBack()
        }
        MenuSeparator {}
        MenuItem {
            text: "Delete table"
            onTriggered: _ed.deleteTable()
        }
    }

    Menu {
        id: _textCtx
        MenuItem {
            text: "Edit text…"
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                if (_ed.isText(n))
                    _ed.beginTextRename(n.id)
            }
        }
        MenuItem { text: "Delete text box"; onTriggered: _ed.deleteChip() }
        MenuItem { text: "Duplicate"; onTriggered: _ed.duplicateSelection() }
        MenuItem { text: "Copy format"; onTriggered: _ed.copyTextFormat() }
        MenuItem { text: "Copy text"; onTriggered: _ed.copyTextPlain() }
        MenuItem { text: "Clear formatting"; onTriggered: _ed.clearTextFormat() }
        MenuItem {
            text: "Paint format"
            enabled: {
                _ed.tick
                return !!_ed.textFormatClip
            }
            checkable: true
            checked: {
                _ed.tick
                return _ed.textPaintOn
            }
            onTriggered: {
                if (!_ed.textFormatClip)
                    return
                _ed.applyTextFormat()
                _ed.textPaintOn = true
                _ed.bump()
            }
        }
        MenuSeparator {}
        Menu {
            title: "Size"
            MenuItem {
                text: "Caption  72×20"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(72, 20)
                }
                onTriggered: _ed.applyTextBoxSize(72, 20)
            }
            MenuItem {
                text: "Small  96×24"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(96, 24)
                }
                onTriggered: _ed.applyTextBoxSize(96, 24)
            }
            MenuItem {
                text: "Medium  128×32"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(128, 32)
                }
                onTriggered: _ed.applyTextBoxSize(128, 32)
            }
            MenuItem {
                text: "Large  176×40"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(176, 40)
                }
                onTriggered: _ed.applyTextBoxSize(176, 40)
            }
            MenuItem {
                text: "Title  240×48"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(240, 48)
                }
                onTriggered: _ed.applyTextBoxSize(240, 48)
            }
            MenuItem {
                text: "Wide  280×28"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(280, 28)
                }
                onTriggered: _ed.applyTextBoxSize(280, 28)
            }
        }
        Menu {
            title: "Theme"
            MenuItem {
                text: "Gremlin dark"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.theme || n.theme === "gremlin"
                }
                onTriggered: _ed.applyTextTheme("gremlin")
            }
            MenuItem {
                text: "Gremlin hollow"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "hollow")
                }
                onTriggered: _ed.applyTextTheme("hollow")
            }
            MenuItem {
                text: "Sheet"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "sheet")
                }
                onTriggered: _ed.applyTextTheme("sheet")
            }
        }
        Menu {
            title: "Font"
            MenuItem {
                text: "8"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 8)
                }
                onTriggered: _ed.applyField("fontSize", 8)
            }
            MenuItem {
                text: "10"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 10)
                }
                onTriggered: _ed.applyField("fontSize", 10)
            }
            MenuItem {
                text: "12"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.fontSize || n.fontSize === 12
                }
                onTriggered: _ed.applyField("fontSize", 12)
            }
            MenuItem {
                text: "14"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 14)
                }
                onTriggered: _ed.applyField("fontSize", 14)
            }
            MenuItem {
                text: "16"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 16)
                }
                onTriggered: _ed.applyField("fontSize", 16)
            }
            MenuItem {
                text: "18"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 18)
                }
                onTriggered: _ed.applyField("fontSize", 18)
            }
            MenuItem {
                text: "24"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 24)
                }
                onTriggered: _ed.applyField("fontSize", 24)
            }
        }
        Menu {
            title: "Color"
            MenuItem { text: "Text…"; onTriggered: _ed.requestDrawColor("textColor") }
            MenuItem { text: "Fill…"; onTriggered: _ed.requestDrawColor("color") }
            MenuItem { text: "Stroke…"; onTriggered: _ed.requestDrawColor("border") }
        }
        Menu {
            title: "Opacity"
            Menu {
            title: "Fill"
            MenuItem {
                text: "0%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0)
                }
                onTriggered: _ed.applyField("fillOpacity", 0)
            }
            MenuItem {
                text: "25%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0.25)
                }
                onTriggered: _ed.applyField("fillOpacity", 0.25)
            }
            MenuItem {
                text: "50%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0.5)
                }
                onTriggered: _ed.applyField("fillOpacity", 0.5)
            }
            MenuItem {
                text: "75%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0.75)
                }
                onTriggered: _ed.applyField("fillOpacity", 0.75)
            }
            MenuItem {
                text: "100%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || n.fillOpacity === undefined || n.fillOpacity === 1
                }
                onTriggered: _ed.applyField("fillOpacity", 1)
            }
        }
        Menu {
            title: "Stroke"
            MenuItem {
                text: "0%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0)
                }
                onTriggered: _ed.applyField("borderOpacity", 0)
            }
            MenuItem {
                text: "25%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0.25)
                }
                onTriggered: _ed.applyField("borderOpacity", 0.25)
            }
            MenuItem {
                text: "50%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0.5)
                }
                onTriggered: _ed.applyField("borderOpacity", 0.5)
            }
            MenuItem {
                text: "75%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0.75)
                }
                onTriggered: _ed.applyField("borderOpacity", 0.75)
            }
            MenuItem {
                text: "100%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || n.borderOpacity === undefined || n.borderOpacity === 1
                }
                onTriggered: _ed.applyField("borderOpacity", 1)
            }
        }
        }
        Menu {
            title: "Align"
            MenuItem { text: "Left"; onTriggered: _ed.applyField("align", "left") }
            MenuItem { text: "Center"; onTriggered: _ed.applyField("align", "center") }
            MenuItem { text: "Right"; onTriggered: _ed.applyField("align", "right") }
            MenuSeparator {}
            MenuItem { text: "Top"; onTriggered: _ed.applyField("valign", "top") }
            MenuItem { text: "Middle"; onTriggered: _ed.applyField("valign", "middle") }
            MenuItem { text: "Bottom"; onTriggered: _ed.applyField("valign", "bottom") }
        }
        MenuItem {
            text: "Bold"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.bold)
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                _ed.applyField("bold", !(n && n.bold))
            }
        }
        MenuItem {
            text: "Word wrap"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !n || n.wrap !== false
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                _ed.applyField("wrap", !(n && n.wrap !== false))
            }
        }
        MenuItem {
            text: "Scale font with box"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.scaleFont)
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                _ed.applyField("scaleFont", !(n && n.scaleFont))
            }
        }
        MenuSeparator {}
        MenuItem {
            text: {
                _ed.tick
                var n = _ed.pinTarget()
                return _ed.isLocked(n) ? "Unpin" : "Pin"
            }
            checkable: true
            checked: {
                _ed.tick
                return _ed.isLocked(_ed.pinTarget())
            }
            onTriggered: {
                var n = _ed.pinTarget()
                if (n)
                    _ed.toggleLock(n.id)
            }
        }
        MenuItem { text: "Bring forward"; onTriggered: _ed.bringForward() }
        MenuItem { text: "Send back"; onTriggered: _ed.sendBack() }
    }

    Menu {
        id: _ctx
        property string nodeId: ""
        property string kind: ""
        property int seg: -1
        property int leader: 0
        MenuItem {
            text: "Undo"
            enabled: _ed.canUndo
            onTriggered: _ed.undo()
        }
        MenuItem {
            text: "Redo"
            enabled: _ed.canRedo
            onTriggered: _ed.redo()
        }
        MenuItem {
            text: "Clear Format"
            enabled: _ed.isGroup(_ed.ctxTarget()) && _ed.ctxHasGroupFormat()
            onTriggered: _ed.clearGroupFormat()
        }
        MenuSeparator {}
        Menu {
            title: "Chip"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            MenuItem {
                enabled: false
                text: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    var mem = _ed.targetMember()
                    if (n && mem)
                        return (n.id || "group") + " · " + (_ed.roleWord(_ed.fiveWayRole(mem)) || _ed.memberLabel(n, mem))
                    return n ? (_ed.friendlyOf(n, mem) || n.id || "Chip") : "Chip"
                }
            }
            MenuItem {
                text: "Rename"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && !_ed.isDraw(n))
                }
                onTriggered: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    if (!n)
                        return
                    var mem = _ed.targetMember()
                    var mi = -1
                    if (mem && n.members) {
                        for (var i = 0; i < n.members.length; i++) {
                            if (n.members[i] === mem) {
                                mi = i
                                break
                            }
                        }
                    }
                    _ed.beginRename(n.id, mi)
                }
            }
            MenuSeparator {}
            Menu {
                id: _fontMenu
                title: "Font size"
                Instantiator {
                    model: [8, 9, 10, 11, 12, 14, 16, 18, 20, 22]
                    delegate: MenuItem {
                        required property int modelData
                        text: "" + modelData
                        checkable: true
                        checked: _ed.fieldEq("fontSize", modelData, 10)
                        onTriggered: _ed.applyField("fontSize", modelData)
                    }
                    onObjectAdded: (i, obj) => _fontMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _fontMenu.removeItem(obj)
                }
            }
            Menu {
                title: "Chip"
                Menu {
                    id: _chipSzMenu
                    title: "Size"
                    Instantiator {
                        model: [12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 42, 48]
                        delegate: MenuItem {
                            required property int modelData
                            text: "" + modelData
                            checkable: true
                            checked: _ed.fieldEq("chipSize", modelData, 18)
                            onTriggered: _ed.applyField("chipSize", modelData)
                        }
                        onObjectAdded: (i, obj) => _chipSzMenu.insertItem(i, obj)
                        onObjectRemoved: (i, obj) => _chipSzMenu.removeItem(obj)
                    }
                }
                MenuItem {
                    text: "Round"
                    checkable: true
                    checked: _ed.fieldEq("chipShape", "round", "round")
                    onTriggered: _ed.applyField("chipShape", "round")
                }
                MenuItem {
                    text: "Square"
                    checkable: true
                    checked: _ed.fieldEq("chipShape", "square", "round")
                    onTriggered: _ed.applyField("chipShape", "square")
                }
                MenuSeparator {}
                MenuItem {
                    text: "Filled"
                    checkable: true
                    checked: _ed.fieldEq("chipFill", "filled", "filled")
                    onTriggered: _ed.applyField("chipFill", "filled")
                }
                MenuItem {
                    text: "Hollow"
                    checkable: true
                    checked: _ed.fieldEq("chipFill", "hollow", "filled")
                    onTriggered: _ed.applyField("chipFill", "hollow")
                }
                MenuSeparator {}
                MenuItem {
                    text: "Reset this cell"
                    enabled: _ed.targetMember() !== null
                    onTriggered: _ed.resetMemberStyle()
                }
            }
            Menu {
                title: "Colors"
                MenuItem { text: "Fill…"; onTriggered: _ed.pickColor("color") }
                MenuItem { text: "Outline…"; onTriggered: _ed.pickColor("border") }
                MenuItem { text: "Text…"; onTriggered: _ed.pickColor("textColor") }
                MenuSeparator {}
                MenuItem { text: "Pressed fill…"; onTriggered: _ed.pickColor("hlColor") }
                MenuItem { text: "Pressed outline…"; onTriggered: _ed.pickColor("hlBorder") }
                MenuItem { text: "Pressed text…"; onTriggered: _ed.pickColor("hlText") }
            }
            MenuItem {
                text: "Highlight on press"
                checkable: true
                checked: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || n.highlight !== false
                }
                onTriggered: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    _ed.applyField("highlight", !(n && n.highlight !== false))
                }
            }
            MenuSeparator {}
            MenuItem {
                text: "Delete chip"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!n && !_ed.isGroup(n) && !_ed.isDraw(n)
                }
                onTriggered: _ed.deleteChip()
            }
        
            
        }
        Menu {
            title: "Hotspot"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            Menu {
                id: _hotSzMenu
                title: "Size"
                Instantiator {
                    model: [4, 6, 8, 9, 10, 12, 14, 16, 20, 24, 28]
                    delegate: MenuItem {
                        required property int modelData
                        text: "" + modelData
                        checkable: true
                        checked: _ed.fieldEq("hotSize", modelData, 9)
                        onTriggered: _ed.applyField("hotSize", modelData)
                    }
                    onObjectAdded: (i, obj) => _hotSzMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _hotSzMenu.removeItem(obj)
                }
            }
            MenuItem {
                text: "Round"
                checkable: true
                checked: _ed.fieldEq("hotShape", "round", "round")
                onTriggered: _ed.applyField("hotShape", "round")
            }
            MenuItem {
                text: "Square"
                checkable: true
                checked: _ed.fieldEq("hotShape", "square", "round")
                onTriggered: _ed.applyField("hotShape", "square")
            }
            MenuSeparator {}
            MenuItem {
                text: "Filled"
                checkable: true
                checked: _ed.fieldEq("hotFill", "filled", "filled")
                onTriggered: _ed.applyField("hotFill", "filled")
            }
            MenuItem {
                text: "Hollow"
                checkable: true
                checked: _ed.fieldEq("hotFill", "hollow", "filled")
                onTriggered: _ed.applyField("hotFill", "hollow")
            }
            MenuSeparator {}
            MenuItem { text: "Color…"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.pickColor("hotColor") } }
        
            
        }
        Menu {
            title: "Leader End"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            MenuItem { text: "Detach chip end"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.detachEnd("from") } }
            MenuItem { text: "Detach hotspot end"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.detachEnd("to") } }
            MenuSeparator {}
            MenuItem { text: "Reconnect to this chip"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.attachEndToSelf("from") } }
            MenuItem { text: "Reconnect to this hotspot"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.attachEndToSelf("to") } }
        
            
        }
        Menu {
            title: "Group"
            enabled: _ed.canGroup() || _ed.canUngroup() || _ed.isGroup(_ed.ctxTarget()) || _ed.groupEditId !== ""


            MenuItem {
                text: "Group selected"
                enabled: _ed.canGroup()
                onTriggered: _ed.groupSelection()
            }
            MenuItem {
                text: "Break group"
                enabled: {
                    _ed.tick
                    return _ed.canUngroup() || _ed.isGroup(_ed.ctxTarget())
                }
                onTriggered: _ed.ungroupSelection()
            }
            MenuItem {
                text: "Edit group"
                enabled: _ed.isGroup(_ed.ctxTarget())
                onTriggered: _ed.beginGroupEdit(_ctx.nodeId)
            }
            MenuItem {
                text: "Done editing group"
                enabled: _ed.groupEditId !== ""
                onTriggered: _ed.endGroupEdit()
            }
        
            
        }
        Menu {
            title: "Format"
            enabled: _ed.isFiveWay(_ed.ctxTarget()) || _ed.ctxHasTheme()


            Menu {
                title: "5-Way"
                enabled: _ed.isFiveWay(_ed.ctxTarget())
                MenuItem {
                    text: "Plus cluster"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "plus"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("plus")
                    }
                }
                MenuItem {
                    text: "Mini hat"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "mini"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("mini")
                    }
                }
                MenuItem {
                    text: "Named card"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "card"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("card")
                    }
                }
                MenuItem {
                    text: "Radial leaders"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "radial"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("radial")
                    }
                }
            }
            MenuItem {
                text: "Clear Format"
                enabled: _ed.ctxHasGroupFormat()
                onTriggered: _ed.clearGroupFormat()
            }
        
            
        }
        Menu {
            title: "Align"
            enabled: _ed.isGroup(_ed.ctxTarget())


            MenuItem { text: "Align left"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("left") }
            MenuItem { text: "Align center"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("center") }
            MenuItem { text: "Align right"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("right") }
            MenuItem { text: "Free layout"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("free") }
        
            
        }
        Menu {
            title: "Leader"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            MenuItem { text: "Color…"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.pickColor("leaderColor") } }
            Menu {
                id: _leadWMenu
                title: "Weight"
                Instantiator {
                    model: [8, 11, 15, 20, 25, 30, 40]
                    delegate: MenuItem {
                        required property int modelData
                        text: (modelData / 10).toFixed(1)
                        checkable: true
                        checked: {
                            var n = _ed.nodeAt(_ed.selectedId)
                            return Math.round(_ed.leaderWidthOf(n) * 10) === modelData
                        }
                        onTriggered: _ed.applyField("leaderWidth", modelData / 10)
                    }
                    onObjectAdded: (i, obj) => _leadWMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _leadWMenu.removeItem(obj)
                }
            }
            MenuSeparator {}
            MenuItem { text: "Add straight spine"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.ensureMidSpine(_ed.nodeAt(_ed.selectedId)); _ed.bump() } }
            MenuItem { text: "Convert spine"; enabled: _ed.ctxHasSelectedSpine(); onTriggered: _ed.convertSelectedSpine() }
            MenuItem { text: "Add curved spine"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.addCurveSpine(_ed.nodeAt(_ed.selectedId)) } }
            Menu {
                title: "This segment"
                MenuItem { text: "Curved"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.selectedLeader = _ctx.leader; _ed.selectedSeg = _ctx.seg; _ed.setSegCurve(_ed.currentLeader(_ed.nodeAt(_ed.selectedId)), Math.max(0, _ctx.seg), true) } }
                MenuItem { text: "Straight"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.selectedLeader = _ctx.leader; _ed.selectedSeg = _ctx.seg; _ed.setSegCurve(_ed.currentLeader(_ed.nodeAt(_ed.selectedId)), Math.max(0, _ctx.seg), false) } }
            }
            Menu {
                title: "All segments"
                MenuItem { text: "Curved"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.setAllSegCurve(true) } }
                MenuItem { text: "Straight"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.setAllSegCurve(false) } }
            }
            MenuSeparator {}
            MenuItem { text: "Add leader"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.addLeader() } }
            MenuItem { text: "Branch from this end"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.selectedLeader = _ctx.leader; _ed.addBranch() } }
            MenuItem {
                text: "Clear all spines"
                enabled: {
                    var id = _ctx.nodeId || _ed.selectedId
                    var n = _ed.nodeAt(id)
                    return !!(n && !_ed.isDraw(n))
                }
                onTriggered: {
                    var id = _ctx.nodeId || _ed.selectedId
                    if (!_ed.nodeAt(id))
                        return
                    _ed.selectedId = id
                    _ed.clearAllSpines(id)
                }
            }
            MenuItem {
                text: "Delete spine"
                enabled: _ed.selectedSpine >= 0
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.selectedLeader = _ctx.leader
                    _ed.deleteSelection()
                }
            }
            MenuItem {
                text: {
                    _ed.tick
                    var ids = _ed.selectedIds || []
                    return ids.length > 1 ? "Delete leaders" : "Delete leader"
                }
                enabled: {
                    var ids = (_ed.selectedIds && _ed.selectedIds.length) ? _ed.selectedIds : [_ed.selectedId]
                    var i
                    for (i = 0; i < ids.length; i++) {
                        var n = _ed.nodeAt(ids[i])
                        if (n && !_ed.isDraw(n) && _ed.leaderList(n).length)
                            return true
                    }
                    return false
                }
                onTriggered: {
                    _ed.deleteLeader()
                }
            }
        
            
        }
        Menu {
            title: "Draw"
            enabled: true

            MenuItem {
                text: { _ed.tick; var n = _ed.ctxTarget(); return _ed.isLocked(n) ? "Unpin overlay" : "Pin overlay" }
                enabled: { var n = _ed.ctxTarget(); return _ed.isOverlay(n) || _ed.isDraw(n) }
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.toggleLock()
                }
            }
            MenuItem {
                text: _ed.plantSnap ? "Click overlay to plant snap…" : "Add snap point"
                enabled: { var n = _ed.ctxTarget(); return _ed.isOverlay(n) }
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.beginPlantSnap()
                }
            }
            MenuItem {
                text: "Clear snap points"
                enabled: {
                    var n = _ed.ctxTarget()
                    return !!(n && n.sockets && n.sockets.length)
                }
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.clearSockets()
                }
            }
            MenuSeparator {}

            Menu {
                title: "Around selection"
                enabled: {
                    var ids = _ed.selectedIds || []
                    var k
                    for (k = 0; k < ids.length; k++) {
                        if (!_ed.isDraw(_ed.nodeAt(ids[k])))
                            return true
                    }
                    return false
                }
                MenuItem { text: "Rectangle"; onTriggered: _ed.addDrawAround("rect") }
                MenuItem { text: "Rounded"; onTriggered: _ed.addDrawAround("roundrect") }
                MenuItem { text: "Ellipse"; onTriggered: _ed.addDrawAround("ellipse") }
                MenuItem { text: "Triangle"; onTriggered: _ed.addDrawAround("triangle") }
                MenuItem { text: "Diamond"; onTriggered: _ed.addDrawAround("diamond") }
            }
            Menu {
                title: "Free drag"
                MenuItem { text: "Rectangle"; checkable: true; checked: _ed.drawTool === "rect"; onTriggered: _ed.setDrawTool("rect") }
                MenuItem { text: "Rounded"; checkable: true; checked: _ed.drawTool === "roundrect"; onTriggered: _ed.setDrawTool("roundrect") }
                MenuItem { text: "Ellipse"; checkable: true; checked: _ed.drawTool === "ellipse"; onTriggered: _ed.setDrawTool("ellipse") }
                MenuItem { text: "Triangle"; checkable: true; checked: _ed.drawTool === "triangle"; onTriggered: _ed.setDrawTool("triangle") }
                MenuItem { text: "Diamond"; checkable: true; checked: _ed.drawTool === "diamond"; onTriggered: _ed.setDrawTool("diamond") }
                MenuItem { text: "Table"; checkable: true; checked: _ed.drawTool === "table"; onTriggered: _ed.setDrawTool("table") }
                MenuItem { text: "Text"; checkable: true; checked: _ed.drawTool === "text"; onTriggered: _ed.setDrawTool("text") }
                MenuSeparator {}
                MenuItem { text: "Import overlay…"; onTriggered: _ed.overlayImportRequested() }
                MenuSeparator {}
                MenuItem { text: "Cancel tool"; enabled: _ed.drawTool.length > 0; onTriggered: _ed.drawTool = "" }
            }
            MenuSeparator {}
            Menu {
                title: "Shape"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return _ed.isDraw(n) && !_ed.isTable(n) && !_ed.isText(n)
                }
                MenuItem { text: "Rectangle"; checkable: true; checked: _ed.fieldEq("shape", "rect", "rect"); onTriggered: _ed.applyField("shape", "rect") }
                MenuItem { text: "Rounded"; checkable: true; checked: _ed.fieldEq("shape", "roundrect", "rect"); onTriggered: _ed.applyField("shape", "roundrect") }
                MenuItem { text: "Ellipse"; checkable: true; checked: _ed.fieldEq("shape", "ellipse", "rect"); onTriggered: _ed.applyField("shape", "ellipse") }
                MenuItem { text: "Triangle"; checkable: true; checked: _ed.fieldEq("shape", "triangle", "rect"); onTriggered: _ed.applyField("shape", "triangle") }
                MenuItem { text: "Diamond"; checkable: true; checked: _ed.fieldEq("shape", "diamond", "rect"); onTriggered: _ed.applyField("shape", "diamond") }
            }
            Menu {
                id: _padMenu
                title: "Padding"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                Instantiator {
                    model: [4, 8, 12, 16, 24, 32]
                    delegate: MenuItem {
                        required property int modelData
                        text: "" + modelData
                        checkable: true
                        checked: _ed.fieldEq("pad", modelData, 8)
                        onTriggered: _ed.applyField("pad", modelData)
                    }
                    onObjectAdded: (i, obj) => _padMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _padMenu.removeItem(obj)
                }
            }
            Menu {
                title: "Rotate"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                MenuItem { text: "0°"; onTriggered: _ed.applyField("rot", 0) }
                MenuItem { text: "90°"; onTriggered: _ed.applyField("rot", 90) }
                MenuItem { text: "180°"; onTriggered: _ed.applyField("rot", 180) }
                MenuItem { text: "270°"; onTriggered: _ed.applyField("rot", 270) }
                MenuItem { text: "-15°"; onTriggered: { var n = _ed.nodeAt(_ed.selectedId); _ed.applyField("rot", ((n && n.rot) ? n.rot : 0) - 15) } }
                MenuItem { text: "+15°"; onTriggered: { var n = _ed.nodeAt(_ed.selectedId); _ed.applyField("rot", ((n && n.rot) ? n.rot : 0) + 15) } }
            }
            MenuItem {
                text: "Filled"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                checkable: true
                checked: _ed.fieldEq("fill", "filled", "hollow")
                onTriggered: _ed.applyField("fill", "filled")
            }
            MenuItem {
                text: "Hollow"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                checkable: true
                checked: _ed.fieldEq("fill", "hollow", "hollow")
                onTriggered: _ed.applyField("fill", "hollow")
            }
            MenuItem {
                text: "Fill color…"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.requestDrawColor("color")
            }
            MenuItem {
                text: "Stroke color…"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.requestDrawColor("border")
            }
            Menu {
                title: "Stroke"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                MenuItem { text: "1"; checkable: true; checked: _ed.fieldEq("stroke", 1, 2); onTriggered: _ed.applyField("stroke", 1) }
                MenuItem { text: "2"; checkable: true; checked: _ed.fieldEq("stroke", 2, 2); onTriggered: _ed.applyField("stroke", 2) }
                MenuItem { text: "3"; checkable: true; checked: _ed.fieldEq("stroke", 3, 2); onTriggered: _ed.applyField("stroke", 3) }
                MenuItem { text: "4"; checkable: true; checked: _ed.fieldEq("stroke", 4, 2); onTriggered: _ed.applyField("stroke", 4) }
                MenuItem { text: "6"; checkable: true; checked: _ed.fieldEq("stroke", 6, 2); onTriggered: _ed.applyField("stroke", 6) }
            }
            Menu {
                title: "Opacity"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                MenuItem { text: "25%"; checkable: true; checked: _ed.fieldEq("opacity", 0.25, 1); onTriggered: _ed.applyField("opacity", 0.25) }
                MenuItem { text: "50%"; checkable: true; checked: _ed.fieldEq("opacity", 0.5, 1); onTriggered: _ed.applyField("opacity", 0.5) }
                MenuItem { text: "75%"; checkable: true; checked: _ed.fieldEq("opacity", 0.75, 1); onTriggered: _ed.applyField("opacity", 0.75) }
                MenuItem { text: "100%"; checkable: true; checked: _ed.fieldEq("opacity", 1, 1); onTriggered: _ed.applyField("opacity", 1) }
            }
            MenuSeparator {}
            MenuItem {
                text: "Bring forward"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.bringForward()
            }
            MenuItem {
                text: "Send back"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.sendBack()
            }
            MenuItem {
                text: "Detach from chips"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return _ed.isDraw(n) && n.around && n.around.length
                }
                onTriggered: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    if (!n) return
                    var g = _ed.drawGeom(n)
                    n.around = []
                    n.fx = _ed.xToFx(g.x)
                    n.fy = _ed.yToFy(g.y)
                    n.fw = g.w / Math.max(1, _ed.spaceRect().w)
                    n.fh = g.h / Math.max(1, _ed.spaceRect().h)
                    _ed.bump()
                }
            }
            MenuItem {
                text: "Delete drawing"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.deleteChip()
            }
        
            
        }


    }
}
